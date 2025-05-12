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


values = read_values_from_file("bob.values")
process_yaml("bob.yaml", values)