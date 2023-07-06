#!/bin/bash

cd $(dirname $0)

if [ "$( docker container inspect -f '{{.State.Running}}' meili-vingine 2> /dev/null )" = "true" ]
then
    uvicorn main:api --reload --port 9000
else
    echo "MeiliSearch isn't running. Aborting..."
fi


