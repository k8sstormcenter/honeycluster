import uuid
import json
import os
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
REDIS_BUNDLEVISKEY = os.getenv('REDIS_BUNDLEVISKEY', 'tetrastix')
REDIS_PATTERNKEY = os.getenv('REDIS_PATTERNKEY', 'tetra_pattern')


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

@app.route('/convert_to_stix', methods=['GET'])
def convert_to_stix():
    offset = int(request.args.get('i', 30)) 
    # Read Tetragon logs from Redis #yes, this is not a secure way to query a DB, please fix
    tetragon_logs = client.lrange(REDIS_KEY, -offset, -1)
    #extract the hash from each log
    bundle = transform_tetragon_to_stix(tetragon_logs)


    #now as a second step we bundle the bundles
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    trees = group_bundles(individual_bundles)
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
    #return datetime.utcnow().isoformat(timespec="microseconds") + "Z"
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

def validate_stix_bundle(bundle):
    """
    Validates a STIX bundle to ensure all objects have IDs.

    Args:
        bundle (dict): The STIX bundle as a dictionary.

    Returns:
        bool: True if the bundle is valid, False otherwise.
    """
    if not isinstance(bundle, dict):
        print("Error: Bundle is not a dictionary.")
        return False

    if "objects" not in bundle:
        print("Error: Bundle does not contain 'objects' key.")
        return False

    for obj in bundle["objects"]:
        if not isinstance(obj, dict):
            print("Error: Object is not a dictionary.", obj)
            return False
        if "id" not in obj or not obj["id"]:  # Corrected check
            print("Error: Object is missing an ID or has an empty ID.", obj)
            return False
        # Check if 'id' is a valid STIX ID (optional but recommended)
        if not obj["id"].startswith(("indicator--", "attack-pattern--", "observed-data--", "file--", "process--", "bundle--", "relationship--")):
             print(f"Invalid STIX ID format: {obj['id']}")
             return False

    return True





def transform_process_to_stix(log):
    parent = log.get("parent", {})
    process = log.get("process", {})
    file_arg = next(
        (
            arg.get("file_arg", {}).get("path")
            for arg in log.get("args", [])
            if "file_arg" in arg
        ),
        None,
    )

    parent_image_name = parent.get("binary", "").split("/")[-1]
    process_image_name = process.get("binary", "").split("/")[-1]

    parent_file_id = generate_stix_id("file") if parent_image_name else None
    process_file_id = generate_stix_id("file") if process_image_name else None
    file_arg_id = generate_stix_id("file") if file_arg else None

    stix_objects = []

    if parent_image_name:
        stix_objects.append(
            {"type": "file", "id": parent_file_id, "name": parent_image_name}
        )

    if process_image_name:
        stix_objects.append(
            {"type": "file", "id": process_file_id, "name": process_image_name}
        )

    if file_arg:
        stix_objects.append({"type": "file", "id": file_arg_id, "name": file_arg})

    parent_process_object = {
        "type": "process",
        "id": generate_stix_id("process"),
        "pid": parent.get("pid", -1),
        "command_line": f"{parent.get('binary')} {parent.get('arguments')}",
        "cwd": parent.get("cwd"),
        "created_time": parent.get("start_time", _get_current_time_iso_format()),
        "image_ref": parent_file_id,
        "extensions": {"flags": parent.get("flags", "")},
    }
    stix_objects.append(parent_process_object)

    process_object = {
        "type": "process",
        "id": generate_stix_id("process"),
        "pid": process.get("pid", -1),
        "command_line": f"{process.get('binary')} {process.get('arguments')}",
        "cwd": process.get("cwd"),
        "created_time": process.get("start_time", _get_current_time_iso_format()),
        "image_ref": process_file_id,
        "parent_ref": parent_process_object["id"],
        "extensions": {
            "flags": process.get("flags", ""),
            "docker": process.get("docker", ""),
            "container_id": process.get("pod", {}).get("container", {}).get("id", ""),
            "pod_name": process.get("pod", {}).get("name", ""),
            "namespace": process.get("pod", {}).get("namespace", ""),
        },
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
        "extensions": {"node_info": {"node_name": log.get("node_name")}},
    }

    #if parent_file_id:
    #    observed_data_object["object_refs"].append(parent_file_id)
    #if process_file_id:
    #    observed_data_object["object_refs"].append(process_file_id)
    #if file_arg_id:
    #    observed_data_object["object_refs"].append(file_arg_id)

    stix_objects.append(observed_data_object)
    # Create relationship between observed-data and process, parent process, files
    for obj_ref in observed_data_object["object_refs"]:
        observed_data_relationship = create_relationship(
            observed_data_object["id"], obj_ref, "refers-to"
        )
        stix_objects.append(observed_data_relationship)

    return stix_objects



def matches(pattern, bundle, stix_version=STIX_VERSION):
    try:
        return len(match(pattern, [bundle], stix_version=stix_version)) == 1
    except Exception as e:
        print(f"Error matching pattern {pattern} to bundle {bundle}: {e}")
        raise

def transform_tetragon_to_stix(tetragon_log):
    stix_objects = []
    STIX_ATTACK_PATTERNS = get_attack_patterns()
    if not tetragon_log:
        return []
   
    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))  # Decode bytes to string
        UNIQUE = tetragon_log.get("md5_hash")
        stix_objects = []
        # We need to bundle the observables differently 
        stix_bundle = {
            "type": "bundle",
            "id": generate_stix_id("bundle"),
            "spec_version": "2.1",
            "objects": [],
        }
        if "process_exec" in tetragon_log:
            stix_objects = transform_process_to_stix(tetragon_log["process_exec"])

        elif "process_kprobe" in tetragon_log:
            stix_objects = transform_process_to_stix(tetragon_log["process_kprobe"])
        # Now we have each individual logs in STIX observable format
        # we test if it matches any known indicator
        # if yes, then we append it to the bundle accordingly
        for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
            try:
                stix_bundle["objects"].extend(stix_objects)
                PATTERN,ID =get_pattern(STIX_ATTACK_PATTERN)
                IDD= STIX_ATTACK_PATTERN["id"]
                if matches(PATTERN, stix_bundle):
            #         #for each pattern we check if an observable matches and write all matches to redis after appending the STIX_PATTERN ID to the observed-data.object_refs list
                    redis_key = f"{REDIS_OUTKEY}:{ID}:{UNIQUE}"
                    indicator_relationship = create_relationship(
                            stix_bundle["id"], ID, "indicates"  # Assuming "indicates" relationship
                        )
                    stix_bundle["objects"].append(indicator_relationship)
                    for obj in stix_bundle["objects"]:
                        if obj["type"] == "observed-data":
                            obj["object_refs"].append(ID)
                            break 
                    #for obj in STIX_ATTACK_PATTERN["objects"]:
                    #    if obj["type"] == "relationship": #we add the relationship from the attack pattern here
                    #        stix_bundle["objects"].append(obj)

                    if validate_stix_bundle(stix_bundle):
                       client.hset(REDIS_BUNDLEKEY,f"{IDD}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle)))
                    stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
                    if validate_stix_bundle(stix_bundle):
                       client.rpush(redis_key, json.dumps(sanitize_bundle(stix_bundle)))
                    #now we write the bundle to redis for the visualization to the viskey
                       client.hset(REDIS_VISKEY,f"{ID}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle)))
                    #print(f"Writing to Redis key: {REDIS_VISKEY}")
            except Exception as e:
                print(f"Error extending bundle in tranform_tetragon_to_stix: {e}")

    return stix_bundle



def group_bundles(individual_bundles):
    STIX_ATTACK_PATTERNS = get_attack_patterns()
    stix_bundle_array = {} #maybe the python dict is not the best data structure for this
    for key, value in individual_bundles.items():
        stix_bundle = json.loads(value)
        k= key.decode('utf-8').split(":")[0]
        ID = int(k) #the ID is the first part of the key
 
        # Now we sort the bundles by the ID
        #if the ID hasnt been seen before we create the header
        if ID not in  stix_bundle_array:
            stix_bundle_array[ID] = {
                "type": "bundle",
                "id": generate_stix_id("bundle"),
                "name": str(ID),
                "spec_version": "2.1",
                "objects": [],
            }
        stix_bundle_array[ID]["objects"].extend(stix_bundle["objects"])
    # Now we are done with all the observed-data objects in one bundle per attack pattern, we finally appent only once the header
    for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
        ID= int(STIX_ATTACK_PATTERN["id"])
        PATTERN,LONGID =get_pattern(STIX_ATTACK_PATTERN)
        if ID  in  stix_bundle_array:
            stix_bundle_array[ID]["objects"].extend(STIX_ATTACK_PATTERN["objects"])
            #for obj in stix_bundle_array[ID]["objects"]:
            #    if obj["type"] == "relationship":
            #        obj["object_refs"].append(LONGID)
            #        break 
            if validate_stix_bundle(stix_bundle_array[ID]):
                client.hset(REDIS_BUNDLEVISKEY,f"{ID}:{LONGID}", json.dumps(sanitize_bundle(stix_bundle_array[ID])))

    return stix_bundle_array


def get_hash(tetragon_log):
    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))
        unique=tetragon_log.get("md5_hash")
    return unique


def main():
    """Parse a tetragon log in json format from a file and print its
    STIX representation in json format to stdout"""


    # Read Tetragon logs from Redis
    tetragon_logs = client.lrange(REDIS_KEY, -50, -1)
    #extract the hash from each log
    bundle = transform_tetragon_to_stix(tetragon_logs)

    #now as a second step we bundle the bundles
    individual_bundles = client.hgetall(REDIS_BUNDLEKEY)
    trees = group_bundles(individual_bundles)




if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)