# uploading your bundles for your patterns (while we dont have a UI)

> [!NOTE]
> there are some bugs with the `stix id = null`, that I m still debugging

Identify on which IP your lighteningrod is being forwarded to and edit the script, then execute the upload

```bash
chmod +x testpost.sh
./testpost.sh
```


{"bundle_id":"1","message":"STIX attack bundle added successfully"}  
{"bundle_id":"2","message":"STIX attack bundle added successfully"}  
{"bundle_id":"3","message":"STIX attack bundle added successfully"}  
{"bundle_id":"4","message":"STIX attack bundle added successfully"}  
{"bundle_id":"5","message":"STIX attack bundle added successfully"}  
{"bundle_id":"6","message":"STIX attack bundle added successfully"}  


# Execute the conversion and the matchin (there will be a button for this) 

```bash
curl -X GET "http://localhost:8000/convert_to_stix?i=0"
{"message":"STIX conversion successful"}
```

In your flask logs you should see:

```
...
Writing to Redis key: tetrastix2
success
Writing to Redis key: tetrastix2
success
Writing to Redis key: tetrastix2
success
Writing to Redis key: tetrastix2
success
Writing to Redis key: tetrastix2
indicator--kh-ce-sys-ptrace
indicator--kh-ce-nsenter
indicator--kh-ce-module-load
indicator--kh-ce-net-mitm
indicator--kh-ce-var-log-symlink
indicator--kh-ce-priv-mount
```

Now, (once the bug is found) you can use the visualizer to display your identified attack paths
