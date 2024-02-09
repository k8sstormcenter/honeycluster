import json


# Load the JSON schema
json_schema = json.loads("""
{
  "type": "object",
  "properties": {
    "process_kprobe": {
      "type": "object",
      "properties": {
        "action": {
          "type": "string"
        },
        "args": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "sock_arg": {
                "type": "object",
                "properties": {
                  "daddr": {
                    "type": "string"
                  },
                  "family": {
                    "type": "string"
                  },
                  "protocol": {
                    "type": "string"
                  },
                  "priority": {
                    "type": "string"
                  },
                  "saddr": {
                    "type": "string"
                  },
                  "sport": {
                    "type": "integer"
                  },
                  "state": {
                    "type": "string"
                  },
                  "type": {
                    "type": "string"
                  }
                },
                "required": [
                  "daddr",
                  "family",
                  "protocol",
                  "saddr",
                  "sport",
                  "state",
                  "type"
                ]
              }
            },
            "required": [
              "sock_arg"
            ]
          }
        },
        "function_name": {
          "type": "string"
        },
        "policy_name": {
          "type": "string"
        },
        "process": {
          "type": "object",
          "properties": {
            "arguments": {
              "type": "string"
            },
            "binary": {
              "type": "string"
            },
            "cwd": {
              "type": "string"
            },
            "pid": {
              "type": "integer"
            },
            "pod": {
              "type": "object",
              "properties": {
                "name": {
                  "type": "string"
                },
                "namespace": {
                  "type": "string"
                },
                "workload": {
                  "type": "string"
                },
                "workload_kind": {
                  "type": "string"
                }
              },
              "required": [
                "name",
                "namespace",
                "workload",
                "workload_kind"
              ]
            },
            "start_time": {
              "type": "string"
            }
          },
          "required": [
            "arguments",
            "binary",
            "cwd",
            "pid",
            "pod",
            "start_time"
          ]
        }
      },
      "required": [
        "action",
        "args",
        "function_name",
        "policy_name",
        "process"
      ]
    },
    "time": {
      "type": "string"
    }
  },
  "required": [
    "process_kprobe",
    "time"
  ]
}
""")

AVro: 

{
  "type": "record",
  "name": "Record",
  "fields": [
    {
      "name": "type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.action.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.daddr.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.family.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.protocol.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.priority.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.saddr.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.sport.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.state.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.properties.type.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.args.items.properties.sock_arg.required",
      "type": {
        "type": "array",
        "items": "string"
      }
    },
    {
      "name": "properties.process_kprobe.properties.args.items.required",
      "type": {
        "type": "array",
        "items": "string"
      }
    },
    {
      "name": "properties.process_kprobe.properties.function_name.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.policy_name.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.arguments.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.binary.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.cwd.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pid.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.properties.name.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.properties.namespace.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.properties.workload.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.properties.workload_kind.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.pod.required",
      "type": {
        "type": "array",
        "items": "string"
      }
    },
    {
      "name": "properties.process_kprobe.properties.process.properties.start_time.type",
      "type": "string"
    },
    {
      "name": "properties.process_kprobe.properties.process.required",
      "type": {
        "type": "array",
        "items": "string"
      }
    },
    {
      "name": "properties.process_kprobe.required",
      "type": {
        "type": "array",
        "items": "string"
      }
    },
    {
      "name": "properties.time.type",
      "type": "string"
    },
    {
      "name": "required",
      "type": {
        "type": "array",
        "items": "string"
      }
    }
  ]
}
