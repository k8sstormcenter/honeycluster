from flask import Blueprint, jsonify
from src.stix.tetra.orchestrator import transform_tetragon_to_stix
from src.tetra_log.reader import fetch_tetragon_logs

stix_bp = Blueprint("stix", __name__)

@stix_bp.route("/fetch-stix", methods=["GET"])
def fetch_stix():
    try:
        logs = fetch_tetragon_logs()
        stix_objects, bundles = transform_tetragon_to_stix(logs)
        return jsonify(stix_objects), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500