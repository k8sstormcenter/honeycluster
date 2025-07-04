import pytest
from src.etl.pixie_etl import PixieETL

@pytest.fixture
def sample_http_columns():
    return ["time_", "upid", "encrypted", "req_path"]

@pytest.fixture
def sample_dns_columns():
    return ["time_", "upid", "encrypted", "req_body"]

@pytest.mark.parametrize("table_name,processed_table,column_names,row_data,expected_row", [
    (
        "http_events",
        "http_events",
        ["time_", "upid", "encrypted", "req_path"],
        [1234567890, "http-upid", 1, "/test"],
        [1234567890, "http-upid", 1, "/test"]
    ),
    (
        "dns_events",
        "dns_events",
        ["time_", "upid", "encrypted", "req_body"],
        [1234567891, "dns-upid", 0, "example.com"],
        [1234567891, "dns-upid", 0, "example.com"]
    )
])
def test_fetch_and_process_inserts_data(mocker, table_name, processed_table, column_names, row_data, expected_row):
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
        column_names=column_names,
        poll_interval=10
    )

    etl.fetch_and_process()

    # Check .insert() was called once with the correct data
    mock_clickhouse_client.insert.assert_called_once()
    args, kwargs = mock_clickhouse_client.insert.call_args

    assert args[0] == processed_table
    inserted_rows = args[1]
    assert inserted_rows[0] == expected_row
    assert kwargs["column_names"] == column_names

    # Check last_seen_ns
    assert etl.last_seen_ns == row_data[0]
