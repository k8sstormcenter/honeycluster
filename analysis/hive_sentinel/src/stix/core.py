import uuid
from datetime import datetime, timezone

def generate_stix_id(type):
    return f"{type}--{uuid.uuid4()}"

def _get_current_time_iso_format():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds") + "Z"

def create_relationship(source_ref, target_ref, relationship_type):
    return {
        "type": "relationship",
        "spec_version": "2.1",
        "id": generate_stix_id("relationship"),
        "created": _get_current_time_iso_format(),
        "modified": _get_current_time_iso_format(),
        "relationship_type": relationship_type,
        "source_ref": source_ref,
        "target_ref": target_ref,
    }

def sanitize_bundle(bundle):
    if not isinstance(bundle, dict):
        return bundle
    return {k: sanitize_bundle(v) for k, v in bundle.items() if v is not None}

def compare_stix_objects(obj, objects_array):
    for other_obj in objects_array:
        if obj["type"] == other_obj["type"]:
            if all(
                obj.get(key) == other_obj.get(key)
                for key in obj
                if key not in ["id", "created", "modified", "spec_version"]
            ) and all(
                other_obj.get(key) == obj.get(key)
                for key in other_obj
                if key not in ["id", "created", "modified", "spec_version"]
            ):
                return True
    return False