#!/bin/bash
namespace="pl"
list=$(kubectl get applicationprofiles.spdx.softwarecomposition.kubescape.io -n $namespace| grep -v NAME| cut -d ' ' -f1)
for file in $list; do
    kubectl get -n $namespace applicationprofiles  $file -o yaml >~/bob$file.yaml ;
done
