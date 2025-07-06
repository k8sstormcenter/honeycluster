# Hive Sentinel

Hive Sentinel is a microservice that connects to a Pixie observability cluster and ClickHouse, fetches Tetragon and Kubescape logs, and transforms them into [STIX 2.1](https://oasis-open.github.io/cti-documentation/stix/intro) bundles for security operations and threat detection pipelines.

## 🧬 What It Does

* Connects to Pixie via their Python SDK to retrieve logs.
* Connects to ClickHouse to persist processed STIX objects.
* Parses, cleans, and converts logs to STIX 2.1 format with custom correlation logic.
* Runs automated ETL pipelines for:

  * Tetragon to STIX
  * Kubescape to STIX
* Exposes REST API endpoints to:

  * Fetch raw Tetragon logs
  * Fetch raw Kubescape logs
  * Fetch STIX bundles
  * Start/stop Pixie ETL pipelines
  * Check ETL status

## 🚀 How to Run

Install [Poetry](https://python-poetry.org/) and run:

```bash
poetry install
poetry run python main.py
```

Configure your Pixie and ClickHouse environment variables before starting.

## 🚀 How to Test

```bash
poetry install
poetry run pytest
```

Tests cover Pixie ETL, STIX ETL, and REST endpoints.

## 🔐 Environment Setup

Set your Pixie and ClickHouse credentials in a `.env` file:

```
PIXIE_API_TOKEN=px-api-...
PIXIE_CLUSTER_ID=426ee8d4-...
CLICKHOUSE_HOST=localhost
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=
CLICKHOUSE_DB=default
```

These are loaded automatically using `python-dotenv`.

## 📡 Endpoints

### `GET /tetragon`

Fetch raw Tetragon logs.

### `GET /tetragon/fetch-stix`

Fetch Tetragon logs transformed as STIX bundles.

### `GET /kubescape`

Fetch raw Kubescape logs.

### `GET /kubescape/fetch-stix`

Fetch Kubescape logs transformed as STIX bundles.

### `POST /pixie-etl/start`

Start a Pixie ETL pipeline.

#### Request Body Example

```json
{
  "tablename": "http_events",
  "timestamp": "2025-07-03T11:37:36Z",
  "podname": "my-pod",
  "namespace": "default",
  "poll_interval": 5
}
```

### `POST /pixie-etl/stop`

Stop a running Pixie ETL pipeline.

#### Request Body Example

```json
{
  "uuid": "c5ddc8e8-5f6f-4c2d-8e58-3fd2ea739b2d"
}
```

### `GET /pixie-etl/status`

List currently running ETL jobs.

## 🛠️ Developer Notes

👉 Uses `apscheduler` for periodic ETL polling.
👉 Uses `clickhouse-connect` for ingestion.
👉 Uses `python-dotenv` for local environment management.
👉 StixETLs start automatically in production and are disabled during tests.
👉 During the tests, Pixie and Clickhouse connections are mocked. No real Database connection used

---

Made with ❤️ for scalable observability and STIX pipelines.
