# Kubernetes StormCenter: Find runtime threats -- store only the evidence


<img width="5026" height="2000" alt="SOCOverview" src="https://github.com/user-attachments/assets/424956cc-b4ba-404f-bb63-c464b9e74730" />


This deploys an open-source SOC for `k8s`, so that you can visualize ongoing attacks, post-exploitation, save the evidence to a clickhouse database.

It employs adaptive exporting and real-time statistical correlation that remains on the node. 
This means:  
- your data never has to leave your datacenter
- you can tune how much evidence you want to save
- what you consider evidence



We expressely thank the upstream maintainers of our main components: KubeScape and Pixie

If you like it -> consider leaving a star ⭐


Why its cool, cause it has adaptive features that allow filtering out the noise:
<img width="1445" height="747" alt="PixieDXAttackGraph" src="https://github.com/user-attachments/assets/d50a5e7c-662b-4881-b384-c72de8ea5e96" />
<img width="1454" height="920" alt="PixieDXAttackGraphNoise" src="https://github.com/user-attachments/assets/2bfb2506-31d1-43e2-b2a8-27ca3800f12c" />


## Components:
- pixie: for the 24 hr history of all interesting protocols  
This allows the reconstruction of the attack paths and the construction of evidence that either corroborates that an attack occured or tells you where an attack failed (e.g the initial breach and pivot might have happened but they failed at the exfiltration)

- pixie cloud: for visualizing the data across all live clusters as well as the forensic database

- kubescape: for a coarse filtering at any given point in time  
This allows anchoring known malicious signals to kick off the investigation

- clickhouse: for saving the data out of band from your cluster
Sharded by node

- vector: for moving data from A to B  (might be replaced by a dedicated protocol later)


## Backlog

We are looking at a first release end of this summer, so that you can try it out in a compact `all on one k3s` playground

THIS IS CURRENTLY NOT PRODUCTION READY and NOT STABLE, there is no governance or openssf scorecard, yet... its coming...


> [!NOTE]
> This repo contains the deployment artefacts for a sovereign SOC stack -- all development currently is on the individual repos (see the pixie/fork and the node-agent/fork and bob). The old code has been moved into the `deprecated` folder.
>

## Install

Prereqs: a `k3s` cluster (real kernel / eBPF) with **Pixie** deployed and registered.

```bash
# 1. The soc stack, in dependency order: ClickHouse (forensic_db) ->
#    kubescape 1.40.3 + node-agent/storage sbob-rc4 (ContainerProfile) -> vector.
skaffold run -m soc-stack

# 2. Adaptive Export (AE) — reads kubescape_logs and exports the CORRELATED
#    Pixie evidence into forensic_db. It self-creates the schema (needs
#    ingest_service/allow_ddl:"1", see tree/clickhouse-lab/installation.yaml),
#    registers the retention export scripts, and deploys the dark-vector
#    tracepoints.
kubectl -n pl set image ds/adaptive-export \
  adaptive-export=ghcr.io/k8sstormcenter/vizier-adaptive_export_image:0.14.19-aeprod47
kubectl -n pl set env ds/adaptive-export \
  INSTALL_PRESET_SCRIPTS=true \
  CLICKHOUSE_USER=ingest_writer CLICKHOUSE_PASSWORD=changeme-ingest \
  CLICKHOUSE_HOST=clickhouse-forensic-soc-db.clickhouse.svc.cluster.local \
  CLICKHOUSE_PORT=9000 CLICKHOUSE_DATABASE=forensic_db
```

## Run the e2e test (redis)

Deploys the vulnerable Redis + its user-defined ContainerProfile, fires the
post-compromise stage-2 attacks, and proves from the **live** `forensic_db`
that each kubescape rule fired **and** that the Pixie evidence AE exported for
it is stored. Harness: [`bob@feat/cp-artifacts` / dx `e2e/redis`](https://github.com/k8sstormcenter/bob).

```bash
./run-redis-e2e.sh            # deploy redis -> bind SBoB -> attack -> assert
```

Expected: `RESULT: PASS` with rules `R0001 / R0005 / R0008 / R0010 / R1008` in
`kubescape_logs` and the correlated evidence in `dns_events`, `conn_stats`,
`http_events`, `dc_snoop`, `stack_trace`.

## What you get: real evidence in ClickHouse

Kubescape gives you the coarse **alert**; Pixie (via AE) gives you the
**forensic evidence**, and both land in `forensic_db` correlated by pod +
process. From one redis attack run:

**The alert** — `forensic_db.kubescape_logs`:
```
RuleID:   R1008
message:  Communication with a known crypto mining domain: xmr.pool.minergate.com.
hostname: cplane-01
```

**The captured C2 lookup** — `forensic_db.dns_events`:
```
time_:     2026-07-28 18:49:46.066529127
req_body:  {"queries":[{"name":"xmr.pool.minergate.com","type":"A"}]}
```

**The offending process, attributed to the pod** — `forensic_db.dc_snoop`:
```
time_:     2026-07-28 18:49:42.011220101
pid:       1041819
comm:      sh
namespace: redis
pod:       redis/redis-74d544d5f9-dpx4r
container: redis
hostname:  cplane-01
```

**The detection, per rule** — `forensic_db.kubescape_logs`:
```
R0001   Unexpected process launched: whoami with PID 1042137
R0001   Unexpected process launched: getent with PID 1042536
R0001   Unexpected process launched: cat    with PID 1043393
R1008   Communication with a known crypto mining domain: xmr.pool.minergate.com.
```

That one ~90 s attack produced, in `forensic_db`: **dns_events 411k · conn_stats
596k · http_events 1.15M · dc_snoop 51.8M · stack_trace 399k** rows — the full
kernel + network picture, correlated to each kubescape rule. The whole point:
kubescape anchors *when/what* is suspicious; Pixie supplies *the evidence*, and
the adaptive write keeps only what an anomaly actually needs.


