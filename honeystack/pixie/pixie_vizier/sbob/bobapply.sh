#!/bin/bash
for file in *_bob.yaml; do
    kubectl apply -f $file;
done
