#!/bin/bash

echo "Moving init file to Minikube..."
minikube cp example_tetragon_schema.json /home/docker/tetragon.json
echo "✅ Moved the file succesfully!"

px run -f ingest_tetragon.pxl