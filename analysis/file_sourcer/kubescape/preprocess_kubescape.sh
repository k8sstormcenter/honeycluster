#!/bin/bash

# Default values
input_file="mockkubescape.log"
output_file="kubescape.json"
time_flag=""

print_help() {
  echo ""
  echo "Usage: $0 [input_file] [output_file] [--time=now|<ISO_TIME>]"
  echo ""
  echo "Positional arguments:"
  echo "  input_file         (optional) Log file to read, default: mockkubescape.log"
  echo "  output_file        (optional) Output file path, default: kubescape.json"
  echo ""
  echo "Optional flags:"
  echo "  --time=now         Use current UTC time for all entries"
  echo "  --time=<ISO_TIME>  Use a specific ISO 8601 timestamp"
  echo "  -h, --help         Show this help message and exit"
  echo ""
  echo "If --time is not provided, the script uses the 'time' field from each JSON line."
  echo ""
  echo "Examples:"
  echo "  $0                             # Uses defaults"
  echo "  $0 input.log                   # Custom input, default output"
  echo "  $0 input.log out.json          # Custom input & output"
  echo "  $0 --time=now                  # Default files, use current time"
  echo "  $0 in.log out.json --time=... # Full custom run"
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

# > "$output_file" # Uncomment if you want to clear the output first

while IFS= read -r line; do
  # Find all keys except time and node_name
  type=$(echo "$line" | jq -r 'keys_unsorted[]' | grep -vE '^(time|node_name)$')

  if [ -z "$type" ]; then
    echo "⚠️ Skipping line, no extra field found."
    continue
  fi

  # Use provided time if set, else fallback to time in line
  if [ -n "$time_flag" ]; then
    time="$time_flag"
  else
    time=$(echo "$line" | jq -r '.time')
  fi

  node_name=$(echo "$line" | jq -r '.node_name')
  payload=$(echo "$line" | jq -c ".\"$type\"")

  # Build clean JSON
  echo "{\"time\": \"$time\", \"node_name\": \"$node_name\", \"type\": \"$type\", \"payload\": $payload}" >> "$output_file"
done < "$input_file"

echo "✅ Preprocessing done! Output: $output_file"

echo "Moving output file to Minikube..."
minikube cp "$output_file" /home/docker/kubescape.json
echo "✅ Moved the file successfully!"
