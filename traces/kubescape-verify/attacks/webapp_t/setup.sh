##https://github.com/kubescape/node-agent/blob/3bc7b274b2f5b297818b5cefcfbea1d69c0d87a6/demo/general_attack/webapp/setup.sh
#!/bin/bash

# Kill any existing port forwards
echo "[+] Killing any existing port forwards"
killall kubectl 2>/dev/null
# Check if port 58080 is in use and kill the process if necessary
if sudo lsof -i :8080 >/dev/null 2>&1; then
    echo "[+] Port 8080 is in use. Killing the process using it."
    sudo kill -9 $(sudo lsof -t -i :8080)
fi

# Apply the YAML file for the web app
echo "[+] Applying YAML file for the web app"
kubectl apply -f ~/honeycluster/traces/kubescape-verify/attacks/webapp_t/webapp.yaml
#kubectl apply -f ~/honeycluster/traces/kubescape-verify/attacks/webapp_t/applicationprofile.yaml

# Wait for the web app to be ready
echo "[+] Waiting for the web app to be ready"
kubectl wait --for=condition=ready pod -l app=webapp

# Port forward from port 80 to port localhost:58080
echo "[+] Port forwarding from port 80 to localhost:8080"
kubectl port-forward svc/webapp 8080:80 2>&1 >/dev/null &



# Wait for the port forward to be ready
echo "[+] Waiting for the port forward to be ready"
sleep 1
echo "[+] The web app is ready, you can curl it like so: curl -k localhost:8080/ping.php?ip=172.16.0.2"
