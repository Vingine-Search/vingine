#!/bin/bash

docker pull getmeili/meilisearch:v1.2
docker run -it --rm -p 7700:7700 \
 -e MEILI_ENV='development' \
 -e MEILI_MASTER_KEY=$(cat master_key) \
 -v $(pwd)/meili_data:/meili_data getmeili/meilisearch:v1.2
