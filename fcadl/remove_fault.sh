#!/bin/bash
# Remove a Chaos Mesh fault, even if Chaos Mesh cannot (e.g. its daemon on a node starved by a
# memory stressor): normal delete with a timeout; if that hangs, kill the stressor processes on
# every node directly, clear the fault's finalizers and delete again.
# Usage: remove_fault.sh MANIFEST
cd "$(dirname "$0")"
MAN=$1
timeout 90 kubectl delete -f "$MAN" --ignore-not-found && exit 0
echo "remove_fault: delete did not finish in 90 s, killing stressors directly $(date +%T)"
NODES=$(minikube node list 2>/dev/null | awk '{print $1}')
for attempt in 1 2 3; do
  for n in $NODES; do timeout 30 docker exec "$n" sh -c 'pkill -9 -x memStress; pkill -9 -f stress-ng' 2>/dev/null; done
  timeout 30 kubectl patch -f "$MAN" --type=merge -p '{"metadata":{"finalizers":[]}}' 2>/dev/null
  timeout 60 kubectl delete -f "$MAN" --ignore-not-found --wait=false 2>/dev/null
  sleep 5
  left=0
  for n in $NODES; do left=$((left + $(timeout 30 docker exec "$n" sh -c 'pgrep -x memStress | wc -l' 2>/dev/null || echo 0))); done
  if ! timeout 30 kubectl get -f "$MAN" >/dev/null 2>&1 && [ "$left" -eq 0 ]; then
    echo "remove_fault: removed after forced cleanup (attempt $attempt)"; exit 0
  fi
done
echo "remove_fault: WARNING fault or stressor may still be present"
exit 1
