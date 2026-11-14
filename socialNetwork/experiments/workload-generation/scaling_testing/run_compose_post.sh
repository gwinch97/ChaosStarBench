#!/bin/bash

if [ "$#" -ne 4 ]; then
    echo "Error: you must provide 4 arguments."
    echo "Usage: ./run_compose_post.sh <threads> <connections> <duration> <requests_per_second>"
    exit 0
fi

threads=$1
connections=$2
duration=$3
requests_per_second=$4

cd ../../

python3 experiments/workload-generation/graph_generator.py $requests_per_second $duration compose &
../wrk2/wrk -D exp -t $threads -c $connections -d $duration -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $requests_per_second