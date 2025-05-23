import json
from clickhouse_connect import get_client
import os
import sys
from dotenv import load_dotenv

load_dotenv()


def get_clickhouse_client():
    return get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", 8123)),
        username=os.getenv("CLICKHOUSE_USER", "default"),
        password=os.getenv("CLICKHOUSE_PASSWORD", ""),
        database=os.getenv("CLICKHOUSE_DB", "default"),
        secure=False,
    )


def create_table_if_not_exists(client):
    # Drop the table first
    drop_stmt = "DROP TABLE IF EXISTS kubescape"
    client.command(drop_stmt)

    # Create the table with JSON payload
    create_stmt = """
    CREATE TABLE kubescape (
        time DateTime64(9, 'UTC'),
        type String,
        node_name String,
        payload JSON
    ) ENGINE = MergeTree()
    ORDER BY time
    """
    client.command(create_stmt)


def insert_json_file(client, file_path):
    rows = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            rows.append(
                (
                    obj["time"],
                    obj.get("node_name", ""),
                    obj["type"],
                    (
                        obj["payload"]
                        if isinstance(obj["payload"], str)
                        else json.dumps(obj["payload"])
                    ),
                )
            )

    client.insert(
        "kubescape", rows, column_names=["time", "node_name", "type", "payload"]
    )

    print(f"✅ Inserted {len(rows)} rows into 'kubescape' table")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Usage: python init_kubescape_data.py path/to/kubescape.json")
        sys.exit(1)

    file_path = sys.argv[1]

    client = get_clickhouse_client()
    create_table_if_not_exists(client)
    insert_json_file(client, file_path)
