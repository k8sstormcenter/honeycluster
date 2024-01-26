#!/bin/bash

apt update
apt install -y curl
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
apt install -y python
python ./get-pip.py
pip install kubernetes
export KUBERNETES_SERVICE_HOST=kubernetes.default
export KUBERNETES_SERVICE_PORT=443
python ./create.py