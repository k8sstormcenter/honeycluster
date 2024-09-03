
#!/bin/bash

# Fetch the OAuth2 token from the metadata server 
# Option 1 - Shell into your GKE node and run the following command:
TOKEN=$(curl -s -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" | jq -r '.access_token')
# Option 2 : port forward the minimi-service to 8080 and run the following command
@Tobiasgrantner 

# Bearer token (this one is expired!)
TOKEN="ya29.c.c0ASRK0GZ0gHhyqGh3MncKEsuflP-0vHnu4AUHpbQPCKD6vstw18mdjZFFOJmzNUjG53MWV97kiIJpMmUnxpda4_WjZvS8Qi9A57iPq_KUi3CjV-L9IFyuhCcIzrsLwiBdSaLIOrCz1OfgsTPPjula2lXAF5u6Uc1YzWeKX5R6Epk_KTpTHXu-1jWN_Oogth_BlR7whwdTfbyLQ2-LZ-GB2YC7ok2WCJ9EclN3jRkZG7xZ3_8ZxQuHOa-eRWObnaIAjgD1cBuIjgOEpxk5tJfzvkSPN6ArpW_SFtldAGQxxZwOkvyGgYnQglHVEoCIaqVdJ-cUC5awk35RAzDWsUBdeXm-ju1GDaCSjZHLSrJKv4peGHKQ9dAUuEvsayOfCaYlk_kUFwcEqqPlBcs5BXD72nXsyQv1KroGBxv3EddjJPLwqgulkJfoxPM1njqgGTQmMS9-7qgaWaDwwPl4YA1QfJEt_PPUlU7G1IZudzlFp9X7IQTnoVkjSvaCr5ja4opSjTc72vMYtST6K5XkIk2lc5k4taV0xb8NYkA3hYGHEUD0_xOwQZbF5b2S3NvNEpi-FfGyE9iXKthy3xytN0dYNwT_QcCSkC7HYVaIU_VPfYt9tspdInBT8abEN641P4gckRBJ8RMruarhxzQ4j0qekQVvcf1dueXfubWRM32VhfI1dYWtZqW8jccxu-o4smBWqnMnfwVXO2VVSYSBvpe4YMQ15z3tq2515uw-0OvUBXM2jxFdi8o20Xzcy8kZpXgehrfj3qbpbOJxvk7rUSQ-687Z1u1Y-QUkjqbzx_9gVSFzSimgOMSq2fg0bn88FndhFMez5VMw2XVndnX3p_3x7hgYy60d0oZ4SSi6l97w605lbgIl_YdXvOrwv-QbizkaoW0sgZJQd3qdSR3fW2haxX1kaffwim9pyZ8tlrnsJYpoQSzu4YuW2cOm_a3vU0d0dwnWmUzlZxMys63BSn2ctZVUh5vozm3l1uZiiSj4SyYV6vYnyt-O42x"

# KMS Decrypt API endpoint
PROJECT_ID="my-gcp-projectid"
LOCATION="my-gcp-project-location"
KEY_RING="my-gcp-key-ring"
KEY_NAME="my-kms-key"
API_ENDPOINTE="https://cloudkms.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/keyRings/$KEY_RING/cryptoKeys/$KEY_NAME:encrypt"
API_ENDPOINTD="https://cloudkms.googleapis.com/v1/projects/$PROJECT_ID/locations/$LOCATION/keyRings/$KEY_RING/cryptoKeys/$KEY_NAME:decrypt"

# Encrypted data (base64-encoded)
CIPHERTEXT="CiUAcbrqDGs8UAomoDqUwaLNRibC2xZvIbaZgKtqzbaexKMuOIoCEjgAwJ+FDfCbch6hqFxgQxsxmi2Q2N0wpetzPL7GS3AimxWm/Tiy2Selzl5m0xQ5I5k+SCppH7yx6Q=="
PLAINTEXT="dGhpcyBpcyBzZWNyZXQK"


# Prepare the request payload
PAYLOAD=$(jq -n --arg plaintext "$PLAINTEXT" '{plaintext: $plaintext}')

# Make the HTTP request
curl -X POST "$API_ENDPOINTE" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"


# Prepare the request payload
PAYLOAD=$(jq -n --arg ciphertext "$CIPHERTEXT" '{ciphertext: $ciphertext}')
curl -X POST "$API_ENDPOINTD" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD"