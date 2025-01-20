#!/bin/bash

# Function to check if the current user can perform an action
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

    if kubectl exec -n $namespace $pod -- $command &> /dev/null; then
        echo "Vulnerable: Command '$command' can be executed in pod $pod in namespace $namespace"
    else
        echo "Secure: Command '$command' cannot be executed in pod $pod in namespace $namespace"
    fi
}

debug_command_in_pod() {
    local namespace=$1
    local pod=$2
    local command=$4
    local im=$3

    kubectl debug --profile=general -n $namespace -it $pod --image=$im -- /bin/bash -c "$command"; 
    error_output=$(kubectl debug --profile=general -n $namespace -it $pod --image=$im -- /bin/bash -c "$command && echo SUCCESS" 2>&1 /dev/null )
    echo $error_output
    if [[ "$error_output" == *"SUCCESS"* ]]; then  
        echo "Vulnerable: Command: $command succeeded in pod $pod in namespace $namespace"
        if [[ -n "$second_command" ]]; then
            echo "Launching second attack: $second_command"
            error_output=$(kubectl debug --profile=general -n $namespace -it $pod --image=$im -- /bin/bash -c "$second_command && echo SUCCESS" 2>&1 /dev/null )
            echo $error_output
        fi
        return 1 
    else
        echo "Secure: Command: $command failed in pod $pod in namespace $namespace"
        return 0 
    fi


}

#TODO: exclude this process from the checks
check_capabilities_outside_pod() {
    output_file="all_container_caps.txt"
    temp_dir="/tmp/cap-checker-output"
    mkdir -p $temp_dir
    > $output_file
    nodes=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')

    for node in $nodes; do
        echo "Collecting capabilities from node: $node"
    
        #now we exec into the daeomonset pod on this node and check the capabilities of all containers
        p=$(kubectl get pods -l app=cap-checker -o jsonpath="{.items[?(@.spec.nodeName=='$node')].metadata.name}")
        kubectl exec -n storm $p -- /bin/sh -c "
            for pid in \$(ls /proc | grep -E '^[0-9]+$'); do
                cap_eff=\$(capsh --decode=\$(cat /proc/\$pid/status | grep CapEff | awk '{print \$2}'))
                if [ -n \"\$cap_eff\" ]; then
                    binary=\$(readlink -f /proc/\$pid/exe)
                    cmdlines=\$(cat /proc/\$pid/cmdline)
                    echo \"Binary: \$binary, Cmdline: \$cmdlines, PID: \$pid, CapEff: \$cap_eff \"
                fi
            done
        " > $temp_dir/container_caps_$node.txt

        # Append the content to the final output file
        cat $temp_dir/container_caps_$node.txt >> $output_file
    done
    cat $output_file | grep -v awk | grep -v kubectl | grep -v containerd-shim-runc-v2 |grep -v containerd| grep -v systemd| grep -v pause | grep -v kubelet  | grep -v kube-apiserver | grep -v kube-controller-manager | grep -v kube-scheduler | grep -v kube-proxy | grep -v etcd | grep -v kindnetd | grep -v coredns | grep -v local-path-provisioner 
}
# Get all namespaces
namespaces=$(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}')

declare -A attack_dictionary

attack_dictionary["CE_MODULE_LOAD"]="modprobe $(lsmod | awk 'NR==2{print $1}')"
attack_dictionary["CE_NSENTER"]="nsenter -t 1 -a /bin/bash  -c 'lsns ; exit'"
attack_dictionary["CE_PRIV_MOUNT"]="mount -t proc proc /proc"
attack_dictionary["CE_SYS_PTRACE"]="strace -ff ls"
# attack_dictionary["CE_UMH_CORE_PATTERN"]="sysctl -w kernel.core_pattern=/tmp/core && echo SUCCESS"
# attack_dictionary["CE_VAR_LOG_SYMLINK"]="ln -s / /host/var/log/root_link && echo SUCCESS"
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
        command="${attack_dictionary[$attack_name]}"
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
        fi

        if echo $manifest | jq '.spec.containers[].securityContext | select(.privileged == true or (.capabilities.add[] == "SYS_MODULE"))' > /dev/null; then
            if [ $? -eq 0 ]; then
                echo "Pod $pod in namespace $ns has cap_sys_module capability"
            else
                echo "Pod $pod in namespace $ns does not have cap_sys_module capability"
            fi
        fi


        # CE_NSENTER: Check if the user can use nsenter to escape the contianer
        attack_name="CE_NSENTER"  
        command="${attack_dictionary[$attack_name]}"
        second_command="${attack_dictionary[CE_PRIV_MOUNT]}"  #THIS IS JUST A SKETCH TODO: implement in proper language
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" "$second_command" #TODO: make it spawn inside the same shell!!! THAT MAKES MORE SENSE
        fi

        # CE_PRIV_MOUNT: Check if the user can mount filesystems
        attack_name="CE_PRIV_MOUNT"  
        command="${attack_dictionary[$attack_name]}"
        second_command="${attack_dictionary[CE_NSENTER]}" 
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" "$second_command" 
        fi


        # CE_SYS_PTRACE: Check if the user can use ptrace
        #debug_command_in_pod $ns $pod "entlein/lightening:0.0.2" "strace -ff ls " 
        attack_name="CE_SYS_PTRACE"  
        command="${attack_dictionary[$attack_name]}"
        #second_command="${attack_dictionary[CE_NSENTER]}" 
        if [[ -n "$command" ]]; then  
            debug_command_in_pod "$ns" "$pod" "entlein/lightening:0.0.2" "$command" 
        fi

        # CE_UMH_CORE_PATTERN: Check if the user can modify core pattern
        check_command_in_pod $ns $pod "sysctl -w kernel.core_pattern=/tmp/core "

        # CE_VAR_LOG_SYMLINK: Check if the user can create symlinks in /var/log
        check_command_in_pod $ns $pod "ln -s / /var/log/root_link "

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
        check_permission "attach" "pods" $ns

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