#!/bin/bash

# Set variables
NAMESPACE="harbor"
RELEASE_NAME="harbor"
OUTPUT_FILE="topology.dot"
IMAGE_FILE="topology.png"

# Get the list of resources deployed by the Helm chart
kubectl get all -n $NAMESPACE -l "release=$RELEASE_NAME" -o json > resources.json

# Generate the DOT file
echo "digraph G {" > $OUTPUT_FILE
echo "  rankdir=LR;" >> $OUTPUT_FILE

# Parse the JSON and generate the graph description
jq -r '.items[] | "\(.kind) \(.metadata.name)"' resources.json | while read -r line; do
  KIND=$(echo $line | awk '{print $1}')
  NAME=$(echo $line | awk '{print $2}')
  echo "  \"$KIND: $NAME\";" >> $OUTPUT_FILE
done

# Add relationships (e.g., Pods to Services)
jq -r '.items[] | select(.kind == "Pod") | "\(.metadata.name) \(.spec.containers[].name)"' resources.json | while read -r line; do
  POD=$(echo $line | awk '{print $1}')
  CONTAINER=$(echo $line | awk '{print $2}')
  echo "  \"Pod: $POD\" -> \"Container: $CONTAINER\";" >> $OUTPUT_FILE
done

echo "}" >> $OUTPUT_FILE

# Generate the diagram using Graphviz
dot -Tpng $OUTPUT_FILE -o $IMAGE_FILE

# Clean up
rm resources.json