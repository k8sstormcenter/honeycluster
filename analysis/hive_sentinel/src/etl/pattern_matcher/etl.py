# File: analysis/hive_sentinel/src/etl/kubescape_matcher_etl.py

import os
import json
import time
import threading
import traceback
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from src.stix.core import generate_stix_id
from src.clickhouse_client import ClickHouseClient
from src.config import OUTPUT_DIR
from src.stix.matcher import get_attack_patterns, get_pattern, matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PatternMatcherETL:
    def __init__(self, poll_interval=5):
        self.timestamp = None
        self.podname = None
        self.namespace = None
        self.poll_interval = poll_interval
        self.OUTPUT_FILE = os.path.join(OUTPUT_DIR, "pixie_matched_stream.json")

        self.client = ClickHouseClient().get_client()
        self.scheduler = BackgroundScheduler()
        self.lock = threading.Lock()
        self.last_seen_ts = "1970-01-01T00:00:00Z"
        self.attack_patterns = [    {
        "type": "bundle",
        "id": "16",
        "name": "DummyForTesting",
        "version": "1.0.0",
        "spec_version": "2.1",
        "objects": [
            {
                "type": "attack-pattern",
                "id": "attack-pattern--tracee",
                "name": "tracee",
                "description": "description",
            },
            {
                "type": "indicator",
                "id": "indicator--tracee",
                "name": "tracee",
                "description": "Detecting tracee",
                "pattern": "[process:command_line MATCHES '/bin/sh -c ping -c 4 1.1.1.1;cat /proc/self/mounts']",
                "pattern_type": "stix",
                "valid_from": "2024-01-01T00:00:00Z",
            },
            {
                "type": "relationship",
                "id": "relationship--tracee",
                "relationship_type": "indicates",
                "source_ref": "indicator--tracee",
                "target_ref": "attack-pattern--tracee",
            },
        ],
    },]

    def set_filters(self, timestamp=None, podname=None, namespace=None):
        self.timestamp = timestamp
        self.podname = podname
        self.namespace = namespace

    def fetch_logs(self):
        lower_bounds = []
        if self.last_seen_ts:
            lower_bounds.append(self.last_seen_ts)
        if self.timestamp:
            lower_bounds.append(self.timestamp)

        if not lower_bounds:
            logger.warning("No timestamp defined, skipping fetch")
            return []

        effective_start_ns = max(lower_bounds)

        query = """
        SELECT timestamp, data
        FROM kubescape_stix
        WHERE toUInt64(timestamp) > %(start_ns)s
          AND pod_name = %(pod)s
          AND namespace = %(ns)s
        ORDER BY timestamp DESC
        LIMIT 100
        """

        params = {
            "start_ns": effective_start_ns,
            "pod": self.podname,
            "ns": self.namespace
        }

        result = self.client.query(query, parameters=params)
        return result.result_rows

    def fetch_and_process(self):
        with self.lock:
            try:
                rows = self.fetch_logs()
                if not rows:
                    return

                for timestamp, data in rows:
                    objects = json.loads(data)
                    stix_bundle = {
                        "type": "bundle",
                        "id": generate_stix_id("bundle"),
                        "spec_version": "2.1",
                        "objects": objects,
                    }

                    matching_patterns = []
                    for attack_bundle in self.attack_patterns:
                        pattern, indicator_id = get_pattern(attack_bundle)
                        pattern_id = attack_bundle["id"]

                        if matches(pattern, stix_bundle):
                            matching_patterns.append((indicator_id, pattern_id, attack_bundle))

                    if matching_patterns:
                        matches = [
                            {"indicator_id": i, "pattern_id": p, "attack": a["objects"]}
                            for i, p, a in matching_patterns
                        ]

                        with open(self.OUTPUT_FILE, "a") as f:
                            f.write(json.dumps(stix_bundle) + "\n")

                        self.client.insert(
                            table="matched_attack_patterns",
                            data=[(timestamp, json.dumps(stix_bundle), json.dumps(matches))],
                            column_names=["timestamp", "bundle", "matches"]
                        )

                        logger.info("[PatternMatcherETL] Match found and appended")

                self.last_seen_ts = rows[-1][self.time_column_index]

            except Exception as e:
                logger.error(f"[PatternMatcherETL] Error: {e}")
                traceback.print_exc()

    def start(self):
        self.scheduler.add_job(self.fetch_and_process, 'interval', seconds=self.poll_interval)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
