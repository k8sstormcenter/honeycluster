# Tips and Tricks

## Add new keys to the baseline

If you want to add a new key to the `baseline` topic, you can use the following command and replace `<key>` with the key you want to add:

```bash
kubectl exec -n redpanda redpanda-src-0 -c redpanda -- /bin/bash -c "echo null | rpk topic produce baseline --key <key>"
```