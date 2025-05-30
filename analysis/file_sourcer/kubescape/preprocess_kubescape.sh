#!/bin/bash

# Default values
input_file="kubescape.log"
output_file="kubescape.json"
time_flag=""

print_help() {
  echo ""
  echo "Usage: $0 [input_file] [output_file] [--time=now|<ISO_TIME>]"
  echo ""
  echo "Positional arguments:"
  echo "  input_file         (optional) Log file to read, default: kubescape.log"
  echo "  output_file        (optional) Output file path, default: kubescape.json"
  echo ""
  echo "Optional flags:"
  echo "  --time=now         Use current UTC time for all entries"
  echo "  --time=<ISO_TIME>  Use a specific ISO 8601 timestamp"
  echo "  -h, --help         Show this help message and exit"
  echo ""
  exit 0
}

# Parse args
positional_args=()

for arg in "$@"; do
  case $arg in
    -h|--help)
      print_help
      ;;
    --time=now)
      time_flag=$(date -u +"%Y-%m-%dT%H:%M:%S.%NZ")
      ;;
    --time=*)
      time_flag="${arg#*=}"
      ;;
    *)
      positional_args+=("$arg")
      ;;
  esac
done

# Assign positional args if provided
if [ ${#positional_args[@]} -ge 1 ]; then
  input_file="${positional_args[0]}"
fi
if [ ${#positional_args[@]} -ge 2 ]; then
  output_file="${positional_args[1]}"
fi

# Check input file exists
if [ ! -f "$input_file" ]; then
  echo "❌ Input file $input_file not found. Exiting."
  exit 1
fi

while IFS= read -r line; do
  # If the line is empty, skip
  if [ -z "$line" ]; then continue; fi

  # Convert nulls to "null" strings at root level
  cleaned=$(echo "$line" | jq -c 'with_entries(if .value == null then .value = "null" else . end)')

  # Overwrite time field if time flag is provided
  if [ -n "$time_flag" ]; then
    cleaned=$(echo "$cleaned" | jq -c --arg t "$time_flag" '.time = $t')
  fi

  echo "$cleaned" >> "$output_file"
done < "$input_file"

echo "✅ Preprocessing done! Output: $output_file"

echo "Moving output file to Minikube..."
minikube cp "$output_file" /home/docker/kubescape.json
echo "✅ Moved the file successfully!"
