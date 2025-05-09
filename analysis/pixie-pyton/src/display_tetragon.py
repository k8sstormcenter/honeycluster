import os
import json
import pxapi
from dotenv import load_dotenv
from tetragon2stix import transform_tetragon_to_stix

# Load .env variables
load_dotenv()

PIXIE_API_TOKEN = os.getenv("PIXIE_API_TOKEN")
PIXIE_CLUSTER_ID = os.getenv("PIXIE_CLUSTER_ID")

def clean_bstring(val):
    val = val.decode('utf-8')
    if isinstance(val, str) and val.startswith("b'") and val.endswith("'"):
        return val[2:-1]
    return val

# Define PxL script
PXL_SCRIPT = """
import px
df = px.DataFrame(table="tetragon.json")
px.display(df, "tetragon")
"""

# Create Pixie client and connect
px_client = pxapi.Client(token=PIXIE_API_TOKEN, server_url="getcosmic.ai")
conn = px_client.connect_to_cluster(PIXIE_CLUSTER_ID)

# Run script and process results
script = conn.prepare_script(PXL_SCRIPT)
tetragon_logs = []

for row in script.results("tetragon"):
    log = {}
    raw_payload = row["payload"]
    parsed_payload = json.loads(raw_payload)
    log[clean_bstring(row["type"])] = parsed_payload
    log["node_name"] = clean_bstring(row["node_name"])
    log["time"] = clean_bstring(row["time"])
    tetragon_logs.append(log)

stix_objects, bundles = transform_tetragon_to_stix(tetragon_logs)
print(json.dumps(stix_objects, indent=2))
