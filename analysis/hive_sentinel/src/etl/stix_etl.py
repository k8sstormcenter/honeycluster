import threading
from apscheduler.schedulers.background import BackgroundScheduler
from src.clickhouse_client import ClickHouseClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StixETL:
    def __init__(self, table, processed_table, column_names, time_column_index, process_func, poll_interval=5):
        self.client = ClickHouseClient().get_client()
        self.table = table
        self.processed_table = processed_table
        self.column_names = column_names
        self.time_column_index = time_column_index
        self.process_func = process_func
        self.poll_interval = poll_interval

        self.last_seen_ns = 0
        self.lock = threading.Lock()
        self.scheduler = BackgroundScheduler()

    def fetch_and_process(self):
        with self.lock:
            logger.info(f"🚀 Running ETL fetch for table {self.table}")
            query = f"""
                SELECT * FROM {self.table}
                WHERE time > {self.last_seen_ns}
                ORDER BY time ASC
                LIMIT 10
            """
            try:
                result = self.client.query(query)
                rows = result.result_rows
                logger.info(f"🔍 Fetched {len(rows)} rows after {self.last_seen_ns}")

                if not rows:
                    return

                processed_rows = [self.process_func(row) for row in rows]

                if processed_rows:
                    self.client.insert(
                        self.processed_table,
                        processed_rows,
                        column_names=self.column_names
                    )
                    logger.info(f"✅ Inserted {len(processed_rows)} rows into {self.processed_table}")

                    self.last_seen_ns = rows[-1][self.time_column_index]
                    logger.info(f"⏱️ Updated last_seen_ns to {self.last_seen_ns}")

            except Exception as e:
                logger.error(f"❌ Error during fetch_and_process: {e}", exc_info=True)

    def start(self):
        self.scheduler.add_job(self.fetch_and_process, 'interval', seconds=self.poll_interval)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
