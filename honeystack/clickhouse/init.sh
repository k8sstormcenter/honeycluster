    #!/bin/bash
    podname=$(kubectl get pods -n click -l app=clickhouse -o jsonpath='{.items[0].metadata.name}')
    kubectl exec -i -n click $podname -- clickhouse-client --multiquery --database=default <<'EOF'
    CREATE TABLE IF NOT EXISTS default.kubescape_logs (
        BaseRuntimeMetadata String,
        CloudMetadata String,
        RuleID String,
        RuntimeK8sDetails String,
        RuntimeProcessDetails String,
        event String,
        level String,
        hostname String,
        message String,
        msg String,
        md5_hash String,
        processtree_depth UInt32,
        event_time DateTime
    ) ENGINE = MergeTree()
    PARTITION BY toYYYYMM(event_time)
    ORDER BY (hostname, event_time);


    CREATE TABLE IF NOT EXISTS default.http_events (
        time_ UInt64,
        upid UUID,
        remote_addr String,
        remote_port Int32,
        local_addr String,
        local_port Int32,
        trace_role UInt8,
        encrypted UInt8,
        major_version UInt16,
        minor_version UInt16,
        content_type UInt16,
        req_headers String,
        req_method String,
        req_path String,
        req_body String,
        req_body_size UInt64,
        resp_headers String,
        resp_status UInt16,
        resp_message String,
        resp_body String,
        resp_body_size UInt64,
        container_id String,
        node_name String,
        namespace String,
        pod_name String,
        pid UInt64,
        latency UInt64
    ) ENGINE = MergeTree() ORDER BY time_;


    CREATE TABLE IF NOT EXISTS default.dns_events (
        time_ UInt64,
        upid UUID,
        remote_addr String,
        remote_port Int32,
        local_addr String,
        local_port Int32,
        trace_role UInt8,
        encrypted UInt8,
        req_header String,
        req_body String,
        resp_header String,
        resp_body String,
        container_id String,
        node_name String,
        namespace String,
        pod_name String,
        pid UInt64,
        latency UInt64
    ) ENGINE = MergeTree() ORDER BY time_;


    EOF