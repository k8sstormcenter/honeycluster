import pytest
from unittest.mock import MagicMock, patch
from src.etl.stix_etl.etl import StixETL

@pytest.fixture
def sample_rows():
    # Simulate ClickHouse rows with ISO8601 timestamp and data string
    return [
        ["2025-07-02T12:34:16Z", '{"key": "value"}'],
        ["2025-07-02T12:34:17Z", '{"key": "value2"}']
    ]

@pytest.fixture
def processed_rows(sample_rows):
    # Return processed rows using the same ISO timestamps
    return [
        [sample_rows[0][0], '{"processed": "data1"}'],
        [sample_rows[1][0], '{"processed": "data2"}']
    ]

@patch("src.etl.stix_etl.etl.ClickHouseClient")
def test_stix_etl_fetch_and_process(mock_clickhouse_client_cls, sample_rows, processed_rows):
    # Mock ClickHouseClient().get_client()
    mock_client = MagicMock()
    mock_client.execute.return_value = sample_rows
    mock_clickhouse_client_cls.return_value.get_client.return_value = mock_client

    # Mock process_func to return our processed_rows fixtures
    def mock_process_func(row):
        return processed_rows[sample_rows.index(row)]

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

    # Assert: insert called correctly
    mock_client.insert.assert_called_once()
    args, kwargs = mock_client.insert.call_args
    assert args[0] == "test_processed_table"
    assert args[1] == processed_rows
    assert kwargs["column_names"] == ["timestamp", "data"]

    # Assert: last_seen_ts is updated to the ISO string of the last row
    assert etl.last_seen_ts == sample_rows[-1][0]