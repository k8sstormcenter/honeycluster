
import uuid
import json
import base64
import re
from datetime import datetime, timezone
from stix2matcher.matcher import match

# Constants
STIX_VERSION = '2.1'
PROCESS_EXT_KEY = "process-ext"
OBSERVED_DATA_EXT_KEY = "observed-data-ext"

def create_relationship(source_ref, target_ref, relationship_type):
    """Creates a STIX relationship object."""
    return {
        "type": "relationship",
        "spec_version": STIX_VERSION,  
        "id": generate_stix_id("relationship"), #TODO: create a predictable UUID  based on the three inputs
        "created": _get_current_time_iso_format(),  
        "modified": _get_current_time_iso_format(),
        "relationship_type": relationship_type,
        "source_ref": source_ref,
        "target_ref": target_ref,
    }

def generate_stix_id(type):
    return f"{type}--{uuid.uuid4()}"


def _get_current_time_iso_format():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds") + "Z"


def sanitize_bundle(bundle):
    """
    Recursively remove keys with None values from a dictionary.
    """
    if not isinstance(bundle, dict):
        return bundle
    return {k: sanitize_bundle(v) for k, v in bundle.items() if v is not None}


def get_observable_id(bundle):
    return next(
        (obj["id"] for obj in bundle["objects"] if obj["type"] == "observed-data"), None
    )


#needs to return the PATTERN and the ID from the indicator block
def get_pattern(STIX_ATTACK_PATTERN):
    for obj in STIX_ATTACK_PATTERN["objects"]:
        if obj["type"] == "indicator":
            return obj["pattern"], obj["id"]  # Return both pattern and id
    return None, None

# The following works for tetragon
def unique_process_stix_id(exec_id):
    if exec_id:
        try:
            decoded_exec_id = base64.b64decode(exec_id).decode('utf-8')  
            truncated_exec_id = decoded_exec_id[-36:]  
            stix_id = f"process--{truncated_exec_id}"
            return stix_id
        except Exception as e:  
            print(f"Error decoding or hashing exec_id: {e}")

# This is an attempt to make a concat UUID for STIX, it doesnt work for falco until we get a pid
def create_process_stix_id(corr_id):
    if corr_id:
        try:
            truncated_exec_id = corr_id[:36]  
            stix_id = f"process--{truncated_exec_id}"
            return stix_id
        except Exception as e:  
            print(f"Error decoding or hashing exec_id: {e}")

def generate_unique_log_id(container_id, pid, hostname, time,src):
    # Convert Timestamp to ISO 8601 
    # We use the first two ids since they are most reliably available in toolings,
    #tetra: containerd://5a47f1e4aea1058c56280dfac88800b13082c4ac12c9e475c5485a9dd4d5a6bf|787304|honeycluster-control-plane|2025-03-07T16:26:29.583093313Z
    #falco: 7edade45f808
    pid= str(pid).zfill(8)
    host=str(hostname[:12]).zfill(12)

    if src == "tetra":
        con_id = re.match(r"containerd://([0-9a-f]+)", container_id).group(1)[:12]
        timestamp = re.sub(r"[-\:\.]", "", time[2:22]) 
    elif src == "falco":
        con_id = container_id
        timestamp = re.sub(r"[-\:\.]", "", time[2:22]) 
    elif src == "kubescape":
        con_id = container_id[:12]
        timestamp = re.sub(r"[-\:\.]", "", time[2:22]) 
    elif src == "tracee":
        con_id = container_id[:12]
        timestamp = re.sub(r"[-\:\.]", "", time[2:22]) 
        #host for tracee can be weird if she is picking up stuff on kind, should work on real k8s though
    else:  
        con_id = container_id[:12]
        timestamp = re.sub(r"[-\:\.]", "", time[2:22]) 
    
    unique_id = f"{timestamp}{con_id}{pid}{host}"
    # Given that we need to manipulate the above string, we wont hash it
    #unique_id = hashlib.sha256(input_string.encode('utf-8')).hexdigest()

    return unique_id

# This function is specific to tetragons format
def kprobe(k, element):
    try:
        kprobe=k.get(element,{}).get("string_arg", "") or k.get(element,{}).get("int_arg", "") or k.get(element,{}).get("sock_arg", "") or k.get(element,{}).get("file_arg", "")
    except:
        kprobe = ""
    return kprobe


# Requirements:
# the timestamps must all be the same form and legnth!
# the fields should capture as identical as possible the information from the very different sources
# we need to identify a common ID to use as process identifer not these random-gen UUIDs!
def transform_kprobe_to_stix(log, node_name,k):
    parent = log.get("parent", {})
    process = log.get("process", {})
    container_id = process.get("pod", {}).get("container", {}).get("id", "")
    pid = process.get("pid", -1)
    hostname = node_name
    timestamp = process.get("start_time")
    corr_id = generate_unique_log_id(container_id, pid, hostname, timestamp,"tetra")

    stix_objects = []

    process_object = {
        "type": "process",
        "id": create_process_stix_id(corr_id),
        "pid": pid,
        "command_line": f"{process.get('binary')} {process.get('arguments')}",
        "cwd": process.get("cwd"),
        "created_time": timestamp,
        "extensions": {
                "flags": process.get("flags", ""),
                "image_id": process.get("pod", {}).get("container", {}).get("image", {}).get("id", ""),
                "container_id": container_id,
                "pod_name": process.get("pod", {}).get("name", ""),
                "namespace": process.get("pod", {}).get("namespace", ""),
                "function_name": log.get("function_name", ""),
                "parent_pid":parent.get("exec_id"),
                "parent_command_line": f"{parent.get('binary')} {parent.get('arguments')}",
                "parent_cwd": parent.get("cwd"),
                "grand_parent_pid": parent.get("parent_exec_id"),
                "kprobe0": kprobe(k,"kprobe0"),
                "kprobe1": kprobe(k,"kprobe1"),
                "kprobe2": kprobe(k,"kprobe2"),
                "kprobe3": kprobe(k,"kprobe3"),
                "kprobe4": kprobe(k,"kprobe4")         
        }
    }
    stix_objects.append(process_object)

    current_time = log.get("time", _get_current_time_iso_format())
    # This is where interpreted stuff gets appended, like mitre TTPs, criticality and such
    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created": current_time,
        "first_observed": current_time,
        "last_observed": current_time,
        "number_observed": 1,#TODO: we need to get this from the dedup function
        "object_refs": [process_object["id"]],
        "extensions": {
                "alert_name": log.get("action"),
                "correlation": corr_id,
                "rule_id": log.get("policy_name"),
                "node_info": {"node_name": node_name},
                "children": ""
            }
        }
        

    stix_objects.append(observed_data_object)
    return stix_objects


def matches(pattern, bundle, stix_version=STIX_VERSION):
    try:
        return len(match(pattern, [bundle], stix_version=stix_version)) == 1
    except Exception as e:
        print(f"Error matching pattern {pattern} to bundle {bundle}: {e}")
        raise


# When matching STIX, the relationship/indicators etc objects are read before the observed-data objects
# So, we need to make sure that the observed-data object is appended to the bundle AFTER
# Else you get the "missing endpoint" error

def transform_tetragon_to_stix(tetragon_logs):
    stix_bundles = []  
    all_stix_objects = []
    STIX_ATTACK_PATTERNS = get_attack_patterns()


    for log in tetragon_logs: 
        unique_key = log.get("md5_hash") #this is created in honeystack/vector/gkevalues.yaml
        stix_objects = []  

        if "process_exec" in log:
            stix_objects.extend(transform_kprobe_to_stix(log["process_exec"], log.get("node_name"),{})) 

        elif "process_kprobe" in log:
            stix_objects.extend(transform_kprobe_to_stix(log["process_kprobe"], log.get("node_name"),log))
        elif "BaseRuntimeMetadata" in log: 
            stix_objects.extend(transform_kubescape_to_stix(log)) 
        
        # It used to push redis here
        output_to_save = json.dumps(sanitize_bundle(stix_objects))
        all_stix_objects.extend(stix_objects)



        matching_patterns = []
        for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
            pattern, indicator_id = get_pattern(STIX_ATTACK_PATTERN)
            pattern_id = STIX_ATTACK_PATTERN["id"] 


            temp_bundle = { 
                "objects": stix_objects,  
            }

            if matches(pattern, temp_bundle):
                matching_patterns.append((indicator_id, pattern_id, STIX_ATTACK_PATTERN))



        if matching_patterns:  

            stix_bundle = { 
                "type": "bundle",
                "id": generate_stix_id("bundle"),
                "spec_version": "2.1",
                 #"name": "",
                "objects": stix_objects,  
            }
            for indicator_id, pattern_id, STIX_ATTACK_PATTERN in matching_patterns: 
                print(f"Matched pattern ID: {pattern_id}, Indicator ID: {indicator_id}")
                
                indicator_relationship = create_relationship(stix_bundle["id"], indicator_id, "indicates") #bundle -> indicator
                stix_bundle["objects"].append(indicator_relationship) 

                # Find observed-data and add indicator ref.  Ensure its the last obj.
                for obj in stix_bundle["objects"]:
                    if obj.get("type") == "observed-data":
                        obj["object_refs"].append(indicator_id)

                        break


            for _, _, STIX_ATTACK_PATTERN in matching_patterns: 
                stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])

            # It used to push redis here
            output_to_save = json.dumps(sanitize_bundle(stix_bundle))
            stix_bundles.append(stix_bundle)  

    return all_stix_objects, stix_bundles


def transform_kubescape_to_stix(log):
    print(f"Transforming kubescape log to STIX")
    base_metadata = log.get("BaseRuntimeMetadata", {})
    runtime_k8s = log.get("RuntimeK8sDetails", {})
    runtime_process = log.get("RuntimeProcessDetails", {})
    cloud_metadata = log.get("CloudMetadata", {}) or {}

    container_id = runtime_k8s.get("containerID", "")
    pid = runtime_process.get("processTree", {}).get("pid", -1)
    hostname = cloud_metadata.get("instance_id", {}) or ""
    timestamp =  base_metadata.get("timestamp", _get_current_time_iso_format())
    corr_id = generate_unique_log_id(container_id, pid, hostname, timestamp,"kubescape")
    
    stix_objects = []

    process_object = {
        "type": "process",
        "id": create_process_stix_id(corr_id), 
        "pid": pid, 
        "command_line": runtime_process.get("processTree", {}).get("cmdline", ""),
        "cwd": runtime_process.get("processTree", {}).get("cwd", ""),
        "created_time": base_metadata.get("timestamp", _get_current_time_iso_format()),
        "extensions": {
                "container_id": container_id,
                "flags": log.get("message", ""),
                "image_id":  runtime_k8s.get("image", ""),
                "pod_name": runtime_k8s.get("podName", ""),
                "namespace": runtime_k8s.get("namespace", ""),
                "function_name": log.get("RuleID", ""),
                "parent_pid":runtime_process.get("processTree", {}).get("ppid", -1),
                "parent_command_line": runtime_process.get("processTree", {}).get("pcomm", ""),
                "parent_cwd": "",
                "grand_parent_pid": "",
                "kprobe0.capability": base_metadata.get("arguments", {}).get("capability", ""),
                "kprobe1.syscall": base_metadata.get("arguments", {}).get("syscall", ""),
                "kprobe2.trace": base_metadata.get("trace", {}),
                "kprobe3.severity": base_metadata.get("severity", {}),
                "kprobe4.infectedPID": base_metadata.get("infectedPID", {})  
        }
    }
    stix_objects.append(process_object)

    current_time = log.get("time", _get_current_time_iso_format())
    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created_time": current_time,
        "first_observed": current_time,
        "last_observed": current_time,
        "number_observed": 1,
        "object_refs": [process_object["id"]],
        "extensions": {
                "alert_name": base_metadata.get("alertName", ""),
                "correlation": corr_id, 
                "rule_id": log.get("RuleID", ""),
                "node_info": hostname, #importnat Kubescape doesnt give us the full hostname of the node
                "children": runtime_process.get("processTree", {}).get("children", [])
        }
    }
    stix_objects.append(observed_data_object)

    return stix_objects

def get_attack_patterns():
    return []

def transform_tetragon_to_stix_2(tetragon_log):
    stix_objects = []
    STIX_ATTACK_PATTERNS = get_attack_patterns()
    if not tetragon_log:
        return []


    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))
        UNIQUE = tetragon_log.get("md5_hash")
        stix_objects = []

        # Initialize stix_bundle here, not inside pattern loop
        stix_bundle = {
            "type": "bundle",
            "id": generate_stix_id("bundle"),
            "spec_version": "2.1",
            "name" : "",
            "objects": [],
        }
        if "process_exec" in tetragon_log:
            stix_objects = transform_kprobe_to_stix(tetragon_log["process_exec"], tetragon_log["node_name"])
        elif "process_kprobe" in tetragon_log:
            stix_objects = transform_kprobe_to_stix(tetragon_log["process_kprobe"], tetragon_log["node_name"])
        elif "kubescape" in tetragon_log:
            stix_objects = transform_kubescape_to_stix(tetragon_log)

        matching_patterns = [] 

        for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
            try:
                temp_bundle = {  
                    "type": "bundle",
                    "id": generate_stix_id("bundle"), 
                    "spec_version": "2.1",
                    "name": "",
                    "objects": [],
                }
                temp_bundle["objects"].extend(stix_objects)
                PATTERN,ID = get_pattern(STIX_ATTACK_PATTERN)
                IDD = STIX_ATTACK_PATTERN["id"]

                if matches(PATTERN, temp_bundle):
                    matching_patterns.append((ID, IDD, STIX_ATTACK_PATTERN))  


            except Exception as e:
                print(f"Error matching pattern: {e}")


        if matching_patterns:  
            stix_bundle["objects"].extend(stix_objects)  

            for ID, IDD, STIX_ATTACK_PATTERN in matching_patterns: 
                print(f"Sanitizing matched pattern IDD {IDD} for id {ID}") 

                indicator_relationship = create_relationship(stix_bundle["id"], ID, "indicates")
                stix_bundle["objects"].append(indicator_relationship)
                for obj in stix_bundle["objects"]: 
                    if obj["type"] == "observed-data":
                        obj["object_refs"].append(ID)
                        break

                stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
                output = json.dumps(sanitize_bundle(stix_bundle))
                print(output)
            
    return stix_bundle


def compare_stix_objects(obj, objects_array):
    """Compares a STIX object to an array of STIX objects, ignoring the 'id' field.

    Args:
        obj (dict): The STIX object to compare.
        objects_array (list): The array of STIX objects to compare against.

    Returns:
        bool: True if the object already exists in the array (ignoring ID), False otherwise.
    """
    for other_obj in objects_array:
        if obj["type"] == other_obj["type"]:  # Only compare objects of the same type
            # Compare all fields except 'id', 'created', and 'modified'
            # TODO: test if the timestamp based patterns still work if we ignore these date-fields
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
