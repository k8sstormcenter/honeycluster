#!/bin/bash
for file in *.yaml; do
    kubectl apply -f $file;
done
