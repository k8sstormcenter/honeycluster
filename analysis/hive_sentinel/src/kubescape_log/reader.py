from src.pixie_client import get_px_connection
import json
from datetime import datetime, timezone


def iso_to_nanoseconds(iso_ts: str) -> int:
    """
    Convert ISO 8601 timestamp with nanoseconds to nanoseconds since Unix epoch.

    Example: "2025-05-15T10:19:35.195123920Z" -> 1747304375195123920
    """
    # Trim the 'Z' and parse up to microseconds (first 26 chars)
    dt = datetime.strptime(iso_ts[:26], "%Y-%m-%dT%H:%M:%S.%f").replace(
        tzinfo=timezone.utc
    )

    # Convert to nanoseconds
    base_nanos = int(dt.timestamp() * 1_000_000_000)

    # Add extra nanoseconds beyond microsecond precision
    extra_nanos = int(iso_ts[26:29]) if len(iso_ts) >= 29 else 0

    return base_nanos + extra_nanos


PXL_SCRIPT = """
import px
df = px.DataFrame(table="kubescape.json")
df = df[
    px.contains(
        px.pluck(px.pluck(df.payload, 'process'), 'exec_id'), 
        "unexpected process launched"
    )]

df.pid = px.pluck(px.pluck(df.payload, 'process'), 'pid')
df.pod_name = px.pluck(px.pluck(px.pluck(df.payload, 'process'), 'pod'), 'name')
px.display(df[['pid', 'pod_name', 'time', 'payload', 'type']], "kubescape")
"""


def clean_bstring(val):
    val = val.decode("utf-8")
    if isinstance(val, str) and val.startswith("b'") and val.endswith("'"):
        return val[2:-1]
    return val


def fetch_kubescape_logs():
    conn = get_px_connection()

    script = conn.prepare_script(PXL_SCRIPT)
    kubescape_logs = []

    for row in script.results("kubescape"):
        log = {}
        log["pid"] = clean_bstring(row["pid"])
        log["pod_name"] = clean_bstring(row["pod_name"])
        log["time"] = clean_bstring(row["time"])
        log["time_ns"] = iso_to_nanoseconds(clean_bstring(row["time"]))
        raw_payload = row["payload"]
        parsed_payload = json.loads(raw_payload)
        log[clean_bstring(row["type"])] = parsed_payload
        kubescape_logs.append(log)

    return kubescape_logs
