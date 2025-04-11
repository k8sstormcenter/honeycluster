
sudo bash -c "$(curl -fsSL https://getcosmic.ai/install.sh)"
sudo apt install skopeo
skopeo list-tags docker://gcr.io/pixie-oss/pixie-prod/cloud-api_server_image
export PX_CLOUD_ADDR=getcosmic.ai
px auth login
px deploy --pem_memory_limit=1Gi
