from src.clickhouse_client import get_clickhouse_client


def fetch_kubescape_logs():
    client = get_clickhouse_client()

    query = """
    SELECT
        payload.process.pid AS pid,
        payload.process.pod.name AS pod_name,
        time,
        toUnixTimestamp64Nano(time) AS time_ns,
        type,
        payload
    FROM kubescape
    WHERE payload.process.exec_id LIKE '%Unexpected process launched%'
    """

    result = client.query(query)
    logs = []

    for row in result.result_rows:
        print(row)
        pid, pod_name, time_str, time_ns, log_type, payload = row

        logs.append(
            {
                "pid": pid,
                "pod_name": pod_name,
                "time": time_str,
                "time_ns": time_ns,
                log_type: payload,
            }
        )

    return logs
