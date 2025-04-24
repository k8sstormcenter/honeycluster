#!/bin/zsh
docker buildx create --use
docker buildx build  -t entlein/ping-app:arm  --push .