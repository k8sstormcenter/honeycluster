import uuid
import json
import os
from datetime import datetime
import redis
from stix2matcher.matcher import match
from stix2 import Bundle, Process, Indicator
from stix2patterns.v21 import pattern

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_KEY = 'tetra'
REDIS_OUTKEY = 'tetrasingle'
REDIS_VISKEY = 'tetrastix'

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
json_file_path = os.path.join(script_dir, 'kubehound-stix.json')

# Read the JSON file
# here we should paramterize on attack type (which kubehound edge) so we can later parallelize the processing
with open(json_file_path, 'r') as file:
    STIX_ATTACK_PATTERNS = json.load(file)

def generate_stix_id(type):
    return f"{type}--{uuid.uuid4()}"


def _get_current_time_iso_format():
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


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


#STIX_PATTERN="[process:binary = '/usr/bin/nsenter' AND process:arguments = '-t 1 -a sleep 300' AND process:cwd = '/']"
STIX_PATTERN = "[process:command_line = '/usr/bin/nsenter -t 1 -a bash']"
STIX_PATTERNS = {
        "[process:command_line = '/usr/bin/nsenter -t 1 -a bash']": "NSENTER Container Escape",
        "[file:name = '/etc/shadow']": "Access to Shadow File",
        # Add more patterns here...
    }

OBSERVABLE_STIX_BUNDLE_EXAMPLE2 = {
    "type": "bundle",
    "id": "bundle--0749b3fa-5f45-41fc-b132-15f909b0e855",
    "spec_version": "2.1",
    "objects": [
        {
            "type": "file",
            "id": "file--cc48c445-caaa-41ed-a067-9333c7841cc3",
            "name": "tini"
        },
        {
            "type": "file",
            "id": "file--ce73aa8b-a8eb-4fd0-b492-cc90103ec689",
            "name": "rancher"
        },
        {
            "type": "file",
            "id": "file--d6fa1f7f-867f-4023-91ab-c63281be2243",
            "name": "/run/secrets/kubernetes.io/serviceaccount/..2024_05_30_17_59_36.871209644/token"
        },
        {
            "type": "process",
            "id": "process--9690fcaa-f707-44e1-a9ea-2341a4304c8a",
            "pid": None,
            "command_line": "/usr/bin/tini -- rancher --http-listen-port=80 --https-listen-port=443 --audit-log-path=/var/log/auditlog/rancher-api-audit.log --audit-level=1 --audit-log-maxage=1 --audit-log-maxbackup=1 --audit-log-maxsize=100 --no-cacerts --http-listen-port=80 --https-listen-port=443 --add-local=true",
            "cwd": "/var/lib/rancher",
            "created_time": None,
            "image_ref": "file--cc48c445-caaa-41ed-a067-9333c7841cc3",
            "extensions": {
                "flags": "procFS auid"
            }
        },
        {
            "type": "process",
            "id": "process--07176c3f-4514-4114-b764-572bea195d62",
            "pid": None,
            "command_line": "/usr/bin/nsenter -t 1 -a bash",
            "cwd": "/",
            "created_time": None,
            "image_ref": "file--ce73aa8b-a8eb-4fd0-b492-cc90103ec689",
            "parent_ref": "process--9690fcaa-f707-44e1-a9ea-2341a4304c8a",
            "extensions": {
                "flags": "procFS auid",
                "docker": "7bd7197f085f946549f2e4fa0c28489",
                "container_id": "containerd: //7bd7197f085f946549f2e4fa0c28489cf179745364be4c174bd96673061b10bd",
                "pod_name": "rancher-55966c8d68-f56sc",
                "namespace": "cattle-system"
            }
        },
        {
            "type": "observed-data",
            "id": "observed-data--c4bd5cf6-86da-4446-bd76-25da430e9498",
            "created": None,
            "modified": None,
            "first_observed": "2024-03-30T18:14:23.507328Z",
            "last_observed": "2024-03-30T18:14:23.507328Z",
            "number_observed": 1,
            "object_refs": [
                "process--07176c3f-4514-4114-b764-572bea195d62",
                "process--9690fcaa-f707-44e1-a9ea-2341a4304c8a",
                "file--cc48c445-caaa-41ed-a067-9333c7841cc3",
                "file--ce73aa8b-a8eb-4fd0-b492-cc90103ec689",
                "file--d6fa1f7f-867f-4023-91ab-c63281be2243"
            ]
        }
    ]
}

STIX_ATTACK_PATTERNS = [{
  "type": "bundle",
  "id": "bundle--kubehound-attack-CE_NSENTER",
  "name": "CE_NSENTER",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-nsenter",
        "name": "CE_NSENTER",
        "description": "Container Escape via NSENTER.",
        "external_references": [
          {
            "source_name": "Kubehound",
            "url": "https://TODO",
            "description": "Usually a priviledged container can escape to the host using nsenter"
          }
        ]
      },
      {
        "type": "indicator",
        "id": "indicator--kh-ce-nsenter",
        "name": "Container Module Loading",
        "description": "Calibration test",
        "pattern": "[process:command_line = '/usr/bin/nsenter -t 1 -a bash']",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-ce-nsenter",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-ce-nsenter",
        "target_ref": "attack-pattern--kh-ce-nsenter"
      }
    ]},
{
  "type": "bundle",
  "id": "bundle--kubehound-attack-CE_SYS_PTRACE",
  "name": "CE_SYS_PTRACE",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--kh-ce-sys-ptrace",
      "name": "CE_SYS_PTRACE",
      "description": "Using ptrace for process manipulation from a container."
    },
    {
        "type": "indicator",
        "id": "indicator--kh-ce-sys-ptrace",
        "name": "Ptrace System Call from Container",
        "description": "Detecting the use of the 'ptrace' system call from within a container, which can be used to manipulate other processes.",
        "pattern": "[process:command_line MATCHES '/usr/bin/gdb']",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-ce-sys-ptrace",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-ce-sys-ptrace",
        "target_ref": "attack-pattern--kh-ce-sys-ptrace"
      }]
}
]

STIX_ATTACK_PATTERN= {
    "type": "bundle",
    "id": "bundle--kubehound-attacks",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-nsenter",
        "name": "CE_NSENTER",
        "description": "Use NSENTER to Escape to HOST",
        "external_references": [
          {
            "source_name": "Kubehound",
            "url": "https://github.com/turbot/steampipe-mod-aws-compliance/blob/main/controls/cis-kubernetes-v1.6.0/controls/5.1.5.go",
            "description": "Control to ensure that the admission control plugin PodSecurityPolicy is set."
          }
        ]
      },
      {
          "type": "attack-pattern",
          "id": "attack-pattern--kh-ce-nsenter",
          "name": "CE_NSENTER",
          "description": "Container Escape via NSENTER.",
          "external_references": [
            {
              "source_name": "Kubehound",
              "url": "https://TODO",
              "description": "Calibration test"
            }
          ]
        },
        {
          "type": "indicator",
          "id": "indicator--kh-ce-nsenter",
          "name": "Container Module Loading",
          "description": "Calibration test",
          "pattern": "[process:command_line = '/usr/bin/nsenter -t 1 -a bash']",
          "pattern_type": "stix",
          "valid_from": "2024-01-01T00:00:00Z"
        },
        {
          "type": "relationship",
          "id": "relationship--kh-ce-nsenter",
          "relationship_type": "indicates",
          "source_ref": "indicator--kh-ce-nsenter",
          "target_ref": "attack-pattern--kh-ce-nsenter"
        }
      ]
}

#needs to return the PATTERN and the ID from the indicator block
def get_pattern(STIX_ATTACK_PATTERN):
    for obj in STIX_ATTACK_PATTERN["objects"]:
        if obj["type"] == "indicator":
            return obj["pattern"], obj["id"]  # Return both pattern and id
    return None, None
    


def transform_process_exec_to_stix(log):
    parent = log.get("parent", {})
    process = log.get("process", {})

    parent_image_name = parent.get("binary", "").split("/")[-1]
    process_image_name = process.get("binary", "").split("/")[-1]

    parent_file_id = generate_stix_id("file") if parent_image_name else None
    process_file_id = generate_stix_id("file") if process_image_name else None

    stix_objects = []

    if parent_image_name:
        stix_objects.append(
            {"type": "file", "id": parent_file_id, "name": parent_image_name}
        )

    if process_image_name:
        stix_objects.append(
            {"type": "file", "id": process_file_id, "name": process_image_name}
        )

    parent_process_object = {
        "type": "process",
        "id": generate_stix_id("process"),
        "pid": parent.get("pid", -1),
        "command_line": f"{parent.get('binary')} {parent.get('arguments')}",
        "cwd": parent.get("cwd"),
        "created_time": parent.get("start_time", _get_current_time_iso_format()),
        "image_ref": parent_file_id,
        "extensions": {
            "flags": parent.get("flags", ""),
            "parent_exec_id": parent.get("parent_exec_id", ""),
        },
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
    if parent_file_id:
        observed_data_object["object_refs"].append(parent_file_id)
    if process_file_id:
        observed_data_object["object_refs"].append(process_file_id)

    stix_objects.append(observed_data_object)

    return stix_objects


def transform_process_kprobe_to_stix(log):
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

    if parent_file_id:
        observed_data_object["object_refs"].append(parent_file_id)
    if process_file_id:
        observed_data_object["object_refs"].append(process_file_id)
    if file_arg_id:
        observed_data_object["object_refs"].append(file_arg_id)

    stix_objects.append(observed_data_object)

    return stix_objects

STIX_VERSION = '2.1'

def matches(pattern, bundle, stix_version=STIX_VERSION):
    try:
        return len(match(pattern, [bundle], stix_version=stix_version)) == 1
    except Exception as e:
        print(f"Error matching pattern {pattern} to bundle {bundle}: {e}")
        raise

def transform_tetragon_to_stix(tetragon_log):

    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


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
            stix_objects = transform_process_exec_to_stix(tetragon_log["process_exec"])

        elif "process_kprobe" in tetragon_log:
            stix_objects = transform_process_kprobe_to_stix(tetragon_log["process_kprobe"])
        # Now we have each individual logs in STIX observable format
        # we test if it matches any known indicator
        # if yes, then we append it to the bundle accordingly
        for STIX_ATTACK_PATTERN in STIX_ATTACK_PATTERNS:
            try:
                stix_bundle["objects"].extend(stix_objects)
                PATTERN,ID =get_pattern(STIX_ATTACK_PATTERN)
                if matches(PATTERN, stix_bundle):
                    print("success")
            #         #for each pattern we check if an observable matches and write all matches to redis after appending the STIX_PATTERN ID to the observed-data.object_refs list
                    redis_key = f"{REDIS_OUTKEY}:{ID}:{UNIQUE}"
                    stix_bundle["objects"].extend(STIX_ATTACK_PATTERN["objects"])
                    print(stix_bundle["objects"])
                    for obj in stix_bundle["objects"]:
                        if obj["type"] == "observed-data":
                            obj["object_refs"].append(ID)
                            break 
                    #TODO: The Stix Attack Pattern must be a list of many attack patterns (currently one)
                    client.rpush(redis_key, json.dumps(sanitize_bundle(stix_bundle)))
                    #now we write the bundle to redis for the visualization to the viskey
                    client.hset(REDIS_VISKEY,f"{ID}:{UNIQUE}", json.dumps(sanitize_bundle(stix_bundle)))
                    print(f"Writing to Redis key: {REDIS_VISKEY}")
            except Exception as e:
                print(f"Error extending bundle: {e}")

    return stix_bundle


def get_hash(tetragon_log):
    for log in tetragon_log:
        tetragon_log = json.loads(log.decode('utf-8'))
        unique=tetragon_log.get("md5_hash")
    return unique


def main():
    """Parse a tetragon log in json format from a file and print its
    STIX representation in json format to stdout"""
    # Connect to Redis
    client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)


    # Read Tetragon logs from Redis
    tetragon_logs = client.lrange(REDIS_KEY, 0, -1)
    #extract the hash from each log
    bundle = transform_tetragon_to_stix(tetragon_logs)

    #print(json.dumps(sanitize_bundle(bundle), indent=4))

    # print(json.dumps(sanitize_bundle(bundle), indent=4))
    # Now for each record in Redis we write the Observable back into th
    #r.json().set("your_key", "$", json_document)
    #docker run -it --rm -p 6666:6379  redis/redis-stack
    #client2 = redis.Redis(host=REDIS_HOST, port=6666)
    #client2.json().set( "tetratest", "$", json.dumps(sanitize_bundle(bundle)))


if __name__ == "__main__":
    main()