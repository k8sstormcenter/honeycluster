# local development
```
poetry install
poetry run python manual.py
```
and additionally, you probably want both redis as well as stix-visualizer to be port-forwarded from your cluster.



# uploading your bundles for your patterns (while we dont have a UI)


> [!NOTE]
> This python module contains various "deduplicate_bundles" functions, this is most likely the first function you would change to get a different graph-slicing

Assuming  your lighteningrod is being forwarded to 8000 , you can execute the upload of a few default patterns

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


