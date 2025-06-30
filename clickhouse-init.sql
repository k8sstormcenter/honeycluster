-- ⚙️ ClickHouse Initialization SQL for Honeycluster Pipelines

-- 1️⃣ KUBESCAPE LOGS TABLE
CREATE TABLE IF NOT EXISTS default.kubescape_logs (
    BaseRuntimeMetadata String,
    CloudMetadata String,
    RuleID String,
    RuntimeK8sDetails String,
    RuntimeProcessDetails String,
    event String,
    level String,
    message String,
    msg String,
    time UInt64
) ENGINE = MergeTree
ORDER BY time;

-- 2️⃣ KUBESCAPE STIX TABLE
CREATE TABLE IF NOT EXISTS default.kubescape_stix (
    timestamp UInt64,
    data String
) ENGINE = MergeTree
ORDER BY timestamp;

-- 3️⃣ TETRAGON LOGS TABLE
CREATE TABLE IF NOT EXISTS default.tetragon_logs (
    time_ UInt64,
    uuid String,
    time String,
    node_name String,
    type String,
    payload String
) ENGINE = MergeTree
ORDER BY time_;

-- 4️⃣ TETRAGON STIX TABLE
CREATE TABLE IF NOT EXISTS default.tetragon_stix (
    timestamp UInt64,
    data String
) ENGINE = MergeTree
ORDER BY timestamp;

-- 5️⃣ HTTP EVENTS TABLE
CREATE TABLE IF NOT EXISTS default.http_events (
    time_ UInt64,
    upid String,
    remote_addr String,
    remote_port UInt16,
    local_addr String,
    local_port UInt16,
    trace_role String,
    encrypted UInt8,
    major_version UInt16,
    minor_version UInt16,
    content_type String,
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
    latency UInt64
) ENGINE = MergeTree
ORDER BY time_;

-- 6️⃣ DNS EVENTS TABLE
CREATE TABLE IF NOT EXISTS default.dns_events (
    time_ UInt64,
    upid String,
    remote_addr String,
    remote_port UInt16,
    local_addr String,
    local_port UInt16,
    trace_role String,
    encrypted UInt8,
    req_header String,
    req_body String,
    resp_header String,
    resp_body String,
    latency UInt64
) ENGINE = MergeTree
ORDER BY time_;

-- ✅ All required tables for ingestion, Pixie, and STIX ETL are ready.