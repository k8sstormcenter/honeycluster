curl -s "https://secretmanager.googleapis.com/v1/projects/$PROJECT_ID/secrets/secret/versions/1:access" \
    --header "authorization: Bearer $1" \
    --header "content-type: application/json" |
    jq -r '.payload.data' |
    base64 -d