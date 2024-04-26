# HoneyCluster to verify and quantify attack paths
You start with your "normal" cluster, where you wish to

(A) verify/quantify theoretical threat modelling assumptions

or 

(B) to simply observe  how your cluster will be attacked by interpreting the anomalous signals

## The four fold path to threat intelligence
1 Threat Model -> Attack Model -> Critical Attack Path

2 Instrument a honeycluster with eBPF tripwires and some bait

3 Trace and stream events, remove baseline

4 Disseminate the Threat Intelligence

## (A) Demo on KIND 
### 1 Example Attack Tree

As a simple example attack tree, we will look at the attack path made possible if an attacker can create `/var/log` hostPath Persistent Volumes on a cluster, inspired by [this blog post](https://jackleadford.github.io/containers/2020/03/06/pvpost.html).

```mermaid
flowchart TD
    A[Access sensitive \ninfo on node] --> B{kubectl logs BAD_POD}
    A --> H[Pod uses PVC \nwhich references a \nhostPath PV]
    B --> I[Pod writes symlink \nto 0.log file]
    B --> C[Container can \nrun as root]
    B --> D[Pod with \nwriteable hostPath \nto /var/log]
    D --> E{Ability to create \nK8s resources} 
    H --> E
    E --> F[Misconfigured RBAC]
    E --> G[Initial access \nto Pod]
```



### 2 Setup KIND

Bring all the infra up (known issue: wait conditions on some OS not working):

```bash
make --makefile=Makefile_kind honey-up
```

At this point, you might want to port-forward to Redpanda dashboard (service redpanda-src-console) and browse to the TOPIC = keygen. 
```bash
kubectl port-forward service/redpanda-src-console -n redpanda 30000:8080
```
http://localhost:30000/topics/keygen?p=-1&s=500&o=-2#messages

In my case on kind, I see 5 messages. I will judge them as "BENIGN" because I know thats the install, but check please.

### 3 Setup Baseline redaction
For this to work you need GO installed. Currently also RPK, there might still be some dependency issues for some OS, and we are working hard to avoid the local compiling.

```bash
export PATH="/usr/local/opt/go@1.21/bin:$PATH"
make --makefile=Makefile_kind honey-signal

stuff....
build successful
deploy your transform to a topic:
        rpk transform deploy
TOPIC   STATUS
signal  OK
transform "signal" deployed.
```

### 4 Execute the sample attack
(currently we disabled the redpanda topics `trace*` because we are rewriting them, you can compile and deploy them though)
Make an SSH connection to the server, and note the corresponding message in the `signal` topic:

```bash
make --makefile=Makefile_kind ssh-connect
ssh -p 5555 root@127.0.0.1
Handling connection for 5555
root@127.0.0.1's password: root
...
stuff
...
Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
applicable law.

root@ssh-proxy:~# ls
```
At this point, you should see some `signal` in RedPanda. Approx 40-50 signals. 

You could decide that you dont want to see all of the bash environment related signals, and copy paste the key e.g. exec69ef01cde4ec877c63652bf9d84e9210 into the `redpanda/signal/transform.go` and recompile using `make --makefile=Makefile_kind redpanda-wasm`  


More self-attack-experimentation:



Close the SSH connection, and run the full attack which will again make an SSH connection to our vulnerable server, run a malicious script which will create a HostPath type PersistentVolume, allowing a pod to access `/var/log` on the host (inspired by [this blog post](https://jackleadford.github.io/containers/2020/03/06/pvpost.html)), using the [Python Kubernetes client library](https://github.com/kubernetes-client/python). Note that you could modify the hostPath in the Python script to go directly for the data on the host that you want to compromise, however, in order to increase the number of attack steps in our scenario (and hence the number of indicators that we can look for), let's imagine that we are not able to create arbitrary hostPaths. In this scenario, perhaps a `hostPath` type `PersistentVolume` is allowed for `/var/log` so that a Pod can monitor other Pod's logs.

```bash
make --makefile=Makefile_kind attack
```

When prompted, the password is `root`.

If the service account compromised by our attacker could inspect the logs of the containers it can create, running `kubectl logs bad-pv-pod --tail=-1` (or making an API call from within the bad pod) will enable an attacker to view arbitrary files (line by line) on the host. In this example, we have a single node cluster, so we can access control plane data.

Note that we have a lot more messages in the `signal` topic following the attack. Additional topics can be configured to filter for the other attack steps by configuring `DIRS` in the Makefile.

[![K8sstormcenterSSH](https://img.youtube.com/vi/EcZcLz3kkUs/0.jpg)](https://www.youtube.com/watch?v=EcZcLz3kkUs)


The above screen recording shows the newly established ssh connection being picked up by the eBPF traces and appearing as anomaly in the topic `signalminusbaseline` (since, renamed to `signal` )  in the RedPandaUI and 
filtered into the topic  `tracesssh`  on RedPanda (lower screen, shell `rpk topic consume tracesssh`).
### Teardown of Kind

```bash
make --makefile=Makefile_kind teardown
```

## (B) Experiment to detect Leaky Vessel on live clusters
No additional cluster instrumentation is needed, no specific assumptions etc were made.

The video below shows the poisoning of a registry with an image exploiting CVE-2024-21626 "Leaky-Vessel" by tagging and pushing the poisoned image with identical name/tag as the original image. (This is a type of Supply Chain Attack).

Two different RKE2 clusters (intentionally running a vulnerable `runc`) are observed by streaming the `smb` topic in the RedPandaUI. When the poisoned image is pulled and started up, the traces appear on the topic. As well as we see the sensitive-file-access to the private key on the host-node, as well as the newly created file `LEAKYLEAKY` on the host node.


[![K8sstormcenterLeakyVessel](https://img.youtube.com/vi/RNYz86uDXLc/0.jpg)](https://www.youtube.com/watch?v=RNYz86uDXLc)



# Deploying a real Honeycluster
WIP: It does work, but we are working on cleaning it all up. 

## Example on RKE2 (on openstack)

In the KubeCon EU talk, we present two "real" clusters, they are hosted on a RKE2 1.27 with Rancher running.
This type of honeycluster is supposed to look like a experimental kubernetes-cluster on which an SRE is actively debugging something.
This SRE is useing insecure reverse SSH to login to the cluster via a jump-host, no modifications to the corporate firewall are required.


## Security Considerations

Given this is an insecure and experimental setup of a honeypot-infrastructure, there are several additional measures taken that are not covered in the talk or this repo.
This repo is for demonstration purposes only.

## Setup

1) Edit all values "rke2values.yaml" for your own cluster. We assume that you have cert-manager, an ingress-class (we use nginx) and some storage. You dont need to be running cilium as CNI, but we are. 

2) For the leaky vessel exploit: it likely doesnt work, as must runc are patched now. In the talk we presented a intentionally downgraded runc. 

```bash
make --makefile=Makefile_rke2 install-honeycluster
```

## WASM compilation for any transform not in the prebuilt folder
(you STILL need Go 1.21 installed, WIP to remove this requirement from the base-install)
IF in the above step you have GO errors, it is because the following command compiles the WASM binaries:

```bash
make --makefile=Makefile_rke2 redpanda-wasm
```






