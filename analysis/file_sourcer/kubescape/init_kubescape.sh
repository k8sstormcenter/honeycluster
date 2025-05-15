#!/bin/bash

 > "kubescape2.json"

head -n 1 example_kubescape_schema.json > "kubescape2.json"

echo "Moving init file to Minikube..."
minikube cp kubescape.json /home/docker/kubescape.json
echo "✅ Moved the file succesfully!"

px run -f ingest_kubescape.pxl