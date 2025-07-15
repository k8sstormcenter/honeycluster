# File: analysis/hive_sentinel/src/etl/kubescape_matcher_etl.py

import os
import json
import time
import threading
import traceback
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from src.clickhouse_client import ClickHouseClient
from src.config import OUTPUT_DIR
from src.stix.matcher import get_attack_patterns, get_pattern, matches

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OUTPUT_FILE = os.path.join(OUTPUT_DIR, "pixie_matched_stream.json")

class PatternMatcherETL:
    def __init__(self, poll_interval=5):
        self.timestamp = None
        self.podname = None
        self.namespace = None
        self.poll_interval = poll_interval

        self.client = ClickHouseClient().get_client()
        self.scheduler = BackgroundScheduler()
        self.lock = threading.Lock()
        self.last_seen_ns = 0
        self.attack_patterns = get_attack_patterns()

    def set_filters(self, timestamp=None, podname=None, namespace=None):
        self.timestamp = timestamp
        self.podname = podname
        self.namespace = namespace

    def fetch_logs(self):
        lower_bounds = []
        if self.last_seen_ns:
            lower_bounds.append(self.last_seen_ns)
        if self.timestamp:
            lower_bounds.append(int(self.timestamp))

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

                for timestamp_str, data in rows:
                    timestamp = int(timestamp_str)
                    bundle = json.loads(data)

                    matching_patterns = []
                    for attack_bundle in self.attack_patterns:
                        pattern, indicator_id = get_pattern(attack_bundle)
                        pattern_id = attack_bundle["id"]

                        try:
                            if matches(pattern, bundle):
                                matching_patterns.append((indicator_id, pattern_id, attack_bundle))
                        except Exception as e:
                            logger.warning(f"Error during pattern match: {e}")

                    if matching_patterns:
                        result = {
                            "original": bundle,
                            "matches": [
                                {"indicator_id": i, "pattern_id": p, "attack": a["objects"]}
                                for i, p, a in matching_patterns
                            ]
                        }

                        with open(OUTPUT_FILE, "a") as f:
                            f.write(json.dumps(result) + "\n")

                        self.client.execute(
                            "INSERT INTO matched_attack_patterns (timestamp, data) VALUES",
                            [(timestamp, json.dumps(result))]
                        )

                        logger.info("[PatternMatcherETL] Match found and appended")

                self.last_seen_ns = max(int(row[0]) for row in rows if row[0])

            except Exception as e:
                logger.error(f"[PatternMatcherETL] Error: {e}")
                traceback.print_exc()

    def start(self):
        self.scheduler.add_job(self.fetch_and_process, 'interval', seconds=self.poll_interval)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
