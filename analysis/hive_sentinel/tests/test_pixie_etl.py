import pytest
from src.etl.pixie_etl import PixieETL

@pytest.fixture
def sample_http_columns():
    return ["time_", "upid", "encrypted", "req_path"]

@pytest.fixture
def sample_dns_columns():
    return ["time_", "upid", "encrypted", "req_body"]

@pytest.mark.parametrize("table_name,processed_table,stix_table,column_names,row_data,expected_row", [
    (
        "http_events",
        "http_logs",
        "http_stix",
        ["time_", "upid", "encrypted", "req_path"],
        [1234567890, "http-upid", 1, "/test"],
        [1234567890, "http-upid", 1, "/test"]
    ),
    (
        "dns_events",
        "dns_logs",
        "dns_stix",
        ["time_", "upid", "encrypted", "req_body"],
        [1234567891, "dns-upid", 0, "example.com"],
        [1234567891, "dns-upid", 0, "example.com"]
    )
])

def test_fetch_and_process_inserts_dual_data(mocker, table_name, processed_table, stix_table, column_names, row_data, expected_row):
    # Mock get_px_connection
    mock_conn = mocker.Mock()
    mock_script = mocker.Mock()

    mock_script.results.return_value = iter([row_data])
    mock_conn.prepare_script.return_value = mock_script

    mocker.patch("src.etl.pixie_etl.get_px_connection", return_value=mock_conn)

    # Mock ClickHouseClient().get_client()
    mock_clickhouse_client = mocker.Mock()
    mock_clickhouse_client.insert = mocker.Mock()

    mock_clickhouse_client_cls = mocker.Mock()
    mock_clickhouse_client_cls.get_client.return_value = mock_clickhouse_client

    mocker.patch("src.etl.pixie_etl.ClickHouseClient", return_value=mock_clickhouse_client_cls)

    etl = PixieETL(
        table_name=table_name,
        processed_table=processed_table,
        stix_table=stix_table,
        column_names=column_names,
        poll_interval=10
    )

    etl.fetch_and_process()

    # Check two inserts: one for logs, one for STIX
    assert mock_clickhouse_client.insert.call_count == 2

    # Check first insert (raw logs)
    args_logs, kwargs_logs = mock_clickhouse_client.insert.call_args_list[0]
    assert args_logs[0] == processed_table
    inserted_rows_logs = args_logs[1]
    assert inserted_rows_logs[0] == expected_row
    assert kwargs_logs["column_names"] == column_names

    # Check second insert (STIX bundles)
    args_stix, kwargs_stix = mock_clickhouse_client.insert.call_args_list[1]
    assert args_stix[0] == stix_table
    print(args_stix)
    print(kwargs_stix)
    inserted_rows_stix = args_stix[1]
    assert isinstance(inserted_rows_stix[0][0], int)  # timestamp
    assert isinstance(inserted_rows_stix[0][1], str)  # JSON string
    assert kwargs_stix["column_names"] == ["timestamp", "data"]

    # Check last_seen_ns updated
    assert etl.last_seen_ns == row_data[0]
