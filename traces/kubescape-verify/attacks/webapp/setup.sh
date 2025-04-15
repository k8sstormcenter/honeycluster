##https://github.com/kubescape/node-agent/blob/3bc7b274b2f5b297818b5cefcfbea1d69c0d87a6/demo/general_attack/webapp/setup.sh
#!/bin/bash

# Kill any existing port forwards
echo "[+] Killing any existing port forwards"
killall kubectl 2>/dev/null

# Apply the YAML file for the web app
echo "[+] Applying YAML file for the web app"
kubectl apply -f ~/honeycluster/traces/kubescape-verify/attacks/webapp/webapp.yaml

# Wait for the web app to be ready
echo "[+] Waiting for the web app to be ready"
kubectl wait --for=condition=ready pod -l app=ping-app

# Port forward from port 80 to port localhost:58080
echo "[+] Port forwarding from port 80 to localhost:58080"
kubectl port-forward pod/ping-app 58080:80 2>&1 >/dev/null &
sudo socat TCP-LISTEN:58080,bind=172.16.0.2,reuseaddr,fork TCP:127.0.0.1:58080&


# Wait for the port forward to be ready
echo "[+] Waiting for the port forward to be ready"
sleep 1
echo "[+] The web app is ready, you can curl it like so: curl -k 172.16.0.2:30156/ping.php?ip=172.16.0.2"
