#!/bin/bash

# Defaults
input_file="kubescape_schema_init.json"
output_file="kubescape.json"

print_help() {
  echo ""
  echo "Usage: $0 [input_file] [output_file]"
  echo ""
  echo "Positional arguments:"
  echo "  input_file         (optional) File to grab first line from (default: example_kubescape_schema.json)"
  echo "  output_file        (optional) File to write the first line into (default: kubescape.json)"
  echo ""
  echo "This script copies only the first line from the input file into the output file,"
  echo "moves it into Minikube, and then runs a px script."
  echo ""
  echo "Example:"
  echo "  $0                                 # Use defaults"
  echo "  $0 myfile.json init.json           # Custom input/output"
  echo ""
  exit 0
}

# Handle args
positional_args=()

for arg in "$@"; do
  case $arg in
    -h|--help)
      print_help
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

# Check input file
if [ ! -f "$input_file" ]; then
  echo "❌ Input file $input_file not found. Exiting."
  exit 1
fi

# Create output with first line of input
head -n 1 "$input_file" > "$output_file"
echo "✅ Created $output_file with first line from $input_file"

# Copy to Minikube
echo "Moving $output_file to Minikube..."
minikube cp "$output_file" "/tmp/$output_file"
echo "✅ Moved the file successfully!"

# Run px script
echo "Running ingest script..."
px run -f ingest_kubescape.pxl
