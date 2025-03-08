import uuid
import json
import os
import base64
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import redis
from stix2matcher.matcher import match
from stix2 import Bundle, Process, Indicator, Relationship
from stix2patterns.v21 import pattern


# Initialize Flask app
app = Flask(__name__)


# Constants
STIX_VERSION = '2.1'
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_KEY = os.getenv('REDIS_KEY', 'tetra')
REDIS_OUTKEY = os.getenv('REDIS_OUTKEY', 'tetrasingle')
REDIS_VISKEY = os.getenv('REDIS_VISKEY', 'tetrastix2')
REDIS_BUNDLEKEY = os.getenv('REDIS_BUNDLEKEY', 'tetra_bundle')
REDIS_KUBESCAPEKEY = os.getenv('REDIS_KUBESCAPEKEY', 'kubescape')
REDIS_TRACEEKEY = os.getenv('REDIS_TRACEEKEY', 'tracee')
REDIS_FALCOKEY = os.getenv('REDIS_FALCOKEY', 'falco')
REDIS_BUNDLEVISKEY = os.getenv('REDIS_BUNDLEVISKEY', 'tetrastix') #implement in UI
REDIS_FOLLOWVISKEY = os.getenv('REDIS_FOLLOWVISKEY', 'tetraproc')
REDIS_PATTERNKEY = os.getenv('REDIS_PATTERNKEY', 'tetra_pattern')
REDIS_DEBUGKEY = os.getenv('REDIS_DEBUGKEY', 'tetra_debug')
PROCESS_EXT_KEY = "process-ext"
OBSERVED_DATA_EXT_KEY = "observed-data-ext"



# Global client to DB
client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


# in this app you can calibrate the attack patterns that you will use in the real time processing
# so, you have the kubehound-stix.json as a reference, but its very trivial
# The real patterns should be stored in Redis for efficient processing
# You can test them one by one or all at once
# Once you are happy with your set of patterns, you should persist them to MongoDB 

# TODO: rewrite as WASM components


### first part of code (TODO: move to a separate file) routes

# route of type redis-state-management
@app.route('/wipesafe', methods=['GET'])
def wipesafe():
    try:
        keys_to_delete = [REDIS_BUNDLEKEY, REDIS_VISKEY, REDIS_BUNDLEVISKEY] 
        for key in keys_to_delete:
            client.delete(key)  
        return jsonify({"message": "Specified Redis keys deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# lets deduce which type of logs we are dealing with by looking at the queue-name
# the Bundles should all be in a form that can be deduplicated, no matter the original log source

## route of type data-transform-unspecific
## while we pass the name of queue, which determines the datasource, it is not specific
## it can be run in parallel for different queues 
## TODO: input validation :) 
## TODO: implement an actual queue (this was abandoned after node and pythons queue libs were incompatible)
## TODO: this function will fail is the redis-key is too large, thus queue/chunking/pagination 
@app.route('/convert_list_to_stix', methods=['GET'])
def convert_list_to_stix():
    queue= request.args.get('queue')
    print(f"Converting list to STIX for queue: {queue}")
    tetragon_logs = client.lrange(queue, 0, -1)
    transform_tetragon_to_stix(tetragon_logs)
    return jsonify({"message": "List been converted to STIX"}), 200
## route of type data-transform-unspecific
@app.route('/bundle_for_viz', methods=['GET'])
def bundle_for_viz():
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    deduplicate_bundles(individual_bundles)
    return jsonify({"message": "STIX bundeling ready for visualization"}), 200



## route of type configure-transformation-unspecific
@app.route('/add_attack_bundle', methods=['POST'])
def add_attack_bundle():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        #count the number of keys in the bundle and add one
        #important that you use contiguous integers as keys
        bundle_id = str(len(client.hgetall(REDIS_PATTERNKEY)) + 1)
        client.hset(REDIS_PATTERNKEY, bundle_id, json.dumps(data))
        return jsonify({"message": "STIX attack bundle added successfully", "bundle_id": bundle_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_attack_bundles', methods=['GET'])
def get_attack_bundles():
    try:
        bundles = client.hgetall(REDIS_PATTERNKEY)
        bundles = {k.decode('utf-8'): json.loads(v) for k, v in bundles.items()}
        return jsonify(bundles), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_attack_bundle/<bundle_id>', methods=['DELETE'])
def delete_attack_bundle(bundle_id):
    try:
        client.hdel(REDIS_BUNDLEKEY, bundle_id)
        return jsonify({"message": "STIX bundle deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



## Second part of code (TODO: move to a separate file) function definitions

#In absence of a database, we will use a JSON file to provide some attack patterns
# TODO: this is outdated -> use the testpost.sh instead
def get_attack_patterns():
    try:
        attack_patterns = client.hgetall(REDIS_PATTERNKEY)
        if not attack_patterns:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(script_dir, 'kubehound-stix.json')

            with open(json_file_path, 'r') as file:
                STIX_ATTACK_PATTERNS = json.load(file)
        else:
            STIX_ATTACK_PATTERNS = [json.loads(v.decode('utf-8')) for v in attack_patterns.values()]
        return STIX_ATTACK_PATTERNS
    except Exception as e:
        print(f"Error retrieving attack patterns: {e}")
        return []

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



def flatten_tracee_args(args, prefix=None):
    flattened_args = {}
    if isinstance(args, dict): 
        for key, value in args.items():
            new_key = f"{prefix}_{key}" if prefix else key
            if isinstance(value, dict):
                flattened_args.update(flatten_tracee_args(value, new_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    flattened_args.update(flatten_tracee_args(item, f"{new_key}[{i}]"))
            else:
                flattened_args[new_key] = value
    elif isinstance(args, list):  
        for i, item in enumerate(args):
            flattened_args.update(flatten_tracee_args(item, f"{prefix}_{i}" if prefix else str(i)))
    else: 
        flattened_args[prefix] = args if prefix else args

    return flattened_args



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
    print(f"Transforming kprobe log to STIX")
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

def transform_tracee_to_stix(log):
    container = log.get("container", {})
    kubernetes = log.get("kubernetes", {})
    metadata = log.get("metadata", {}).get("Properties", {})
    event_time = log.get("timestamp", None)
    if event_time: 
       event_time = datetime.utcfromtimestamp(event_time / 1e9).isoformat(timespec="milliseconds") + "Z"

    container_id = container.get("id", "")
    pid = log.get("processId", -1)
    hostname = log.get("hostName", "") or ""
    corr_id = generate_unique_log_id(container_id, pid, hostname, event_time,"tracee")
    stix_objects = []

    process_object = {
        "type": "process",
        "id": create_process_stix_id(corr_id),
        "pid": pid,
        "command_line": log.get("processName", ""),
        "cwd": "",  # Not available in Tracee
        "created_time": event_time or _get_current_time_iso_format(),
        "extensions": {
                "container_id": container_id,
                "flags": "", #for tracee those will be in the nested args
                "image_id": container.get("image", ""),
                "pod_name": kubernetes.get("podName", ""),
                "namespace": kubernetes.get("podNamespace", ""),
                "function_name": log.get("syscall", ""),  
                "kprobe_arguments": flatten_tracee_args(log.get("args", ""))
        }
    }
    stix_objects.append(process_object)

    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created": event_time or _get_current_time_iso_format(),
        "modified": event_time or _get_current_time_iso_format(),
        "first_observed": event_time or _get_current_time_iso_format(),
        "last_observed": event_time or _get_current_time_iso_format(),
        "number_observed": 1,
        "object_refs": [process_object["id"], metadata.get("id", "")], #need to link in the tracee attack-pattern definitions
        "extensions": {
                "alert_name": metadata.get("signatureName", ""),
                "correlation": corr_id,
                "interpretation": f"{metadata.get('Category', '')} {metadata.get('Technique', '')} {metadata.get('external_id', '')}",
                "rule_id": metadata.get("signatureID", ""),
                "node_info": hostname,
                "children": "", #not provided by tracee
        }
    }
    stix_objects.append(observed_data_object)

    return stix_objects



def transform_falco_to_stix(log):
    process = log.get("interesting", {})
    event_time = log.get("timestamp", None)
    container_id = process.get("container.id","")
    pid = process.get("proc.tty", -1) # That is NOT the PID, we dont have the PID and for some reason adding the field to output doesnt work, PLEASE HELP
    hostname = log.get("hostname", "") 
    corr_id = generate_unique_log_id(container_id, pid, hostname, event_time,"falco")
    stix_objects = []

    process_object = {
        "type": "process",
        "id": create_process_stix_id(corr_id),
        "pid": pid,
        "command_line": f"{process.get("proc.commandline")}",
        "cwd": process.get("proc.exepath", ""),
        "created_time": process.get("evt.time", _get_current_time_iso_format()),
        "extensions": {
                "flags": process.get("evt.arg.flags", ""),
                "image_id": f"{process.get("container.image.repository")} {process.get('container.image.tag')}",
                "container_id": container_id,
                "pod_name": process.get("k8s.pod.name", ""),
                "namespace": process.get("k8s.pod.namespace", ""),
                "function_name": log.get("evt.type", ""),
                "parent_pid": process.get("proc.ppid", -1),#that one doesnt exist either
                "parent_command_line": f"{process.get('proc.pname')}",
                "kprobe0.fdl4proto": process.get("fd.l4proto", ""),
                "kprobe1.fdname": process.get("fd.name", ""),
                "kprobe2.fdtype": process.get("fd.type", ""),
                "kprobe3.evtres": process.get("evt.res", ""),
                "kprobe4.username": process.get("user.name", ""),      
        }
    }
    stix_objects.append(process_object)

    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created": event_time or _get_current_time_iso_format(),
        "modified": event_time or _get_current_time_iso_format(),
        "first_observed": event_time or _get_current_time_iso_format(),
        "last_observed": event_time or _get_current_time_iso_format(),
        "number_observed": 1,
        "object_refs": [process_object["id"]], #need to link in the tracee attack-pattern definitions
        "extensions": {
                "alert_name": log.get("priority", ""),
                "correlation": corr_id,
                "interpretation": ", ".join(log.get("tags", [])),
                "rule_id": log.get("rule", ""),
                "node_info": hostname,
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

def transform_tetragon_to_stix(tetragon_log):
    stix_bundles = []  
    STIX_ATTACK_PATTERNS = get_attack_patterns()


    for log_string in tetragon_log: 
        try:
            log = json.loads(log_string.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"Skipping invalid JSON log entry: {e}")
            continue

        unique_key = log.get("md5_hash") #this is created in honeystack/vector/gkevalues.yaml
        stix_objects = []  

        if "process_exec" in log:
            stix_objects.extend(transform_kprobe_to_stix(log["process_exec"], log.get("node_name"),{})) 

        elif "process_kprobe" in log:
            stix_objects.extend(transform_kprobe_to_stix(log["process_kprobe"], log.get("node_name"),log))
        elif "BaseRuntimeMetadata" in log: 
            stix_objects.extend(transform_kubescape_to_stix(log)) 
        elif "matchedPolicies" in log:
            stix_objects.extend(transform_tracee_to_stix(log))
        elif "interesting" in log:
            stix_objects.extend(transform_falco_to_stix(log))
        
        #DEBUG: insert into REDISDEBUG the stix_objects at this point -> turn off for production
        client.hset(REDIS_DEBUGKEY, f"{unique_key}", json.dumps(sanitize_bundle(stix_objects)))



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

            client.hset(REDIS_BUNDLEKEY, f"{pattern_id}:{unique_key}", json.dumps(sanitize_bundle(stix_bundle)))
            stix_bundles.append(stix_bundle)  

    return stix_bundles




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
                print(f"Writing to Redis key: {REDIS_BUNDLEKEY}, matched pattern IDD {IDD} for id {ID}") 

                indicator_relationship = create_relationship(stix_bundle["id"], ID, "indicates")
                stix_bundle["objects"].append(indicator_relationship)
                for obj in stix_bundle["objects"]: 
                    if obj["type"] == "observed-data":
                        obj["object_refs"].append(ID)
                        break

                stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
                client.hset(REDIS_BUNDLEKEY,f"{IDD}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle))) # Store unique bundles
            
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


def deduplicate_bundles(individual_bundles):
    stix_bundle_array = {} 
    for key, value in individual_bundles.items():
        stix_bundle = json.loads(value)
        #print(f"Processing bundle {key}: {stix_bundle}")
        ID = int(key.decode('utf-8').split(":")[0])
        if ID not in  stix_bundle_array:
            stix_bundle_array[ID] = {
                "type": "bundle",
                "id": stix_bundle["id"],
                #"name": stix_bundle["name"],
                "spec_version": "2.1",
                "objects": stix_bundle["objects"],
            }
        else:
            # we extend those objects that we have NOT already seen
            for obj in stix_bundle["objects"]:
                if compare_stix_objects(obj, stix_bundle_array[ID]["objects"]):
                    #print(f"Object already exists in bundle {ID}: {obj}")
                    continue
                else:
                    stix_bundle_array[ID]["objects"].append(obj)

        client.hset(REDIS_BUNDLEVISKEY,f"{ID}", json.dumps(sanitize_bundle(stix_bundle_array[ID])))    
    return stix_bundle_array




#def process_follow_bundles(individual_bundles):
def deduplicate_bundles_proc(individual_bundles):
    stix_bundle_array = {} 
    for key, value in individual_bundles.items():
        stix_bundle = json.loads(value)
        #The ID is either the process ID or the parent ID and we use it to group any matches that share either
        #print(f"Processing bundle {key}: {stix_bundle}")
        ID= stix_bundle["objects"][0]["id"] #thats the parent ID (for kprobes)

        if ID not in  stix_bundle_array:
            stix_bundle_array[ID] = {
                "type": "bundle",
                "id": stix_bundle["id"],
                #"name": stix_bundle["name"],
                "spec_version": "2.1",
                "objects": stix_bundle["objects"],
            }
        else:
            for obj in stix_bundle["objects"]:
                if compare_stix_objects(obj, stix_bundle_array[ID]["objects"]):
                    #print(f"Object already exists in bundle {ID}: {obj}")
                    continue
                else:
                    stix_bundle_array[ID]["objects"].append(obj)

        client.hset(REDIS_FOLLOWVISKEY,f"{ID}", json.dumps(sanitize_bundle(stix_bundle_array[ID])))    
    return stix_bundle_array

def get_hash(tetragon_log):
    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))
        unique=tetragon_log.get("md5_hash")
    return unique


def main():
    """Parse a tetragon log in json format from a file and print its
    STIX representation in json format to stdout"""


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)