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

Kubescape fires the coarse **alert** (`kubescape_logs`); the Adaptive Export
then writes the **correlated Pixie forensic evidence** into `forensic_db`,
attributed by pod + process. The tables below are the full evidence set from
**one** redis e2e run on a **fresh** cluster (`./run-redis-e2e.sh`, ~90 s of
attack) — every count is from that single run:

| table | rows | what it holds |
|---|---:|---|
| `dc_snoop` | 480,000 | every process launch + file access (dentry cache) |
| `http_events` | 14,148 | parsed HTTP requests/responses |
| `stack_trace` | 11,211 | continuous-profiler folded stacks (control flow) |
| `conn_stats` | 6,085 | per-connection socket stats (bytes, open/close) |
| `dns_events` | 3,071 | every DNS query — incl. the C2 lookups |
| `redis_events` | 170 | parsed Redis protocol commands |
| `adaptive_attribution` | 135 | AE's steering record — which anomaly it exported for |

Sample rows (long fields shortened):

**`dns_events`** — the crypto-mining C2 lookup that fired R1008:
```
namespace: redis   pod: redis-74d544d5f9-s9s2d
req_body:  {"queries":[{"name":"xmr.pool.minergate.com","type":"A"}]}
```

**`dc_snoop`** — the offending process, attributed to the pod (R0001):
```
comm: sh   pid: 1041819   namespace: redis   pod: redis/redis-74d544d5f9-s9s2d
container: redis   hostname: cplane-01
```

**`conn_stats`** — the redis pod's socket activity:
```
namespace: redis   pod: redis-74d544d5f9-s9s2d   protocol: 7
conn_open: 141   bytes_sent: 987   bytes_recv: 1974
```

**`http_events`** — parsed HTTP across the cluster:
```
namespace: honey   pod: kubevuln-...   req_method: GET   req_path: /v1/liveness
resp_status: 200   latency: 378215
```

**`redis_events`** — parsed Redis protocol (command + response):
```
namespace: redis   pod: redis-74d544d5f9-s9s2d   req_cmd: PING   req_args: {}   resp: PONG
```

**`stack_trace`** — continuous-profiler folded stack (head only; real rows are long):
```
namespace: redis   container: redis   count: 1
stack_trace: 0x9ba5e353f7cfb848;…;[m] /usr/lib/x86_64-linux-gnu/libc.so.6 + 0x00048c48
```

**`adaptive_attribution`** — AE's steering record (what it exported for, and why):
```
namespace: redis   pod: redis-74d544d5f9-s9s2d   comm: redis-cli   pid: 78317
last_rule_id: R0002   n_anomalies: 3
```

The whole point: kubescape anchors *when/what* is suspicious; Pixie supplies
*the evidence* (process, file, DNS, network, protocol, control-flow), and the
adaptive write keeps only what an anomaly actually needs.


