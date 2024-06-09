# Tips and Tricks

## Add new keys to the baseline

If you want to add a new key to the baseline, you can use the following command and replace `<key>` with the key you want to add:

```bash
kubectl exec -n redpanda svc/redis-headless -- redis-cli SADD baseline "<key>"
```