#!/bin/zsh
docker buildx create --use
docker buildx build --platform linux/amd64 -t entlein/ping-app:latest  --push .