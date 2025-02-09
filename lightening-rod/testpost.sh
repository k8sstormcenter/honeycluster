#!/bin/bash

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "1",
  "name": "CE_NSENTER",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-nsenter",
        "name": "CE_NSENTER",
        "description": "Attempted Container Escape via NSENTER.",
        "external_references": [
          {
            "source_name": "Mitre",
            "url": "https://attack.mitre.org/techniques/T1611/",
            "description": "Usually a priviledged container can escape to the host using nsenter"
          }
        ]
      },
      {
        "type": "indicator",
        "id": "indicator--kh-ce-nsenter",
        "name": "NSenter binary executed",
        "description": "Calibration test",
        "pattern": "[process:extensions.function_name MATCHES '__x64_sys_setns' AND process:extensions.kprobe_arguments.int_arg_1 = 1073741824 ]",
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
    ]}
EOF


curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "2",
  "name": "CE_SYS_PTRACE",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--kh-ce-sys-ptrace",
      "name": "CE_SYS_PTRACE",
      "description": "Strace from inside a container."
    },
    {
        "type": "indicator",
        "id": "indicator--kh-ce-sys-ptrace",
        "name": "Ptrace System Call from Container",
        "description": "Detecting the attempted use of the 'ptrace' system call from within a container, which can be used to manipulate other processes. TODO: thats not true",
        "pattern": "[(process:extensions.function_name MATCHES '__x64_sys_ptrace' AND process:command_line MATCHES '/usr/bin/strace') OR (process:extensions.function_name MATCHES '__x64_sys_execve' AND process:extensions.kprobe_arguments.string_arg MATCHES '/usr/bin/gdb')]",
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
EOF

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "3",
  "name": "CE_PRIV_MOUNT",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--kh-ce-priv-mount",
      "name": "CE_PRIV_MOUNT",
      "description": "Mounting directories from inside a container."
    },
    {
        "type": "indicator",
        "id": "indicator--kh-ce-priv-mount",
        "name": "Mounting the /proc dir from Container",
        "description": "Detecting the mounting of the proc directory.",
        "pattern": "[process:extensions.function_name MATCHES '__x64_sys_mount' AND process:extensions.kprobe_arguments.string_arg_1 MATCHES '/proc']",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-ce-priv-mount",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-ce-priv-mount",
        "target_ref": "attack-pattern--kh-ce-priv-mount"
      }]
    }
EOF

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "5",
    "name": "CE_MODULE_LOAD",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-module-load",
        "name": "CE_MODULE_LOAD",
        "description": "Loading kernel modules from inside a container."
      },
      {
          "type": "indicator",
          "id": "indicator--kh-ce-module-load",
          "name": "Modprobe from within Container",
          "description": "Detecting an attempt to execute modprobe",
          "pattern": "[process:command_line MATCHES 'modprobe' AND process:extensions.function_name MATCHES 'sys_init_module']",
          "pattern_type": "stix",
          "valid_from": "2024-01-01T00:00:00Z"
        },
        {
          "type": "relationship",
          "id": "relationship--kh-ce-module-load",
          "relationship_type": "indicates",
          "source_ref": "indicator--kh-ce-module-load",
          "target_ref": "attack-pattern--kh-ce-module-load"
        }]
  }
EOF

  curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "4",
    "name": "CE_NET_MITM",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-net-mitm",
        "name": "CE_NET_MITM",
        "description": "Attempting to tamper with iptables and trying to run mitmdump."
      },
      {
          "type": "indicator",
          "id": "indicator--kh-ce-net-mitm",
          "name": "Person in the middle attack",
          "description": "Detecting an attempt to tamper with iptables",
          "pattern": "[process:command_line MATCHES 'iptables -t nat -A PREROUTING' AND process:command_line MATCHES 'mitmdump']",
          "pattern_type": "stix",
          "valid_from": "2024-01-01T00:00:00Z"
        },
        {
          "type": "relationship",
          "id": "relationship--kh-ce-net-mitm",
          "relationship_type": "indicates",
          "source_ref": "indicator--kh-ce-net-mitm",
          "target_ref": "attack-pattern--kh-ce-net-mitm"
        }]
  }
EOF

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "6",
    "name": "CE_VAR_LOG_SYMLINK",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-var-log-symlink",
        "name": "CE_VAR_LOG_SYMLINK",
        "description": "Arbitrary file reads on the host from a node via an exposed /var/log mount.."
      },
      {
          "type": "indicator",
          "id": "indicator--kh-ce-var-log-symlink",
          "name": "Symlink to log dir",
          "description": "Symbolic link to /var/log/root_link",
          "pattern": "[process:command_line MATCHES 'ln -s' AND process:extensions.function_name MATCHES '__x64_sys_symlinkat' OR process:extensions.kprobe_arguments.string_arg_2 MATCHES 'var/log/root_link']",
          "pattern_type": "stix",
          "valid_from": "2024-01-01T00:00:00Z"
        },
        {
          "type": "relationship",
          "id": "relationship--kh-ce-var-log-symlink",
          "relationship_type": "indicates",
          "source_ref": "indicator--kh-ce-var-log-symlink",
          "target_ref": "attack-pattern--kh-ce-var-log-symlink"
        }]
  }
EOF
curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "7",
    "name": "CE_UMH_CORE_PATTERN",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-ce-umh-core-pattern",
        "name": "CE_UMH_CORE_PATTERN",
        "description": "Exploiting the User Mode Helper Core Pattern."
      },
      {
        "type": "indicator",
        "id": "indicator--kh-ce-umh-core-pattern",
        "name": "",
        "description": "Detecting ",
        "pattern": "[process:extensions.function_name MATCHES 'security_file_permission']",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-ce-umh-core-pattern",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-ce-umh-core-pattern",
        "target_ref": "attack-pattern--kh-ce-umh-core-pattern"
      }
    ]
  }
EOF

#TODO: add the state = 110 to the indicator

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "8",
  "name": "EXPLOIT_CONTAINERD_SOCK",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--kh-exploit-containerd-sock",
      "name": "EXPLOIT_CONTAINERD_SOCK",
      "description": "Exploiting the CR socket mounted (readonly) into the container."
    },
    {
      "type": "indicator",
      "id": "indicator--kh-exploit-containerd-sock",
      "name": "",
      "description": "Detecting a socket connection by crictl",
      "pattern": "[process:extensions.function_name MATCHES 'sys_connect' AND process:extensions.kprobe_arguments.sock_arg.state MATCHES '110']",
      "pattern_type": "stix",
      "valid_from": "2024-01-01T00:00:00Z"
    },
    {
      "type": "relationship",
      "id": "relationship--exploit-containerd-sock",
      "relationship_type": "indicates",
      "source_ref": "indicator--kh-exploit-containerd-sock",
      "target_ref": "attack-pattern--kh-exploit-containerd-sock"
    }
  ]
}
EOF

curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "9",
    "name": "EXPLOIT_HOST_READ",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-exploit-host-read",
        "name": "EXPLOIT_HOST_READ",
        "description": "Exfiltration of a process memory dump."
      },
      {
        "type": "indicator",
        "id": "indicator--kh-exploit-host-read",
        "name": "",
        "description": "Detecting procdump()",
        "pattern": "[process:extensions.function_name MATCHES 'openat' AND process:command_line MATCHES 'dd']",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-exploit-host-read",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-exploit-host-read",
        "target_ref": "attack-pattern--kh-exploit-host-read"
      }
    ]
  }
EOF


curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
    "type": "bundle",
    "id": "11",
    "name": "EXPLOIT_HOST_WRITE",
    "version": "1.0.0",
    "spec_version": "2.1",
    "objects": [
      {
        "type": "attack-pattern",
        "id": "attack-pattern--kh-exploit-host-write",
        "name": "EXPLOIT_HOST_WRITE",
        "description": "Host Write to modify /etc/cron.d"
      },
      {
        "type": "indicator",
        "id": "indicator--kh-exploit-host-write",
        "name": "Host Write to modify /etc/cron.d",
        "description": "Detecting a opening the crontab on host filesystem",
        "pattern": "[process:extensions.function_name MATCHES 'openat'  AND process:extensions.kprobe_arguments.string_arg MATCHES '/etc/cron.d/breakout' ]",
        "pattern_type": "stix",
        "valid_from": "2024-01-01T00:00:00Z"
      },
      {
        "type": "relationship",
        "id": "relationship--kh-exploit-host-write",
        "relationship_type": "indicates",
        "source_ref": "indicator--kh-exploit-host-write",
        "target_ref": "attack-pattern--kh-exploit-host-write"
      }
    ]
  }
EOF

#curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "12",
  "name": "TREE",
  "version": "1.0.0",
  "spec_version": "2.1",
"objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--containerescapeplusmount",
      "name": "TREE",
      "description": "nsenter followed by mount"
    },
    {
      "type": "indicator",
      "id": "indicator--containerescapeplusmount",
      "name": "Container Escape followed by Mount /proc",
      "description": "Detecting containerescapeplusmount",
      "pattern": "[process:extensions.function_name MATCHES '__x64_sys_setns' OR process:extensions.function_name MATCHES '__x64_sys_mount']",      "pattern_type": "stix",
      "valid_from": "2024-01-01T00:00:00Z"
    },
    {
      "type": "relationship",
      "id": "relationship--containerescapeplusmount",
      "relationship_type": "indicates",
      "source_ref": "indicator--containerescapeplusmount",
      "target_ref": "attack-pattern--containerescapeplusmount"
    }
  ]
}
EOF

#curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "13",
  "name": "ESCAPEMOUNT",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--containerescapemount",
      "name": "ESCAPEMOUNT",
      "description": "nsenter followed by mount"
    },
    {
      "type": "indicator",
      "id": "indicator--containerescapemount",
      "name": "Container Escape followed by Mount /proc",
      "description": "Detecting containerescapeplusmount",
      "pattern": "[process:extensions.kprobe_arguments.int_arg_1 = 1073741824 OR process:extensions.function_name MATCHES '__x64_sys_mount']",      "pattern_type": "stix",
      "valid_from": "2024-01-01T00:00:00Z"
    },
    {
      "type": "relationship",
      "id": "relationship--containerescapemount",
      "relationship_type": "indicates",
      "source_ref": "indicator--containerescapemount",
      "target_ref": "attack-pattern--containerescapemount"
    }
  ]
}
EOF

#curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d @- << 'EOF'
{
  "type": "bundle",
  "id": "14",
  "name": "kubescapetest",
  "version": "1.0.0",
  "spec_version": "2.1",
  "objects": [
    {
      "type": "attack-pattern",
      "id": "attack-pattern--kubescapetest",
      "name": "kubescapetest",
      "description": "description kubescapetest"
    },
    {
      "type": "indicator",
      "id": "indicator--kubescapetest",
      "name": "",
      "description": "Detecting kubescapetest",
      "pattern": "[process:extensions.kprobe_arguments.flags[0] MATCHES 'RDONLY']",
      "pattern_type": "stix",
      "valid_from": "2024-01-01T00:00:00Z"
    },
    {
      "type": "relationship",
      "id": "relationship--kubescapetest",
      "relationship_type": "indicates",
      "source_ref": "indicator--kubescapetest",
      "target_ref": "attack-pattern--kubescapetest"
    }
  ]
}
EOF