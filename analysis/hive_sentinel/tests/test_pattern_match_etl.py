import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.etl.pattern_matcher.etl import PatternMatcherETL

TEST_DIR = os.path.dirname(__file__)
TEST_OUTPUT_FILE = os.path.join(TEST_DIR, "pixie_matched_stream.json")
TEST_INPUT_FILE = os.path.join(TEST_DIR, "data", "kubescape_stix.json")

@pytest.fixture
def sample_rows():
    with open(TEST_INPUT_FILE, "r") as f:
        entries = json.load(f)
    return [[entry["timestamp"], entry["data"]] for entry in entries]

@patch("src.etl.pattern_matcher.etl.ClickHouseClient")
def test_pattern_matcher_fetch_and_process(mock_clickhouse_client_cls, sample_rows):
    # Mock ClickHouseClient().get_client()
    mock_client = MagicMock()
    mock_result = MagicMock()
    mock_result.result_rows = sample_rows
    mock_client.query.return_value = mock_result
    mock_clickhouse_client_cls.return_value.get_client.return_value = mock_client

    if os.path.exists(TEST_OUTPUT_FILE):
        os.remove(TEST_OUTPUT_FILE)

    etl = PatternMatcherETL()
    etl.OUTPUT_FILE = TEST_OUTPUT_FILE
    etl.set_filters(timestamp="20250715153200", podname="webapp-mywebapp-67965968bb-hmnrq", namespace="webapp")

    etl.fetch_and_process()

    # Check file created and has lines
    assert os.path.exists(TEST_OUTPUT_FILE)
    with open(TEST_OUTPUT_FILE, "r") as f:
        lines = f.readlines()
        assert len(lines) > 0
        for line in lines:
            parsed = json.loads(line)
            assert "original" in parsed
            assert "matches" in parsed
            assert isinstance(parsed["matches"], list)

    # Check insert was called
    assert mock_client.execute.called