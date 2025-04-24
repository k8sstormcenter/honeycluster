##https://github.com/kubescape/node-agent/blob/3bc7b274b2f5b297818b5cefcfbea1d69c0d87a6/demo/general_attack/webapp/setup.sh
#!/bin/bash

# Kill any existing port forwards
echo "[+] Killing any existing port forwards"
killall kubectl 2>/dev/null
if sudo lsof -i :58080 >/dev/null 2>&1; then
    echo "[+] Port 58080 is in use. Killing the process using it."
    sudo kill -9 $(sudo lsof -t -i :58080)
fi

# Apply the YAML file for the web app
echo "[+] Applying YAML file for the web app"
kubectl apply -f ~/honeycluster/traces/kubescape-verify/attacks/webapp_debug_k0s/webapp.yaml
kubectl apply -f ~/honeycluster/honeystack/kubescape/kscloudconfig.yaml

# Wait for the web app to be ready
echo "[+] Waiting for the web app to be ready"
kubectl wait --for=condition=ready pod -l app=webapp
kubectl wait --for=condition=Available deployment/webapp 

# Port forward from port 80 to port localhost:58080
echo "[+] Port forwarding from port 80 to localhost:58080"
#kubectl port-forward pod/webapp 58080:80 2>&1 >/dev/null &
export port=$(kubectl describe svc/webapp | grep NodePort | awk '{print $3}' | cut -d '/' -f1)
echo "NodePort is: $port"
kubectl port-forward svc/webapp 58080:80 2>&1 >/dev/null &
#sudo socat TCP-LISTEN:58080,bind=172.16.0.2,reuseaddr,fork TCP:127.0.0.1:58080&


# Wait for the port forward to be ready
echo "[+] Waiting for the port forward to be ready"
sleep 1
echo "[+] The web app is ready, you can curl it like so: curl -k 172.16.0.2:$port/"
# echo "[+] The web app is ready, you can curl it like so: curl -k localhost:8080/"

# in zsh curl -k localhost:8080/ping.php\?ip=172.16.0.2
