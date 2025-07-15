from flask import Blueprint, jsonify, request
from dateutil import parser as date_parser
from uuid import uuid4
from src.etl.pixie_etl import PixieETL
import json
from datetime import datetime
from src.etl.stix_etl import StixETL
from src.stix.kubescape.orchestrator import transform_kubescape_logs_to_stix
from src.stix.tetra.orchestrator import transform_tetragon_to_stix

pixie_bp = Blueprint('pixie_etl', __name__, url_prefix='/pixie-etl')

running_etls = {}

# Columns for HTTP_EVENTS
http_columns = [
    'time_',
    'upid',
    'remote_addr',
    'remote_port',
    'local_addr',
    'local_port',
    'trace_role',
    'encrypted',
    'major_version',
    'minor_version',
    'content_type',
    'req_headers',
    'req_method',
    'req_path',
    'req_body',
    'req_body_size',
    'resp_headers',
    'resp_status',
    'resp_message',
    'resp_body',
    'resp_body_size',
    'latency',
    'pod_name',
    'namespace',
    'container_id',
    'pid',
    'node_name',
]

# Columns for DNS_EVENTS
dns_columns = [
    'time_',
    'upid',
    'remote_addr',
    'remote_port',
    'local_addr',
    'local_port',
    'trace_role',
    'encrypted',
    'req_header',
    'req_body',
    'resp_header',
    'resp_body',
    'latency',
    'pod_name',
    'namespace',
    'container_id',
    'pid',
    'node_name',
]

@pixie_bp.route('/start', methods=['POST'])
def start_pixie_etl():
    data = request.json

    tablename = data.get("tablename")
    time_value = data.get("timestamp")
    podname = data.get("podname")
    namespace = data.get("namespace")
    poll_interval = data.get("poll_interval", 10)

    try:
        # Process timestamp
        timestamp_ns = None
        if time_value:
            if isinstance(time_value, str):
                dt = date_parser.isoparse(time_value)
                timestamp_ns = int(dt.timestamp() * 1_000_000_000)
            elif isinstance(time_value, int):
                if time_value < 1e12:  # ms
                    timestamp_ns = time_value * 1_000_000
                elif time_value < 1e15:  # µs
                    timestamp_ns = time_value * 1_000
                else:  # ns
                    timestamp_ns = time_value
            else:
                return jsonify({"status": "error", "message": "Invalid timestamp type, must be string or int"}), 400

        if tablename == "http_events":
            etl = PixieETL(
                table_name='http_events',
                processed_table='http_events',
                stix_table='http_stix',
                column_names=http_columns,
                poll_interval=poll_interval
            )

        elif tablename == "dns_events":
            etl = PixieETL(
                table_name='dns_events',
                processed_table='dns_events',
                stix_table='dns_stix',
                column_names=dns_columns,
                poll_interval=poll_interval
            )
        else:
            return jsonify({"status": "error", "message": f"Feature for {tablename} not implemented"}), 400

        etl.set_filters(timestamp=timestamp_ns, podname=podname, namespace=namespace)

        etl_id = str(uuid4())
        running_etls[etl_id] = {
            "etl": etl,
            "tablename": tablename,
            "filters": {
                "timestamp": timestamp_ns,
                "podname": podname,
                "namespace": namespace
            },
            "poll_interval": poll_interval
        }

        etl.start()

        return jsonify({
            "status": "started",
            "uuid": etl_id,
            "tablename": tablename,
            "filters": {
                "timestamp": timestamp_ns,
                "podname": podname,
                "namespace": namespace
            },
            "poll_interval": poll_interval
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@pixie_bp.route('/stop', methods=['POST'])
def stop_pixie_etl():
    data = request.json
    etl_id = data.get("uuid")

    try:
        etl_entry = running_etls.get(etl_id)
        if etl_entry is None:
            return jsonify({"status": "error", "message": f"No ETL found with uuid {etl_id}"}), 404

        etl_entry["etl"].stop()
        del running_etls[etl_id]

        return jsonify({"status": "stopped", "uuid": etl_id}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@pixie_bp.route('/status', methods=['GET'])
def status_pixie_etls():
    try:
        status = {}
        for etl_id, info in running_etls.items():
            status[etl_id] = {
                "tablename": info["tablename"],
                "filters": info["filters"],
                "poll_interval": info["poll_interval"]
            }
        return jsonify({"running_etls": status}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Process Tetragon logs to STIX row
def process_tetragon_row(row):
    # ClickHouse returns rows as tuples; map columns:
    log = {
        "timestamp": row[0],
        "node_name": row[1],
        f"{row[2]}": json.loads(row[3]),
    }
    stix_objects, bundles = transform_tetragon_to_stix([log])
    data = json.dumps(stix_objects)
    return [log["timestamp"], data]


def ns_to_iso8601(ns):
    """Convert nanoseconds since epoch to ISO8601 string."""
    return datetime.utcfromtimestamp(ns / 1e9).isoformat() + 'Z'

# Process Kubescape logs to STIX row
def process_kubescape_row(row):
    log = {
        "BaseRuntimeMetadata": json.loads(row[0]),
        "CloudMetadata": json.loads(row[1]) if row[1] != "empty" else {},
        "RuleID": row[2],
        "RuntimeK8sDetails": json.loads(row[3]),
        "RuntimeProcessDetails": json.loads(row[4]),
        "event": json.loads(row[5]),
        "level": row[6],
        "message": row[7],
        "msg": row[8],
        "timestamp": row[9],
    }
    stix_objects, bundles = transform_kubescape_logs_to_stix([log])
    data = json.dumps(stix_objects)
    return [log["timestamp"], data]

# STIX table columns
stix_columns = ["timestamp", "data"]

# Tetragon ETL
tetragon_stix_etl = StixETL(
    table="tetragon_logs",
    processed_table="tetragon_stix",
    column_names=stix_columns,
    time_column_index=0,  # 'time_' as nanoseconds
    process_func=process_tetragon_row,
    poll_interval=10
)

# Kubescape ETL
kubescape_stix_etl = StixETL(
    table="kubescape_logs",
    processed_table="kubescape_stix",
    column_names=stix_columns,
    time_column_index=9,  # 'timestamp' column index
    process_func=process_kubescape_row,
    poll_interval=10
)

def start_stix_etls():
    print("[INFO] Starting Tetragon STIX ETL")
    tetragon_stix_etl.start()
    print("[INFO] Starting Kubescape STIX ETL")
    kubescape_stix_etl.start()
