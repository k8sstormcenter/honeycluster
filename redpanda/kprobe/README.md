# Redpanda Golang WASM Transform

To get started you first need to have at least go 1.20 installed.

You can get started by modifying the <code>transform.go</code> file
with your logic.

Once you're ready to test out your transform live you need to:

1. Make sure you have a container running via <code>rpk container start</code>
1. Run <code>rpk transform build</code>
1. Create your topics via <code>rpk topic create</code>
1. Run <code>rpk transform deploy</code>
1. Then use <code>rpk topic produce</code> and <code>rpk topic consume</code>
   to see your transformation live!


# Dependencies (MAC)
### we only want messages that have the word kprobe in them 
### rew install redpanda-data/tap/redpanda
### rpk transform init --language=tinygo
### rpk profile create --from-profile <(kubectl get configmap --namespace redpanda redpanda-src-rpk -o go-template='{{ .data.profile }}') redpanda-profile
``` 
alias internal-rpk="kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- rpk"
kubectl cp transform.yaml redpanda/redpanda-src-0:/tmp
kubectl cp kprobe.wasm redpanda/redpanda-src-0:/tmp
kubectl --namespace redpanda exec -i -t redpanda-src-0 -c redpanda -- /bin/bash -c "cd /tmp && rpk transform deploy"
```