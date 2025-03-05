#!/bin/bash

pod_name=$1
requests=$2

if [ -z "$1" ] || [ -z "$2" ]; then # check arg1
    echo "Usage: bash cache-penetration.sh <pod_name> <requests>";
	exit 0;
fi

if [ "$pod_name" != "home-timeline-redis" ] && [ "$pod_name" != "social-graph-redis" ] && [ "$pod_name" != "user-timeline-redis" ]; then
    echo "Error: this experiment can only run on 'home-timeline-redis', 'social-graph-redis' or 'user-timeline-redis' pods.";
    exit 0;
fi

# close any current redis port forwards
SESSION_NAMES=("redis-pf")
for SESSION_NAME in "${SESSION_NAMES[@]}"; do
    if screen -list | grep -q "\.${SESSION_NAME}"; then
        screen -X -S "$SESSION_NAME" quit
    fi
done

# forward ports for the specific redis db
echo "Creating a screen to forward the ports for ${pod_name}";
screen -dmS redis-pf bash -c "../../../k8pod_check.sh socialnetwork ${pod_name}; kubectl get pods -n socialnetwork | grep '${pod_name}' | awk '{print \$1}' | xargs -I {} kubectl port-forward -n socialnetwork {} 6379:6379; exec bash";

sudo chaosd attack redis cache-penetration -a 127.0.0.1:6379 --request-num ${requests}