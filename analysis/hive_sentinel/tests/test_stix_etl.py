import pytest
from unittest.mock import MagicMock, patch
from src.etl.stix_etl import StixETL

@pytest.fixture
def sample_rows():
    # Simulate ClickHouse row: (timestamp_ns, data, ...)
    return [
        [1719923456000000000, '{"key": "value"}'],
        [1719923456000001000, '{"key": "value2"}']
    ]

@pytest.fixture
def processed_rows():
    return [
        [1719923456000000000, '{"processed": "data1"}'],
        [1719923456000001000, '{"processed": "data2"}']
    ]

@patch("src.etl.stix_etl.ClickHouseClient")
def test_stix_etl_fetch_and_process(mock_clickhouse_client_cls, sample_rows, processed_rows):
    # Mock ClickHouseClient().get_client()
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = sample_rows
    mock_client.query.return_value = mock_result
    mock_clickhouse_client_cls.return_value.get_client.return_value = mock_client

    # Mock process_func to transform rows predictably
    def mock_process_func(row):
        index = sample_rows.index(row)
        return processed_rows[index]

    etl = StixETL(
        table="test_table",
        processed_table="test_processed_table",
        column_names=["timestamp", "data"],
        time_column_index=0,
        process_func=mock_process_func,
        poll_interval=5
    )

    # Act
    etl.fetch_and_process()

    # Assert: insert called with correct processed data
    mock_client.insert.assert_called_once()
    args, kwargs = mock_client.insert.call_args

    assert args[0] == "test_processed_table"
    assert args[1] == processed_rows
    assert kwargs["column_names"] == ["timestamp", "data"]

    # Assert: last_seen_ns is updated to the last row's timestamp
    assert etl.last_seen_ns == sample_rows[-1][0]
