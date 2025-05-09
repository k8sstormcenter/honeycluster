# Pixie STIX Transformer

This project connects to a Pixie observability cluster, fetches Tetragon logs, and transforms them into [STIX 2.1](https://oasis-open.github.io/cti-documentation/stix/intro) format for security analysis and threat intelligence workflows.

## 🧠 What It Does

* Uses Pixie's Python API to fetch logs from the `tetragon.json` table.
* Cleans and parses the logs.
* Transforms them into STIX 2.1 objects using custom logic.
* Outputs the STIX bundle and matching indicators.

## 📁 Project Structure

```
pixie-pyton/
├── README.md
├── poetry.lock
├── pyproject.toml
├── .env                 # Store your Pixie token and cluster ID here
└── src/
    ├── display_tetragon.py      # Main script that connects to Pixie and runs the transformer
    ├── tetragon2stix.py         # STIX transformation logic for Tetragon and Kubescape logs
    └── __pycache__/             # Python bytecode cache (you can ignore this)
```

## 🚀 How to Run

Make sure you have your virtual environment set up using [Poetry](https://python-poetry.org/):

```bash
poetry install
poetry shell
```

Set your environment variables in a `.env` file:

```
PIXIE_API_TOKEN=px-api-...
PIXIE_CLUSTER_ID=426ee8d4-...
```

Then run the main script:

```bash
python src/display_tetragon.py
```

## 🔐 Pixie Token & Cluster

The script uses `python-dotenv` to load your Pixie credentials from a `.env` file. Make sure `.env` is in your root directory.

```python
from dotenv import load_dotenv
load_dotenv()
```

## 💪 Dependencies

All dependencies are defined in `pyproject.toml`. If you want to add more, just run:

```bash
poetry add <package-name>
```

## 💠 Notes

* Only logs that match known STIX attack patterns will be added to the final bundle.
* `tetragon2stix.py` includes helpers for generating predictable STIX IDs and mapping kprobe events.

## 📩 Output

After processing, the script prints a prettified JSON with the generated STIX objects to stdout.

---

Made with ❤️ for observability + threat detection.
