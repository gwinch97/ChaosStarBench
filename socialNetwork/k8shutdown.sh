#!/bin/bash

node_names=$(kubectl get nodes --no-headers | awk '{print $1}')

for node in $node_names; do
  if [[ "$node" == *"service"* ]]; then
      kubectl drain $node --ignore-daemonsets
  fi
done

minikube stop