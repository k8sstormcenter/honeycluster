
sudo bash -c "$(curl -fsSL https://getcosmic.ai/install.sh)"
add to PATH
export PX_CLOUD_ADDR=getcosmic.ai
px auth login
px deploy --pem_memory_limit=1Gi
