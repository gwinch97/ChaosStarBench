#!/bin/bash

pod_ready_check() {
    namespace=$1
    pod_name_pattern=$2
    kubectl config set-context --current --namespace=$namespace
    while true; do
        pod_readies=$(kubectl get pods --namespace=$namespace | grep $pod_name_pattern | awk '{print $2}')
        
        all_ready=true
        while read -r ready_status; do
            # Split the READY value into two numbers
            first_number=$(echo $ready_status | cut -d'/' -f1)
            second_number=$(echo $ready_status | cut -d'/' -f2)
            
            # Check if the first number matches the second
            if [[ $first_number -ne $second_number ]]; then
                all_ready=false
                break
            fi
        done <<< "$pod_readies"
        
        if $all_ready; then
            echo "All pods matching '$pod_name_pattern' in namespace '$namespace' are fully ready."
            break
        fi
        
        echo "Waiting for all pods matching '$pod_name_pattern' in namespace '$namespace' to be fully ready..."
        sleep 15
    done
}

pod_ready_check "$1" "$2"

