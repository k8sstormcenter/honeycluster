from src.stix.core import generate_stix_id, _get_current_time_iso_format

def transform_http_row_to_stix(row):
    timestamp = _get_current_time_iso_format()
    corr_id = f"http-{row.get('src_ip', 'unknown')}-{row.get('url', 'unknown')}-{row.get('timestamp', '0')}"

    stix_objects = []

    # NetworkTraffic with HTTP extension
    network_traffic_object = {
        "type": "network-traffic",
        "id": generate_stix_id("network-traffic"),
        "protocols": ["tcp"],
        "extensions": {
            "x-pixie-http-ext": {
                "method": row.get("method"),
                "url": row.get("url"),
                "status_code": row.get("status_code"),
                "headers": row.get("headers", {}),
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
            "note": "Pixie HTTP data wrapped in STIX observed-data"
        },
    }
    stix_objects.append(observed_data_object)

    return stix_objects