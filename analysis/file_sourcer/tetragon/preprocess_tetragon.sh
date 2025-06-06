#!/bin/bash

input_file="${1:-tetragon.log}"
output_file="${2:-tetragon.json}"

if [ ! -f "$input_file" ]; then
  echo "❌ Input file $input_file not found. Exiting."
  exit 1
fi

> "$output_file" # Clear output file first

while IFS= read -r line; do
  # Find all keys except time and node_name
  type=$(echo "$line" | jq -r 'keys_unsorted[]' | grep -vE '^(time|node_name)$')

  if [ -z "$type" ]; then
    echo "⚠️ Skipping line, no extra field found."
    continue
  fi

  # Extract fields
  time=$(echo "$line" | jq -r '.time')
  node_name=$(echo "$line" | jq -r '.node_name')
  payload=$(echo "$line" | jq -c ".\"$type\"")

  # Build clean JSON
  echo "{\"time\": \"$time\", \"node_name\": \"$node_name\", \"type\": \"$type\", \"payload\": $payload}" >> "$output_file"
done < "$input_file"

echo "✅ Preprocessing done! Output: $output_file"

echo "Moving output file to Minikube..."
minikube cp tetragon.json /home/docker/tetragon.json
echo "✅ Moved the file succesfully!"