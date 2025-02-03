#!/bin/bash

node_names=$(kubectl get nodes --no-headers | awk '{print $1}')

for node in $node_names; do
  if [[ "$deploy" == *"elasticsearch"* ]]; then
    continue
  fi
  kubectl drain $node --ignore-daemonsets
done

minikube stop