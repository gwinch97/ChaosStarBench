#!/bin/bash

# Check if 6 arguments are provided
if [ "$#" -ne 6 ]; then
    echo "Error: you must provide 6 arguments."
    echo "Usage: ./run_experiment.sh <experiment> <severity=low/medium/high> <threads> <connections> <duration> <requests_per_second>"
    exit 1
fi

experiment="$1"
severity="$2"
threads="$3"
connections="$4"
duration="$5"
requests_per_second="$6"

# Validate experiment
EXPERIMENT_NAMES=("iochaos" "networkchaos" "physicalmachinechaos" "podchaos" "redischaos" "stresschaos")
experiment_found=false

# Disable case sensitivity
shopt -s nocasematch

# Loop through the array to check if $experiment is in $EXPRIMENT_NAMES
for exp in "${EXPERIMENT_NAMES[@]}"; do
    if [ "$exp" == "$experiment" ]; then
        experiment_found=true
        break
    fi
done

if [ "$experiment_found" == false ]; then
    echo "Error: Experiment '$experiment' is not found."
    exit 1
fi

# Validate severity
case "$severity" in
    low)
        yaml="*-low.yaml"
        ;;
    medium)
        yaml="*-medium.yaml"
        ;;
    high)
        yaml="*-high.yaml"
        ;;
    *)
        echo "Error: Invalid severity value. Choose from 'low', 'medium', or 'high'."
        exit 1
        ;;
esac

duration_half=$((duration / 2))

cd ../../

# run workload for 30 mins without chaos
../wrk2/wrk -D exp -t $threads -c $connections -d $duration_half -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $requests_per_second

# inject chaos
cd experiments/chaos-experiments/$experiment
kubectl apply -f $yaml

# run workload for another 30 mins with chaos
cd ../../../
../wrk2/wrk -D exp -t $threads -c $connections -d $duration_half -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $requests_per_second

# scrape metrics
source .venv/bin/activate
python3 experiments/chaos-experiments/scrape_all_data.py