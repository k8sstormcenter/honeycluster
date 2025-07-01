import json
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from src.clickhouse_client import ClickHouseClient
from src.pixie_client import get_px_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PixieETL:
    def __init__(self, table_name, processed_table, column_names, poll_interval=5):
        self.table_name = table_name
        self.processed_table = processed_table
        self.column_names = column_names
        self.poll_interval = poll_interval

        self.client = ClickHouseClient().get_client()
        self.scheduler = BackgroundScheduler()
        self.lock = threading.Lock()
        self.last_seen_ns = 0  # nanoseconds since epoch

    def clean_bstring(self, val):
        val = val.decode("utf-8")
        if isinstance(val, str) and val.startswith("b'") and val.endswith("'"):
            return val[2:-1]
        return val

    def fetch_px_logs(self):
        conn = get_px_connection()

        start_time_clause = ""
        if self.last_seen_ns > 0:
            start_time_clause = f", start_time={self.last_seen_ns}"

        pxl_script = f"""
import px
df = px.DataFrame(table="{self.table_name}"{start_time_clause})
px.display(df, "{self.table_name}")
"""

        script = conn.prepare_script(pxl_script)
        logs = []

        for row in script.results(self.table_name):
            log = {}
            for col_name, val in zip(self.column_names, row):
                log[col_name] = val

            log["upid"]=str(log["upid"])
            log["encrypted"]=int(log["encrypted"])
            logs.append(log)

        logger.info(f"[{self.table_name} ETL] Fetched {len(logs)} rows")
        if logs:
            logger.debug(f"Example row: {logs[0]}")

        return logs

    def fetch_and_process(self):
        with self.lock:
            try:
                rows = self.fetch_px_logs()
                if not rows:
                    return

                processed_rows = []
                for row in rows:
                    processed_row = [row.get(col, None) for col in self.column_names]
                    processed_rows.append(processed_row)

                self.client.insert(
                    self.processed_table,
                    processed_rows,
                    column_names=self.column_names
                )

                self.last_seen_ns = max(int(row['time_']) for row in rows if 'time_' in row)

            except Exception as e:
                print(f"[{self.table_name} ETL] Error: {e}")

    def start(self):
        self.scheduler.add_job(self.fetch_and_process, 'interval', seconds=self.poll_interval)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
