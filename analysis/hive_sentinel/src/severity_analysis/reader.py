import json
from src.pixie_client import get_px_connection
from src.kubescape_log.reader import fetch_kubescape_logs


def get_dns_script(event_time_ns):
    return f"""
import px

df = px.DataFrame(table='dns_events')

df = df[px.abs(px.time_to_int64(df.time_) - {event_time_ns}) < px.parse_duration("10s")]
df = df['time_', 'latency', 'req_header', 'req_body',
        'resp_header', 'resp_body']

px.display(df, "dns")
"""


def get_http_script(event_time_ns):
    print(event_time_ns)
    return f"""
import px

df = px.DataFrame(table='http_events')

df = df[px.abs(px.time_to_int64(df.time_) - {event_time_ns}) < px.parse_duration("2s")]
df = df['time_', 'latency', 'major_version', 'req_path',
        'req_method', 'req_headers', 'req_body', 'req_body_size', 'resp_status',
        'resp_message', 'resp_headers', 'resp_body', 'resp_body_size']

px.display(df, "http")
"""


def deep_clean_bstrings(val):
    if isinstance(val, dict):
        return {k: deep_clean_bstrings(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [deep_clean_bstrings(i) for i in val]
    elif isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except:
            return str(val)
    return val


def extract_log_fields(row, keys):
    return {k: deep_clean_bstrings(row[k]) for k in keys}


def get_bundle():
    kubescape_logs = fetch_kubescape_logs()
    conn = get_px_connection()
    bundle = []

    dns_keys = [
        "time_",
        "latency",
        "req_header",
        "req_body",
        "resp_header",
        "resp_body",
    ]

    http_keys = [
        "time_",
        "latency",
        "major_version",
        "req_path",
        "req_method",
        "req_headers",
        "req_body",
        "req_body_size",
        "resp_status",
        "resp_message",
        "resp_headers",
        "resp_body",
        "resp_body_size",
    ]

    for k_log in kubescape_logs:
        event = {**k_log}

        dns_script = conn.prepare_script(get_dns_script(event["time_ns"]))
        dns_logs = [
            extract_log_fields(row, dns_keys) for row in dns_script.results("dns")
        ]

        http_script = conn.prepare_script(get_http_script(event["time_ns"]))
        http_logs = [
            extract_log_fields(row, http_keys) for row in http_script.results("http")
        ]

        event["dns_logs"] = dns_logs
        event["http_logs"] = http_logs
        bundle.append(event)

    return bundle
