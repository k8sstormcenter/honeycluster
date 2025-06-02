import json
import datetime

def convert_nodeagent_to_tetragon(nodeagent_json):
    """
    Converts a nodeagent JSON record to a Tetragon-compatible JSON format.

    Args:
        nodeagent_json (dict): A dictionary representing the nodeagent JSON record.

    Returns:
        dict: A dictionary representing the Tetragon JSON schema, or None if the input is invalid.
    """

    if not isinstance(nodeagent_json, dict):
        print("Error: Input must be a dictionary.")
        return None

    if "BaseRuntimeMetadata" not in nodeagent_json or "event" not in nodeagent_json:
        print("Error: Input dictionary must contain 'BaseRuntimeMetadata' and 'event' keys.")
        return None

    base_metadata = nodeagent_json["BaseRuntimeMetadata"]
    event_data = nodeagent_json["event"]

    tetragon_json = {
        "time": base_metadata.get("timestamp"),
        "node_name": base_metadata.get("node_name") or event_data["k8s"].get("node", "unknown"),
        "type": base_metadata.get("alertName"),  # Maps to alertName
        "payload": {}
    }

    # Process details from BaseRuntimeMetadata and RuntimeProcessDetails
    process_details = {}
    if "RuntimeProcessDetails" in nodeagent_json:
        process_details = nodeagent_json["RuntimeProcessDetails"]["processTree"]
        process_details["exec_id"] = base_metadata.get("exec_id", "unknown")
        process_details["start_time"] = base_metadata.get("startTime", "0001-01-01T00:00:00Z")
        process_details["auid"] = base_metadata.get("auid", 4294967295)
        process_details["flags"] = base_metadata.get("flags", "unknown")
        process_details["cwd"] = base_metadata.get("cwd", "/")
        process_details["path"] = base_metadata.get("path", "unknown")
        process_details["in_init_tree"] = base_metadata.get("in_init_tree", False)
        process_details["tid"] = process_details.get("pid")
        process_details["parent_exec_id"] = base_metadata.get("parent_exec_id", "unknown")

        if "pod" in base_metadata:
            process_details["pod"] = base_metadata["pod"]
        elif "k8s" in event_data:
            process_details["pod"] = {
                "namespace": event_data["k8s"].get("namespace", "default"),
                "name": event_data["k8s"].get("podName", "unknown"),
                "container": {
                    "id": event_data["runtime"].get("containerId", "unknown"),
                    "name": event_data["runtime"].get("containerName", "unknown"),
                    "image": {
                        "id": event_data["runtime"].get("containerImageDigest", "unknown"),
                        "name": event_data["runtime"].get("containerImageName", "unknown")
                    },
                    "start_time": base_metadata.get("startTime", "0001-01-01T00:00:00Z")
                },
                "pod_labels": event_data["k8s"].get("podLabels", {}),
                "workload": event_data["k8s"].get("workloadName", "unknown"),
                "workload_kind": event_data["k8s"].get("workloadKind", "unknown")
            }
        process_details["docker"] = event_data["runtime"].get("containerId", "unknown")
        tetragon_json["payload"]["process"] = process_details

    if "arguments" in base_metadata:
        tetragon_json["payload"]["arguments"] = base_metadata["arguments"]

    return tetragon_json

# Example usage (assuming you have the JSON data in a variable called 'nodeagent_data')
nodeagent_data = json.loads(your_json_string)
tetragon_data = convert_nodeagent_to_tetragon(nodeagent_data)

if tetragon_data:
   print(json.dumps(tetragon_data, indent=2))
