import uuid
import json
import os
import re
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import redis
import asyncio
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
REDIS_BUNDLEVISKEY = os.getenv('REDIS_BUNDLEVISKEY', 'tetrastix')
REDIS_PATTERNKEY = os.getenv('REDIS_PATTERNKEY', 'tetra_pattern')
PROCESS_EXT_KEY = "process-ext"
OBSERVED_DATA_EXT_KEY = "observed-data-ext"



# Global client to DB
client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


# in this app you can calibrate the attack patterns that you will use in the real time processing
# so, you have the kubehound-stix.json as a reference, but its very trivial
# The real patterns should be stored in Redis for efficient processing
# You can test them one by one or all at once
# Once you are happy with your set of patterns, you should persist them to MongoDB 
# Furture features will also include a backup/restore option to file
# In a future enterprise version, you will be able to let the AI/RAG generate the patterns for you

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

@app.route('/convert_single_to_stix', methods=['GET'])
def convert_single_to_stix():
    tetragon_log= request.args.get('log')
    stix = transform_single_tetragon_to_stix(tetragon_log)
    return stix, 200

@app.route('/convert_list_to_stix', methods=['GET'])
def convert_list_to_stix():
    queue= request.args.get('queue')
    tetragon_logs = client.lrange(queue, 0, -1)
    transform_tetragon_to_stix(tetragon_logs)
    return jsonify({"message": "List been converted to STIX"}), 200

@app.route('/bundle_for_viz', methods=['GET'])
def bundle_for_viz():
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    deduplicate_bundles(individual_bundles)
    return jsonify({"message": "STIX bundeling ready for visualization"}), 200

@app.route('/convert_to_stix', methods=['GET'])
async def convert_to_stix():
    start = int(request.args.get('start', 30)) #TODO test if negative values work
    stop = int(request.args.get('stop', 0))
    REDIS_KEY = request.args.get('r', 'tetra')
    tetragon_logs = client.lrange(REDIS_KEY, -start, stop)
    transform_tetragon_to_stix(tetragon_logs)
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    deduplicate_bundles(individual_bundles)
    #trees = group_bundles(individual_bundles)
    return jsonify({"message": "STIX conversion successful"}), 200

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
def get_attack_patterns():
    try:
        attack_patterns = client.hgetall(REDIS_PATTERNKEY)
        if not attack_patterns:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            json_file_path = os.path.join(script_dir, 'kubehound-stix.json')

            # Read the JSON file
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
        "spec_version": STIX_VERSION,  # Ensure consistent version
        "id": generate_stix_id("relationship"),
        "created": _get_current_time_iso_format(),  # Add created/modified timestamps
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
        # Validate exec_id loosely (adjust regex if needed) – At least has to be non-empty string
        if re.match(r"^[\w\d\-:]+$", exec_id): # Alphanumeric, hyphen, colon, underscore allowed
            truncated_exec_id = exec_id[-36:]  # Truncate to max 36 chars
            stix_id = f"process--{truncated_exec_id}"
            return stix_id
    return generate_stix_id("process")

def flatten_kprobe_args(args):
    flattened_args = {}
    for item in args:
        if isinstance(item, list):
            flattened_args.update(flatten_kprobe_args(item)) 
        elif isinstance(item, dict):
            flattened_args.update(item) 
    return flattened_args



def transform_process_to_stix(log, node_name):
    parent = log.get("parent", {})
    process = log.get("process", {})
    file_args = [] 
    for arg in log.get("args", []):
        file_args.append(arg)

   # parent_image_name = parent.get("binary", "").split("/")[-1]
   # process_image_name = process.get("binary", "").split("/")[-1]
   # parent_file_id = generate_stix_id("file") if parent_image_name else None
   # process_file_id = generate_stix_id("file") if process_image_name else None
   # file_arg_id = generate_stix_id("file") if file_args else None

    stix_objects = []
   # if parent_image_name:
   #     stix_objects.append(
   #         {"type": "file", "id": parent_file_id, "name": parent_image_name}
   #     )

   # if process_image_name:
   #     stix_objects.append(
   #         {"type": "file", "id": process_file_id, "name": process_image_name}
   #     )

    # file_args:
    #    stix_objects.append({"type": "file", "id": file_arg_id, "name": file_args[0], "extensions": file_args})

    parent_process_object = {
        "type": "process",
        "id": create_process_stix_id(parent.get("exec_id")),
        "pid": parent.get("pid", -1),
        "command_line": f"{parent.get('binary')} {parent.get('arguments')}",
        "cwd": parent.get("cwd"),
        "created_time": parent.get("start_time", _get_current_time_iso_format()),
        #"image_ref": parent_file_id # Josef: what was the idea here?
    }
    stix_objects.append(parent_process_object)

    process_object = {
        "type": "process",
        "id": create_process_stix_id(process.get("exec_id")),
        "pid": process.get("pid", -1),
        "command_line": f"{process.get('binary')} {process.get('arguments')}",
        "cwd": process.get("cwd"),
        "created_time": process.get("start_time", _get_current_time_iso_format()),
        #"image_ref": process_file_id,
        "parent_ref": parent_process_object["id"],
        "extensions": {
                "flags": process.get("flags", ""),
                "docker": process.get("docker", ""),
                "container_id": process.get("pod", {}).get("container", {}).get("id", ""),
                "pod_name": process.get("pod", {}).get("name", ""),
                "namespace": process.get("pod", {}).get("namespace", ""),
                "function_name": log.get("function_name", ""),
                "kprobe_arguments": flatten_kprobe_args(log.get("args", []))             
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
                "node_info": {"node_name": node_name }
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

# #TODO Paralallize this function
# def transform_single_tetragon_to_stix(log):
#     stix_objects = []
#     STIX_ATTACK_PATTERNS = get_attack_patterns()
#     tetragon_log = json.loads(log)
#     print(tetragon_log)
#     UNIQUE = tetragon_log.get("md5_hash")
#     stix_objects = []
#     stix_bundle = {
#         "type": "bundle",
#         "id": generate_stix_id("bundle"),
#         "spec_version": "2.1",
#         "name" : "",
#         "objects": [],
#     }
#     if "process_exec" in tetragon_log:
#         stix_objects = transform_process_to_stix(tetragon_log["process_exec"], tetragon_log["node_name"])

#     elif "process_kprobe" in tetragon_log:
#         stix_objects = transform_process_to_stix(tetragon_log["process_kprobe"],tetragon_log["node_name"])
#     # Now we have each individual logs in STIX observable format
#     # we test if it matches any known indicator
#     # if yes, then we append it to the bundle accordingly
#     for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
#         try:
#             stix_bundle["objects"].extend(stix_objects)
#             PATTERN,ID =get_pattern(STIX_ATTACK_PATTERN)
#             IDD= STIX_ATTACK_PATTERN["id"]
#             stix_bundle["name"] = ID
#             print(json.dumps(stix_bundle, indent=4)) 
#             if matches(PATTERN, stix_bundle):
#                 print(f"Writing to Redis key: {REDIS_BUNDLEKEY}")
#                 indicator_relationship = create_relationship(
#                         stix_bundle["id"], ID, "indicates"  
#                     )
#                 stix_bundle["objects"].append(indicator_relationship)
#                 for obj in stix_bundle["objects"]:
#                     if obj["type"] == "observed-data":
#                         obj["object_refs"].append(ID)
#                         break 

#                 stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
#                 client.hset(REDIS_BUNDLEKEY,f"{IDD}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle)))
#         except Exception as e:
#             print(f"Error extending bundle in tranform_tetragon_to_stix: {e}")

#     return stix_bundle


def transform_tetragon_to_stix(tetragon_log):
    stix_objects = []
    STIX_ATTACK_PATTERNS = get_attack_patterns()
    if not tetragon_log:
        return []

    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))  # Decode bytes to string
        UNIQUE = tetragon_log.get("md5_hash")
        stix_objects = []
        hasmatched = False
        # We need to bundle the observables differently 
        stix_bundle = {
            "type": "bundle",
            "id": generate_stix_id("bundle"),
            "spec_version": "2.1",
            "name" : "",
            "objects": [],
        }
        if "process_exec" in tetragon_log:
            stix_objects = transform_process_to_stix(tetragon_log["process_exec"], tetragon_log["node_name"])

        elif "process_kprobe" in tetragon_log:
            stix_objects = transform_process_to_stix(tetragon_log["process_kprobe"], tetragon_log["node_name"])
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
                PATTERN,ID =get_pattern(STIX_ATTACK_PATTERN)
                IDD= STIX_ATTACK_PATTERN["id"]
                stix_bundle["name"] = ID
                #print(json.dumps(stix_bundle, indent=4)) 
                if matches(PATTERN, temp_bundle):
                    if hasmatched:
                        continue
                    else: 
                        hasmatched = True
                        stix_bundle["objects"].extend(stix_objects)
                    redis_key = f"{REDIS_OUTKEY}:{ID}:{UNIQUE}"
                    print(f"Writing to Redis key: {REDIS_BUNDLEKEY}")
                    indicator_relationship = create_relationship(
                            stix_bundle["id"], ID, "indicates"  # Assuming "indicates" relationship
                        )
                    stix_bundle["objects"].append(indicator_relationship)
                    for obj in stix_bundle["objects"]:
                        if obj["type"] == "observed-data":
                            obj["object_refs"].append(ID)
                            break 

                    stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
                    client.hset(REDIS_BUNDLEKEY,f"{IDD}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle)))
            except Exception as e:
                print(f"Error extending bundle in tranform_tetragon_to_stix: {e}")

    return stix_bundle

#TODO: implement a slice that follows process exec ids


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
                "name": stix_bundle["name"],
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