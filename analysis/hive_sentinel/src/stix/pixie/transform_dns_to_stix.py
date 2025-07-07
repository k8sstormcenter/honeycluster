from src.stix.core import generate_stix_id, _get_current_time_iso_format

def transform_dns_row_to_stix(row):
    timestamp = _get_current_time_iso_format()
    corr_id = f"dns-{row.get('src_ip', 'unknown')}-{row.get('query_name', 'unknown')}-{row.get('timestamp', '0')}"

    stix_objects = []

    # NetworkTraffic with DNS extension
    network_traffic_object = {
        "type": "network-traffic",
        "id": generate_stix_id("network-traffic"),
        "protocols": ["udp"],
        "extensions": {
            "x-pixie-dns-ext": {
                "query_name": row.get("query_name"),
                "query_type": row.get("query_type"),
                "response_code": row.get("response_code"),
                "answers": row.get("answers", []),
                "src_ip": row.get("src_ip"),
                "dst_ip": row.get("dst_ip"),
                "src_port": row.get("src_port"),
                "dst_port": row.get("dst_port"),
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
            "note": "Pixie DNS data wrapped in STIX observed-data"
        },
    }
    stix_objects.append(observed_data_object)

    return stix_objects