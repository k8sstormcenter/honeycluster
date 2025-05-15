import json
from datetime import datetime


def analyze_severity(entry):
    reasons = []
    score = 0

    # Check for unexpected exec
    exec_id = entry.get("process_exec", {}).get("process", {}).get("exec_id", "")
    if "unexpected" in exec_id:
        reasons.append(
            "⚠️ Unexpected process execution detected: exec_id contains 'unexpected'."
        )
        score += 4

    # Check for root privilege
    proc = entry.get("process_exec", {}).get("process", {})
    if (
        proc.get("uid") == 0
        and proc.get("auid") == 0
        and not proc.get("in_init_tree", True)
    ):
        reasons.append(
            "⚠️ Process executed with root privileges (uid=0, auid=0) and is outside the init tree."
        )
        score += 2

    # Check for failed DNS resolutions
    dns_logs = entry.get("dns_logs", [])
    failed_dns = [d for d in dns_logs if '"rcode":3' in d.get("resp_header", "")]
    for d in failed_dns:
        qname = json.loads(d.get("req_body", "{}"))["queries"][0]["name"]
        reasons.append(f"⚠️ Failed DNS query for {qname}")
        score += 1

    successful_dns = [
        d for d in dns_logs if '"num_answers":1' in d.get("resp_header", "")
    ]
    if successful_dns:
        reasons.append(
            "ℹ️ One successful DNS resolution confirms pod exists, reducing criticality slightly."
        )
        score -= 1

    # Check for spammy /health HTTP calls
    http_logs = entry.get("http_logs", [])
    health_requests = [
        h for h in http_logs if h.get("req_path", "").startswith("/health")
    ]
    if len(health_requests) >= 4:
        reasons.append(
            "⚠️ High frequency of /health HTTP GET requests (~4+ in short time), possibly health probes or liveness abuse."
        )
        score += 1

    # Final severity mapping
    if score <= 2:
        severity = "Low"
    elif score <= 5:
        severity = "Medium"
    elif score <= 7:
        severity = "High"
    else:
        severity = "Critical"

    return {
        "pod": entry.get("pod_name"),
        "pid": entry.get("pid"),
        "timestamp": entry.get("time", "N/A"),
        "severity": severity,
        "reasons": reasons,
        "score": score,
    }
