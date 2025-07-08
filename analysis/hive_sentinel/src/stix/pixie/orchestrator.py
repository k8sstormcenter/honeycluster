from src.stix.core import sanitize_bundle, generate_stix_id
from src.stix.pixie.transform_dns_to_stix import transform_dns_row_to_stix
from src.stix.pixie.transform_http_to_stix import transform_http_row_to_stix

def transform_pixie_logs_to_stix(pixie_logs, log_type):
    stix_bundles = []
    all_stix_objects = []

    for log in pixie_logs:
        if log_type == "dns_stix":
            stix_objects = transform_dns_row_to_stix(log)
        elif log_type == "http_stix":
            stix_objects = transform_http_row_to_stix(log)
        else:
            continue

        all_stix_objects.extend(stix_objects)

        stix_bundle = {
            "type": "bundle",
            "id": generate_stix_id("bundle"),
            "spec_version": "2.1",
            "objects": stix_objects,
        }

        stix_bundles.append(sanitize_bundle(stix_bundle))

    return all_stix_objects, stix_bundles
