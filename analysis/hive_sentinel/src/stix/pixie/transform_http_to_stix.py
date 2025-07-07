import json
from src.stix.core import generate_stix_id, _get_current_time_iso_format

def transform_http_row_to_stix(row):
    timestamp = _get_current_time_iso_format()

    req_headers = json.loads(row.get("req_headers", "{}"))
    resp_headers = json.loads(row.get("resp_headers", "{}"))

    method = row.get("req_method")
    path = row.get("req_path")
    status_code = row.get("resp_status")

    dst_ip = row.get("local_addr")
    dst_port = row.get("local_port")
    url = f"http://{dst_ip}:{dst_port}{path}" if dst_ip and dst_port and path else None

    src_ip = row.get("remote_addr")
    src_port = row.get("remote_port")

    corr_id = f"http-{src_ip or 'unknown'}-{path or 'unknown'}-{row.get('time_', '0')}"

    stix_objects = []

    network_traffic_object = {
        "type": "network-traffic",
        "id": generate_stix_id("network-traffic"),
        "protocols": ["tcp"],
        "extensions": {
            "x-pixie-http-ext": {
                "method": method,
                "url": url,
                "status_code": status_code,
                "headers": req_headers,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "raw_row": row, 
            }
        },
        "start": timestamp,
    }
    stix_objects.append(network_traffic_object)

    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created_time": timestamp,
        "first_observed": timestamp,
        "last_observed": timestamp,
        "number_observed": 1,
        "object_refs": [network_traffic_object["id"]],
        "extensions": {
            "correlation": corr_id,
            "note": "Pixie HTTP data wrapped in STIX observed-data"
        },
    }
    stix_objects.append(observed_data_object)

    return stix_objects
