import threading
from apscheduler.schedulers.background import BackgroundScheduler
from src.clickhouse_client import get_clickhouse_client

class StixETL:
    def __init__(self, table, processed_table, column_names, time_column_index, process_func, poll_interval=5):
        self.client = get_clickhouse_client()
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
            query = f"""
                SELECT * FROM {self.table}
                WHERE time > {self.last_seen_ns}
                ORDER BY time ASC
                LIMIT 100
            """
            result = self.client.query(query)
            rows = result.result_rows

            if not rows:
                return

            processed_rows = [self.process_func(row) for row in rows]

            self.client.insert(
                self.processed_table,
                processed_rows,
                column_names=self.column_names
            )

            self.last_seen_ns = rows[-1][self.time_column_index]

    def start(self):
        self.scheduler.add_job(self.fetch_and_process, 'interval', seconds=self.poll_interval)
        self.scheduler.start()

    def stop(self):
        self.scheduler.shutdown(wait=False)
