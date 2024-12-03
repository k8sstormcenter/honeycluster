curl -X POST http://localhost:8000/add_attack_bundle \
-H "Content-Type: application/json" \
-d '{
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
          "source_name": "Kubehound",
          "url": "https://TODO",
          "description": "Usually a privileged container can escape to the host using nsenter"
        }
      ]
    },
    {
      "type": "indicator",
      "id": "indicator--kh-ce-nsenter",
      "name": "Container Module Loading",
      "description": "Calibration test",
      "pattern": "[process:command_line MATCHES \"/usr/bin/nsenter -t 1\"]",
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
}'