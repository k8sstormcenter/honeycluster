from flask import Blueprint, jsonify, request
from src.etl.pixie_etl import PixieETL
import json
from src.etl.stix_etl import StixETL
from src.stix.kubescape.orchestrator import transform_kubescape_logs_to_stix
from src.stix.tetra.orchestrator import transform_tetragon_to_stix

pixie_bp = Blueprint('pixie_etl', __name__, url_prefix='/pixie-etl')

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
]

# Instantiate ETLs but do not start immediately
http_etl = PixieETL(
    table_name='http_events',
    processed_table='http_events',
    column_names=http_columns,
    poll_interval=10
)

dns_etl = PixieETL(
    table_name='dns_events',
    processed_table='dns_events',
    column_names=dns_columns,
    poll_interval=10
)

@pixie_bp.route('/start', methods=['POST'])
def start_etl():
    try:
        http_etl.start()
        dns_etl.start()
        return jsonify({"status": "started"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@pixie_bp.route('/stop', methods=['POST'])
def stop_etl():
    try:
        http_etl.stop()
        dns_etl.stop()
        return jsonify({"status": "stopped"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Process Tetragon logs to STIX row
def process_tetragon_row(row):
    # ClickHouse returns rows as tuples; map columns:
    log = {
        "time_": row[0],
        "uuid": row[1],
        "time": row[2],
        "node_name": row[3],
        "type": row[4],
        "payload": row[5],
    }
    stix_objects, bundles = transform_tetragon_to_stix([log])
    timestamp = int(row[0])  # assuming 'time_' is your nanoseconds timestamp
    data = json.dumps(bundles)
    return [timestamp, data]

# Process Kubescape logs to STIX row
def process_kubescape_row(row):
    log = {
        "BaseRuntimeMetadata": row[0],
        "CloudMetadata": row[1],
        "RuleID": row[2],
        "RuntimeK8sDetails": row[3],
        "RuntimeProcessDetails": row[4],
        "event": row[5],
        "level": row[6],
        "message": row[7],
        "msg": row[8],
        "time": row[9],
    }
    stix_objects, bundles = transform_kubescape_logs_to_stix([log])
    timestamp = int(row[9])  # assuming 'time' is nanoseconds timestamp
    data = json.dumps(bundles)
    return [timestamp, data]

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
    time_column_index=9,  # 'time' column index
    process_func=process_kubescape_row,
    poll_interval=10
)

def start_stix_etls():
    print("[INFO] Starting Tetragon STIX ETL")
    tetragon_stix_etl.start()
    print("[INFO] Starting Kubescape STIX ETL")
    kubescape_stix_etl.start()
