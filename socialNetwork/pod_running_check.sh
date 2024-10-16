#!/bin/bash

pod_running_check() {
    namespace=$1
    pod_name_pattern=$2
    kubectl config set-context --current --namespace=$namespace
    while true; do
        pod_status=$(kubectl get pods --namespace=$namespace | grep $pod_name_pattern | awk '{print $3}')
        if [[ $pod_status == "Running" ]]; then
            break
        fi
        echo "Waiting for pod '$pod_name_pattern' in namespace '$namespace' to be Running..."
        sleep 5
    done
}

pod_running_check "$1" "$2"