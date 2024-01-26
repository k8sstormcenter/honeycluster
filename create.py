from kubernetes import client, config

def main():
    config.load_incluster_config()

    v1 = client.CoreV1Api()
    metadata = client.V1ObjectMeta(name='priv-pod')
    priv = client.V1SecurityContext(privileged=True)
    container1 = client.V1Container(name='nginx', image='nginx', security_context=priv)
    pod_spec = client.V1PodSpec(containers=[container1], host_pid=True)
    pod_body = client.V1Pod(metadata=metadata, spec=pod_spec, kind='Pod', api_version='v1')
    pod = v1.create_namespaced_pod(namespace='default', body=pod_body)

if __name__ == '__main__':
    main()
