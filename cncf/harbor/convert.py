import json

# Path to your JSON file
json_file_path = 'resources.json'

# Read the JSON file
with open(json_file_path, 'r') as file:
    json_content = json.load(file)

# Convert JSON content to a string
json_string = json.dumps(json_content)

# Print the JSON string (optional)
print(json_string)

# Now you can use the json_string in your Colab notebook