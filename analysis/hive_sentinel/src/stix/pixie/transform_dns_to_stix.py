import json
from src.stix.core import generate_stix_id, _get_current_time_iso_format

def transform_dns_row_to_stix(row):
    timestamp = _get_current_time_iso_format()

    req_body = json.loads(row.get("req_body", "{}"))
    query = req_body.get("queries", [{}])[0]
    query_name = query.get("name")
    query_type = query.get("type")

    resp_header = json.loads(row.get("resp_header", "{}"))
    response_code = resp_header.get("rcode")

    resp_body = json.loads(row.get("resp_body", "{}"))
    answers = resp_body.get("answers", [])

    src_ip = row.get("remote_addr")
    dst_ip = row.get("local_addr")
    src_port = row.get("remote_port")
    dst_port = row.get("local_port")

    corr_id = f"dns-{src_ip or 'unknown'}-{query_name or 'unknown'}-{row.get('time_', '0')}"

    stix_objects = []

    network_traffic_object = {
        "type": "network-traffic",
        "id": generate_stix_id("network-traffic"),
        "protocols": ["udp"],
        "extensions": {
            "x-pixie-dns-ext": {
                "query_name": query_name,
                "query_type": query_type,
                "response_code": response_code,
                "answers": answers,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "raw_row": row,  # Keep raw for debug
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
            "note": "Pixie DNS data wrapped in STIX observed-data"
        },
    }
    stix_objects.append(observed_data_object)

    return stix_objects
