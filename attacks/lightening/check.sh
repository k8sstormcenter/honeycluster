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

# Function to check if a command can be executed in a pod
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

    if kubectl debug -n $namespace -it $pod --image=$im -- $command &> /dev/null; 
    then
        echo "Vulnerable: Command '$command' can be executed via image $im in pod $pod in namespace $namespace"
    else
        echo "Secure: Command '$command' cannot be executed via image $im in pod $pod in namespace $namespace"
    fi
}
# Get all namespaces
namespaces=$(kubectl get namespaces -o jsonpath='{.items[*].metadata.name}')

# Iterate over all namespaces
#for ns in $namespaces; do
for ns in default; do
    echo "Processing namespace: $ns"

    # Get all pods in the namespace
    pods=$(kubectl get pods -n $ns -o jsonpath='{.items[*].metadata.name}')

    # Check for various vulnerabilities
    for pod in $pods; do
        echo "Processing pod: $pod"
        manifest=$(kubectl get pod $pod -n $ns -o json)


        # CE_MODULE_LOAD: Check if the user can load kernel modules -> better to check in /lib/modules
        check_command_in_pod $ns $pod "lsmod | awk 'NR==2{print \$1}' | xargs -I {} modprobe {}"
        debug_command_in_pod $ns $pod "entlein/lightening:0.0.2" "lsmod && modprobe $(lsmod | awk 'NR==2{print $1}')"
        if echo $manifest | jq '.spec.containers[].securityContext | select(.privileged == true or (.capabilities.add[] == "SYS_MODULE"))' > /dev/null; then
            echo "Checking CE_MODULE_LOAD for pod: $pod"
            debug_command_in_pod $ns $pod "entlein/lightening:0.0.2"  "capsh --decode=$(cat /proc/self/status | grep CapEff | awk '{print $2}' )| grep cap_sys_module"
            if [ $? -eq 0 ]; then
                echo "Pod $pod in namespace $ns has cap_sys_module capability"
            else
                echo "Pod $pod in namespace $ns does not have cap_sys_module capability"
            fi
        fi


        # CE_NSENTER: Check if the user can use nsenter to enter namespaces
        check_command_in_pod $ns $pod "nsenter --help"

        # CE_PRIV_MOUNT: Check if the user can mount filesystems
        check_command_in_pod $ns $pod "mount"

        # CE_SYS_PTRACE: Check if the user can use ptrace
        check_command_in_pod $ns $pod "strace -p 1"

        # CE_UMH_CORE_PATTERN: Check if the user can modify core pattern
        check_command_in_pod $ns $pod "sysctl -w kernel.core_pattern=/tmp/core"

        # CE_VAR_LOG_SYMLINK: Check if the user can create symlinks in /var/log
        check_command_in_pod $ns $pod "ln -s / /host/var/log/root_link"

        # CONTAINER_ATTACH: Check if the user can attach to containers
        check_permission "attach" "pods" $ns

        # IDENTITY_IMPERSONATE: Check if the user can impersonate other users
        check_permission "impersonate" "users" $ns

        # POD_CREATE: Check if the user can create pods
        check_permission "create" "pods" $ns

        # POD_EXEC: Check if the user can exec into pods
        check_permission "exec" "pods" $ns

        # EXPLOIT_CONTAINERD_SOCK: Check if the user can access containerd socket
        check_command_in_pod $ns $pod "ls /run/containerd/containerd.sock"

        # EXPLOIT_HOST_READ: Check if the user can read host files
        check_command_in_pod $ns $pod "cat /host/etc/passwd"

        # EXPLOIT_HOST_TRAVERSE: Check if the user can traverse host directories
        check_command_in_pod $ns $pod "ls /host"

        # EXPLOIT_HOST_WRITE: Check if the user can write to host files
        check_command_in_pod $ns $pod "echo 'test' > /host/tmp/testfile"

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
        check_command_in_pod $ns $pod "ps aux"

        # TOKEN_BRUTEFORCE: Check if the user can brute force tokens
        check_command_in_pod $ns $pod "curl -X POST -d 'token=...' http://kubernetes.default.svc"

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