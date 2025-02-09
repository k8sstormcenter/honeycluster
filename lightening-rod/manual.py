import uuid
import json
import os
import base64
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


### first part of code (TODO: move to a separate file) routes

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
@app.route('/convert_list_to_stix', methods=['GET'])
def convert_list_to_stix():
    queue= request.args.get('queue')
    print(f"Converting list to STIX for queue: {queue}")
    tetragon_logs = client.lrange(queue, 0, -1)
    transform_tetragon_to_stix(tetragon_logs)
    return jsonify({"message": "List been converted to STIX"}), 200

@app.route('/bundle_for_viz', methods=['GET'])
def bundle_for_viz():
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    deduplicate_bundles(individual_bundles)
    return jsonify({"message": "STIX bundeling ready for visualization"}), 200

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
        "id": generate_stix_id("relationship"),
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


def create_process_stix_id(exec_id):
    if exec_id:
        try:
            decoded_exec_id = base64.b64decode(exec_id).decode('utf-8')  
            truncated_exec_id = decoded_exec_id[-36:]  
            stix_id = f"process--{truncated_exec_id}"
            return stix_id
        except Exception as e:  # Handle decoding or other errors
            print(f"Error decoding or hashing exec_id: {e}")

def flatten_kprobe_args_2(kprobe_args):
    return [str(v) for arg in kprobe_args for v in arg.values()]

def flatten_kprobe_args(args):
    flattened_args = {}
    for i, item in enumerate(args): 
        if isinstance(item, list):
            flattened_args.update(flatten_kprobe_args(item))  
        elif isinstance(item, dict):
            for k, v in item.items():
                new_key = f"{k}_{i}" if k in flattened_args else k  
                flattened_args[new_key] = v
    return flattened_args


 # THIS WOULD BE A STANDALONE PLUGIN FOR ALL THOSE USING TETRAGON
def transform_kprobe_to_stix(log, node_name):
    print(f"Transforming kprobe log to STIX")
    parent = log.get("parent", {})
    process = log.get("process", {})
    file_args = [] 
    for arg in log.get("args", []):
        file_args.append(arg)


    stix_objects = []

    parent_process_object = {
        "type": "process",
        "id": create_process_stix_id(parent.get("exec_id")),
        "pid": parent.get("pid", -1),
        "command_line": f"{parent.get('binary')} {parent.get('arguments')}",
        "cwd": parent.get("cwd"),
        "created_time": parent.get("start_time", _get_current_time_iso_format()),
    }
    stix_objects.append(parent_process_object)

    process_object = {
        "type": "process",
        "id": create_process_stix_id(process.get("exec_id")),
        "pid": process.get("pid", -1),
        "command_line": f"{process.get('binary')} {process.get('arguments')}",
        "cwd": process.get("cwd"),
        "created_time": process.get("start_time", _get_current_time_iso_format()),
        "parent_ref": parent_process_object["id"],
        "extensions": {
          #"extension-definition-kubernetes-kprobe": {  
                "extension_type": "property-extension",
                "flags": process.get("flags", ""),
                "docker": process.get("docker", ""),
                "container_id": process.get("pod", {}).get("container", {}).get("id", ""),
                "pod_name": process.get("pod", {}).get("name", ""),
                "namespace": process.get("pod", {}).get("namespace", ""),
                "function_name": log.get("function_name", ""),
                "kprobe_arguments": flatten_kprobe_args(log.get("args", []))
           # }          
        }
    }
    stix_objects.append(process_object)
    parent_child_relationship = create_relationship(
        parent_process_object["id"], process_object["id"], "parent-child"
    )
    stix_objects.append(parent_child_relationship)

    current_time = log.get("time", _get_current_time_iso_format())
    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created": current_time,
        "modified": current_time,
        "first_observed": current_time,
        "last_observed": current_time,
        "number_observed": 1,
        "object_refs": [process_object["id"], parent_process_object["id"]],
        "extensions": {
            #"extension-definition--kubernetes-metadata": {  
                "extension_type": "property-extension",
                "alert_name": log.get("policy_name"),
                "arguments": "",
                "rule_id": "",
                "node_info": {"node_name": node_name},
                "children": ""
            }
            #}
        }
        

    stix_objects.append(observed_data_object)
    return stix_objects

def transform_kubescape_to_stix(log):
    print(f"Transforming kubescape log to STIX")
    base_metadata = log.get("BaseRuntimeMetadata", {})
    runtime_k8s = log.get("RuntimeK8sDetails", {})
    runtime_process = log.get("RuntimeProcessDetails", {})
    cloud_metadata = log.get("CloudMetadata", {})
    
    stix_objects = []
    parent_process_object = {
        "type": "process",
        "id": generate_stix_id("process"),
        "pid": runtime_process.get("processTree", {}).get("ppid", -1),
        "command_line": runtime_process.get("processTree", {}).get("pcomm", ""),
        "cwd":"",
        "created_time": base_metadata.get("timestamp", _get_current_time_iso_format()),
    }
    stix_objects.append(parent_process_object)

    process_object = {
        "type": "process",
        "id": generate_stix_id("process"), # unfortunately kubescape doesnt capture something to
        "pid": runtime_process.get("processTree", {}).get("pid", -1), 
        "command_line": runtime_process.get("processTree", {}).get("cmdline", ""),
        "cwd": runtime_process.get("processTree", {}).get("cwd", ""),
        "created_time": base_metadata.get("timestamp", _get_current_time_iso_format()),
        "parent_ref": parent_process_object["id"],
        "extensions": {
           # "extension-definition-kubernetes-kprobe": { 
                "extension_type": "property-extension",
                "container_id": runtime_k8s.get("containerID", ""),
                "flags": log.get("message", ""),
                "docker":  runtime_k8s.get("image", ""),
                "pod_name": runtime_k8s.get("podName", ""),
                "namespace": runtime_k8s.get("namespace", ""),
                "function_name": log.get("RuleID", ""),
                "kprobe_arguments": base_metadata.get("arguments", {}) #might need to flatten
           # }
        }
    }
    stix_objects.append(process_object)

    # Create Observed Data object
    current_time = log.get("time", _get_current_time_iso_format())
    observed_data_object = {
        "type": "observed-data",
        "id": generate_stix_id("observed-data"),
        "created_time": current_time,
        "first_observed": current_time,
        "last_observed": current_time,
        "number_observed": 1,
        "object_refs": [process_object["id"], parent_process_object["id"]],
        "extensions": {
            #"extension-definition--kubernetes-metadata": {  
                "extension_type": "property-extension",
                "alert_name": base_metadata.get("alertName", ""),
                "arguments": base_metadata.get("arguments", {}),
                "rule_id": log.get("RuleID", ""),
                "node_info": cloud_metadata.get("instance_id", {}),
                "children": runtime_process.get("processTree", {}).get("children", [])
           # }
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
            stix_objects.extend(transform_kprobe_to_stix(log["process_exec"], log.get("node_name"))) 

        elif "process_kprobe" in log:
            stix_objects.extend(transform_kprobe_to_stix(log["process_kprobe"], log.get("node_name"))) 
        elif "BaseRuntimeMetadata" in log: 
            stix_objects.extend(transform_kubescape_to_stix(log)) 
        
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