import yaml
import re


def appProfile_to_Bob():
    with open("bob_compare.yaml", "r") as f:
        data = yaml.safe_load(f)

    parameter_map = {
        "namespace": data["metadata"]["namespace"],
        "name": data["metadata"]["labels"]["kubescape.io/workload-name"],
        "clustername": data["metadata"]["annotations"]["kubescape.io/wlid"].split("//")[1].split("/")[0].split("cluster-")[1], # Extract clustername from wlid
        "templatehash": data["metadata"]["labels"]["kubescape.io/instance-template-hash"],
        "workloadkind": data["metadata"]["labels"]["kubescape.io/workload-kind"].lower(),
        "camelworkloadkind": data["metadata"]["labels"]["kubescape.io/workload-kind"],
        "instancekind": data["metadata"]["name"].split("-")[0],
        "camelinstancekind": data["kind"],
    }

    output_file = "bob_generated.values"
    with open(output_file, "w") as f:
        for key, value in parameter_map.items():
            f.write(f"{key}={value}\n")
    print(f"Processed BoB Values written to {output_file}")


    data["metadata"]["annotations"]["kubescape.io/instance-id"] = "apiVersion-apps/v1/namespace-$values.namespace/kind-$values.camelinstancekind/name-$values.name-$values.templatehash"
    data["metadata"]["annotations"]["kubescape.io/wlid"] = "wlid://cluster-$values.clustername/namespace-$values.namespace/$values.workloadkind-$values.name"
    data["metadata"]["labels"]["kubescape.io/workload-kind"] = "$values.camelworkloadkind"
    data["metadata"]["labels"]["kubescape.io/workload-name"] = "$values.name"
    data["metadata"]["labels"]["kubescape.io/workload-namespace"] = "$values.namespace"
    data["metadata"]["name"] = "$values.instancekind-$values.name-$values.templatehash"
    data["metadata"]["namespace"] = "$values.namespace"
    data["resourceVersion"] = '"1"' 


    output_file = "bob_generated.yaml"
    with open(output_file, "w") as f:
        yaml.dump(data, f, indent=2)
    print(f"Processed BoB YAML written to {output_file}")


def process_yaml(yaml_file, values):
    with open(yaml_file, "r") as f:
        yaml_content = f.read()


    for key, value in values.items():
        print(key, value)
        if key.islower(): 
            yaml_content = yaml_content.replace(f"$values.{key}", str(value))

    data = yaml.safe_load(yaml_content)


    output_file = "processed_" + yaml_file
    with open(output_file, "w") as f:
        yaml.dump(data, f, indent=2)
    print(f"Processed YAML written to {output_file}")



def read_values_from_file(values_file):
    values = {}
    with open(values_file, "r") as f:
        for line in f:
            # Use regex to handle potential spaces around the '='
            match = re.match(r"([a-zA-Z0-9_-]+)\s*=\s*(.*)", line)
            if match:
                key, value = match.groups()
                values[key] = value.strip()  # Remove leading/trailing whitespace
    return values

appProfile_to_Bob()
values = read_values_from_file("bob_generated.values")
process_yaml("bob_generated.yaml", values)