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

## Evidence in ClickHouse (one redis e2e run, excl. `kubescape_logs`)

Kubescape fires the alert; the Adaptive Export writes the correlated Pixie
evidence to `forensic_db`. `dc_snoop` is filtered to workload + attack (infra
dropped; drop-list is env-configurable via `DC_SNOOP_EXCLUDE_NAMESPACES` /
`DC_SNOOP_EXCLUDE_COMMS`, no rebuild).

```
dc_snoop              redis-server  redis  R proc/self/stat   +  sh bash getent whoami cat  (attack exec)
dns_events            {"queries":[{"name":"xmr.pool.minergate.com","type":"A"}]}   (also evil.attacker.example.com)
conn_stats            redis  127.0.0.1  proto:7  sent:19628 recv:39256
redis_events          redis  PING -> PONG
stack_trace           redis  __open;[k] entry_SYSCALL_64_after_hwframe  count:1
adaptive_attribution  redis/sh  R0002  n_anomalies:1846
```
