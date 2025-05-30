set -e

NAMESPACE="clickhouse"
RELEASE_NAME="clickhouse"

echo "🔐 Fetching generated credentials..."
USERNAME="default"
PASSWORD=$(kubectl get secret --namespace "$NAMESPACE" "$RELEASE_NAME" -o jsonpath="{.data.admin-password}" | base64 -d)

echo ""
echo "✅ ClickHouse installed successfully!"
echo "👉 Username: $USERNAME"
echo "👉 Password: $PASSWORD"