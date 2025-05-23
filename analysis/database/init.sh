#!/bin/bash

set -e

NAMESPACE="clickhouse"
RELEASE_NAME="clickhouse"

echo "🚀 Checking if Helm and kubectl are installed..."
if ! command -v helm &> /dev/null; then
    echo "❌ Helm is not installed. Please install Helm and try again."
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl and try again."
    exit 1
fi

echo "📦 Installing ClickHouse in namespace '$NAMESPACE'..."
helm install "$RELEASE_NAME" \
  --namespace "$NAMESPACE" \
  --create-namespace \
  oci://registry-1.docker.io/bitnamicharts/clickhouse

echo "⏳ Waiting for ClickHouse pods to be ready..."
kubectl wait --namespace "$NAMESPACE" --for=condition=Ready pod -l app.kubernetes.io/name=clickhouse --timeout=180s

echo "🔐 Fetching generated credentials..."
USERNAME="default"
PASSWORD=$(kubectl get secret --namespace "$NAMESPACE" "$RELEASE_NAME" -o jsonpath="{.data.admin-password}" | base64 -d)

echo ""
echo "✅ ClickHouse installed successfully!"
echo "👉 Username: $USERNAME"
echo "👉 Password: $PASSWORD"
