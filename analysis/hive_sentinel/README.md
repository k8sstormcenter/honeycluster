# Hive Sentinel

Hive Sentinel is a microservice that connects to a Pixie observability cluster, fetches Tetragon logs, and transforms them into [STIX 2.1](https://oasis-open.github.io/cti-documentation/stix/intro) bundles for use in security operations and threat detection pipelines.

## 🧠 What It Does

* Connects to Pixie via their Python SDK and retrieves logs from the `tetragon.json` table.
* Parses and cleans the log data.
* Converts logs to STIX 2.1 format using custom logic and correlation IDs.
* Exposes REST API endpoints to:

  * Fetch raw Tetragon logs
  * Fetch transformed STIX bundles
  * Accept external STIX bundles (coming soon)

## 🚀 How to Run

Make sure you have [Poetry](https://python-poetry.org/) installed, then:

```bash
poetry install
poetry run python main.py
```

Or enter the shell:

```bash
poetry shell
python main.py
```

## 📁 Folder Structure

```
├── main.py                 # Entry point for the Flask app
├── src/
│   ├── stix/               # Shared STIX logic
│   │   ├── core.py         # ID generation, timestamps, sanitizer, relationships
│   │   ├── matcher.py      # Pattern matching and attack pattern registry
│   │   └── tetra/          # Tetragon-specific STIX transformation
│   │       ├── transformer.py
│   │       ├── id_generator.py
│   │       └── orchestrator.py
│   ├── tetra_log/          # App-level modules (Flask routes, Pixie client, etc.)
│   │   ├── controller.py
│   │   ├── reader.py
│   │   ├── routes.py
│   │   └── pixie_client.py
│   └── __init__.py         # Application factory
├── tests/                  # Unit tests and mocks
│   └── test_routes.py
├── .env.template           # Example environment config
├── poetry.lock             # Locked dependency versions
├── pyproject.toml          # Poetry project configuration
└── README.md               # You are here
```

## 🔐 Environment Setup

Set your Pixie credentials in a `.env` file:

```
PIXIE_API_TOKEN=px-api-...
PIXIE_CLUSTER_ID=426ee8d4-...
```

These are loaded automatically using `python-dotenv`.

Alternatively, you can run the helper script:
```bash
bash scripts/pixie-auth-info.sh
```
It will create a new Pixie API token. Then print the created token and the first healthy cluster ID to the terminal.

## 🥪 Testing

Unit tests are written with `pytest`. Run them with:

```bash
poetry run pytest
```

You can mock Tetragon logs to keep tests isolated from Pixie.

## 📡 Endpoints

| Method | Endpoint       | Description                  |
| ------ | -------------- | ---------------------------- |
| GET    | `/fetch-tetra` | Returns raw Tetragon logs    |
| GET    | `/fetch-stix`  | Returns logs as STIX bundles |
| POST   | `/ingest-stix` | (coming soon) Accepts STIX   |

---

Made with ❤️ for Kubernetes observability, STIX, and bees.
