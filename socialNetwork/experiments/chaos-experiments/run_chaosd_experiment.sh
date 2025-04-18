#!/bin/bash

# Check if 6 arguments are provided
if [ "$#" -ne 6 ]; then
    echo "Error: you must provide 6 arguments."
    echo "Usage: run_chaosd_experiment.sh <experiment> <severity=low/medium/high> <threads> <connections> <duration> <requests_per_second>"
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
    echo "Supported experiments (case sensitive):"
    echo "networkchaos physicalmachinechaos redischaos stresschaos"
    exit 1
fi

# Validate severity
case "$severity" in
    low)
        sh="low.sh"
        ;;
    medium)
        sh="medium.sh"
        ;;
    high)
        sh="high.sh"
        ;;
    *)
        echo "Error: Invalid severity value. Choose from 'low', 'medium', or 'high'."
        exit 1
        ;;
esac

duration_half=$((duration / 2))

cd ../../
# if this doesn't run, ensure there is a .venv folder inside socialnetwork
source .venv/bin/activate
# if this doesn't run, ensure you ran `make` on wrk2 directory

echo "----- RUN WORKLOAD BEFORE FAULT -----"
../wrk2/wrk -D exp -t $threads -c $connections -d $duration_half -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $requests_per_second

echo "----- INJECT CHAOS -----"
bash experiments/chaos-experiments/$experiment/$sh
# minikube ssh -- sudo chaosd attack network delay --device eth0 --latency 500ms --jitter 100ms

echo "----- RUN WORKLOAD AFTER FAULT -----"
../wrk2/wrk -D exp -t $threads -c $connections -d $duration_half -L -s ./wrk2/scripts/social-network/compose-post.lua http://localhost:8080/wrk2-api/post/compose -R $requests_per_second

echo "----- SCRAPING METRICS -----"
cd experiments/results/
python3 scrape_all_data.py $duration

echo "----- EXPERIMENT COMPLETE -----"
echo "Experiment results and metrics are stored in the 'results' directory"