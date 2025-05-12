import yaml
import re
import ipaddress

def process_yaml(yaml_file, values):
    with open(yaml_file, "r") as f:
        yaml_content = f.read()

    # Substitute values in the entire YAML content
    for key, value in values.items():
        print(key, value)
        if key.islower(): 
            yaml_content = yaml_content.replace(f"$values.{key}", str(value))

    data = yaml.safe_load(yaml_content)

    # Expand CIDR in 'execs' if present
    if "spec" in data and "containers" in data["spec"]:
        containers = data["spec"]["containers"]
        for container in containers:
            if "execs" in container:
                expand_cidr_in_execs(container["execs"], values.get("CIDR"))

    output_file = "processed_" + yaml_file
    with open(output_file, "w") as f:
        yaml.dump(data, f, indent=2)
    print(f"Processed YAML written to {output_file}")

def expand_cidr_in_execs(exec_blocks, cidr):
    if not cidr:
        return

    new_exec_blocks = []
    for exec_block in exec_blocks:
        if any(cidr in arg for arg in exec_block.get("args", [])):
            new_blocks = []
            for ip in ipaddress.IPv4Network(cidr):
                new_block = exec_block.copy()
                new_args = [arg.replace(cidr, str(ip)) for arg in new_block.get("args", [])]
                new_block["args"] = new_args
                new_blocks.append(new_block)
            new_exec_blocks.extend(new_blocks)
        else:
            new_exec_blocks.append(exec_block)
    exec_blocks.clear()
    exec_blocks.extend(new_exec_blocks)


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


values = read_values_from_file("bob.values")
process_yaml("bob.yaml", values)