#!/bin/bash

set -e

NAMESPACE="clickhouse"
RELEASE_NAME="clickhouse"

echo "🚀 Checking tools..."
command -v helm >/dev/null || { echo "❌ Helm not installed"; exit 1; }
command -v kubectl >/dev/null || { echo "❌ kubectl not installed"; exit 1; }
if ! command -v clickhouse-client >/dev/null; then
  echo "⚠️  clickhouse-client not found — installing..."
  sudo apt-get update
  sudo apt-get install -y clickhouse-client
else
  echo "✅ clickhouse-client is already installed."
fi

echo "📦 Installing ClickHouse..."
helm upgrade --install "$RELEASE_NAME" oci://registry-1.docker.io/bitnamicharts/clickhouse \
  --namespace "$NAMESPACE" --create-namespace

echo "⏳ Waiting for ClickHouse pods to be ready..."
kubectl wait --namespace "$NAMESPACE" --for=condition=Ready pod -l app.kubernetes.io/name=clickhouse --timeout=180s

echo "🔐 Fetching credentials..."
USERNAME="default"
PASSWORD=$(kubectl get secret --namespace "$NAMESPACE" "$RELEASE_NAME" -o jsonpath="{.data.admin-password}" | base64 -d)

export CLICKHOUSE_DB="default"
export CLICKHOUSE_USER="$USERNAME"
export CLICKHOUSE_PASSWORD="$PASSWORD"
export CLICKHOUSE_ENDPOINT="http://127.0.0.1:8123"

echo ""
echo "✅ ClickHouse installed and credentials fetched!"

echo "📡 Starting port-forward to localhost:9000 ..."
if lsof -i :9000 >/dev/null; then
  echo "⚠️  Port 9000 already in use — assuming existing port-forward."
else
  kubectl port-forward --namespace "$NAMESPACE" svc/$RELEASE_NAME 9000:9000 &
  PORT_FORWARD_PID=$!
  sleep 5
  echo "🔗 Port-forward PID: $PORT_FORWARD_PID"
fi


if lsof -i :8123 >/dev/null; then
  echo "⚠️  Port 8123 already in use — assuming existing port-forward."
else
  kubectl port-forward --namespace "$NAMESPACE" svc/$RELEASE_NAME 8123:8123 &
  PORT_FORWARD_8123_PID=$!
  echo "🔗 Port-forward for 8123 started (PID: $PORT_FORWARD_8123_PID)"
  sleep 3
fi

echo "👉 Creating kubescape_logs with local clickhouse-client..."
clickhouse-client --host 127.0.0.1 --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
  --query "CREATE TABLE IF NOT EXISTS ${CLICKHOUSE_DB}.kubescape_logs (
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
  ) ENGINE = MergeTree() ORDER BY time;"

echo "👉 Creating tetragon_logs with local clickhouse-client..."
clickhouse-client --host 127.0.0.1 --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
  --query "CREATE TABLE IF NOT EXISTS ${CLICKHOUSE_DB}.tetragon_logs (
    time UInt64,
    node_name String,
    type String,
    payload String
  ) ENGINE = MergeTree() ORDER BY time;"

echo "👉 Verifying tables with local clickhouse-client..."
clickhouse-client --host 127.0.0.1 --user "$CLICKHOUSE_USER" --password "$CLICKHOUSE_PASSWORD" \
  --query "SHOW TABLES;"

echo ""
echo "✅ All done! ClickHouse is installed, port-forward is ready (PID: ${PORT_FORWARD_PID:-N/A}), tables created and verified!"
echo "🔒 If port-forward is running in background, press Ctrl+C to stop it when you’re done."

echo ""
echo "✅ ClickHouse installed and credentials fetched!"
echo ""
echo "👉 Use these later to export in your shell if needed:"
echo ""
echo "export CLICKHOUSE_DB=\"default\""
echo "export CLICKHOUSE_USER=\"$USERNAME\""
echo "export CLICKHOUSE_PASSWORD=\"$PASSWORD\""
echo "export CLICKHOUSE_ENDPOINT=\"http://127.0.0.1:8123"\""
echo ""
echo "👉 To update honeystack/vector/soc.yaml again later, run:"
echo "envsubst < honeystack/vector/soc.yaml > honeystack/vector/soc.yaml.tmp && mv honeystack/vector/soc.yaml.tmp honeystack/vector/soc.yaml"
echo ""
