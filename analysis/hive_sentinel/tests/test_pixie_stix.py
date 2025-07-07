import json
from src.stix.pixie.transform_dns_to_stix import transform_dns_row_to_stix
from src.stix.pixie.transform_http_to_stix import transform_http_row_to_stix

def test_transform_dns_row_to_stix():
    dns_row = {
        "time_": 1751871579697,
        "upid": "00000003-0000-3529-0000-0000000118f6",
        "remote_addr": "10.43.0.10",
        "remote_port": 53,
        "local_addr": "-",
        "local_port": -1,
        "trace_role": 1,
        "encrypted": False,
        "req_header": json.dumps({"txid": 12521, "qr": 0}),
        "req_body": json.dumps({"queries": [{"name": "test.domain.local", "type": "A"}]}),
        "resp_header": json.dumps({"txid": 12521, "qr": 1, "rcode": 3}),
        "resp_body": json.dumps({"answers": []}),
        "latency": 1725467
    }

    stix_objects = transform_dns_row_to_stix(dns_row)
    assert isinstance(stix_objects, list)
    assert any(obj["type"] == "network-traffic" for obj in stix_objects)
    assert any(obj["type"] == "observed-data" for obj in stix_objects)

    # Check that extracted fields exist
    net_obj = next(obj for obj in stix_objects if obj["type"] == "network-traffic")
    ext = net_obj["extensions"]["x-pixie-dns-ext"]
    assert ext["query_name"] == "test.domain.local"
    assert ext["query_type"] == "A"
    assert ext["response_code"] == 3

    print("✅ DNS STIX Transformation Successful:\n", json.dumps(stix_objects, indent=2))

def test_transform_http_row_to_stix():
    http_row = {
        "time_": 1751871558248,
        "upid": "00000004-0000-0e03-0000-00000000166d",
        "remote_addr": "10.42.0.1",
        "remote_port": 39498,
        "local_addr": "10.42.0.6",
        "local_port": 8080,
        "trace_role": 2,
        "encrypted": False,
        "major_version": 1,
        "minor_version": 1,
        "content_type": 0,
        "req_headers": json.dumps({"Host": "10.42.0.6:8080"}),
        "req_method": "GET",
        "req_path": "/ping",
        "req_body": "",
        "req_body_size": 0,
        "resp_headers": json.dumps({"Content-Length": "2"}),
        "resp_status": 200,
        "resp_message": "OK",
        "resp_body": "<removed>",
        "resp_body_size": 2,
        "latency": 118716
    }

    stix_objects = transform_http_row_to_stix(http_row)
    assert isinstance(stix_objects, list)
    assert any(obj["type"] == "network-traffic" for obj in stix_objects)
    assert any(obj["type"] == "observed-data" for obj in stix_objects)

    # Check that extracted fields exist
    net_obj = next(obj for obj in stix_objects if obj["type"] == "network-traffic")
    ext = net_obj["extensions"]["x-pixie-http-ext"]
    assert ext["method"] == "GET"
    assert "/ping" in ext["url"]
    assert ext["status_code"] == 200

    print("✅ HTTP STIX Transformation Successful:\n", json.dumps(stix_objects, indent=2))
