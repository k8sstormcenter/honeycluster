import re

def create_process_stix_id(corr_id):
    if corr_id:
        try:
            truncated_exec_id = corr_id[:36]
            return f"process--{truncated_exec_id}"
        except Exception as e:
            print(f"Error generating process ID: {e}")

def generate_unique_log_id(container_id, pid, hostname, time, src):
    pid = str(pid).zfill(8)
    host = str(hostname[:12]).zfill(12)
    timestamp = re.sub(r"[-\:\.]", "", time[2:22])
    if src == "tetra":
        con_id = re.match(r"containerd://([0-9a-f]+)", container_id).group(1)[:12]
    else:
        con_id = container_id[:12]
    return f"{timestamp}{con_id}{pid}{host}"