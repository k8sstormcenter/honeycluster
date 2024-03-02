# Deploying a real Honeycluster

## Example on RKE2 (on openstack)

In the KubeCon EU talk, we present also two "real" clusters, they are hosted on a RKE2 1.27 with Rancher running.
This cluster is supposed to look like a experimental cluster on which an SRE is actively debugging something.
This SRE is useing reverse SSH to login to the cluster via a jump-host. Thus, the corporate firewall is untouched.


## Security Considerations

Given this is an experimental setup of a honeypot-infrastructure, there are additional measures taken to make sure these clusters can be shut down at a moment's notice and they also have additional observability installed to verify any integrity compromises.

## Setup

1) Edit all values "rke2values.yaml" for your own cluster. We assume that you have cert-manager, an ingress-class (we use nginx) and some storage. You dont need to be running cilium as CNI, but we are. 

2) For the leaky vessel exploit: it likely doesnt work, as must runc are patched now. In the talk we presented a intentionally downgraded runc. 

```bash
make --makefile=rke2/Makefile all-up
```

## Baseline collection
In order to reduce the baseline out, we need to collect sufficient logs to deduplicate them and classify them as "baseline".
During the baseline collection, do not touch the cluster and just let the logs pile up.

```bash
make --makefile=rke2/Makefile redpanda-baseline
```
(you might need Go 1.21 installed)

Now, the ebpf-traces are on and being shipped into the topic=baseline. Thus, we need to collect data for a while until topic-compaction will start kicking in depending on the exact settings. The general idea of compaction is that each "key" will only keep the latest entry, and since the WASM transform creates sort-of a hash-key from the tetragon logs, they will naturally be deduplicated after the compaction threshold is triggered.

Run the "extactcsv" WASM transform over the baseline topic . It will log to STDOUT the deduplicated records (read the logs from the redpanda-src container). Copy paste them into a file (should look like redpanda/extractcsv/extract.csv), remove the leading columns:

```
cut -f 11- -d ' ' redpanda/extractcsv/extract.csv > uniquekeys.csv
awk '{print "\"" $0 "\","}' uniquekeys.csv > output.csv
```
take those entries and copy/paste them into the transform.go function of signalminusbaseline

```
var keys = []string{
	"b7c7da62ea3fab64db4f33feb4ad6182348ff0c1c4159f8aca2b259f7bd3bfddusrbinbashusrbinrpkclusterhealth",
	"b7c7da62ea3fab64db4f33feb4ad6182348ff0c1c4159f8aca2b259f7bd3bfddoptredpandalibexecrpkclusterhealth",
    ...
}
```
For reference, the RKE2/Rancher cluster has 20 namespaces and it takes about 2 hrs to extract the 155 unique keys needed to get the topic= "signalminusbaseline" almost entirely clean .



