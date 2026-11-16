#!/bin/bash
# Let the hotelReservation application containers use swap (cgroup v2 memory.swap.max=max).
#
# Why: the Social Network memory-leak runs (size: 95%, June 2025) show the stressor surviving the
# whole fault, its memory swapping between the 512Mi limit and a lower floor ~170 times an hour,
# which costs CPU in the faulted container. On today's WSL2 kernel (cgroup v2), Kubernetes 1.28
# without NodeSwap sets memory.swap.max=0 for every container, so the same stressor is OOM-killed
# and Chaos Mesh gives up after a few minutes. Allowing swap restores the Social Network behaviour.
# Containers without a memory limit (memory.max=max) are left alone; nothing else is changed.
#
# Usage: allow_swap.sh [app-label ...]   (default: the 8 hotel application services)
# Never fails the caller: prints what it changed or why it could not.
cd "$(dirname "$0")"
source ./config.sh
APPS=${*:-"frontend-$RELEASE geo-$RELEASE profile-$RELEASE rate-$RELEASE recommendation-$RELEASE reservation-$RELEASE search-$RELEASE user-$RELEASE"}
for app in $APPS; do
  kubectl get pods -n "$NAMESPACE" -l app="$app" \
    -o jsonpath='{range .items[*]}{.spec.nodeName}{" "}{.metadata.uid}{"\n"}{end}' 2>/dev/null |
  while read -r node uid; do
    [ -n "$node" ] || continue
    res=$(docker exec "$node" sh -c "
      d=\$(find /sys/fs/cgroup/kubepods.slice -maxdepth 3 -type d -name '*pod$(echo "$uid" | tr - _)*' | head -1)
      [ -n \"\$d\" ] || { echo 'no cgroup'; exit; }
      for c in \$d/docker-*.scope; do
        [ \"\$(cat \$c/memory.max)\" = max ] && continue
        echo max > \$c/memory.swap.max && echo \"swap.max=\$(cat \$c/memory.swap.max) (memory.max=\$(cat \$c/memory.max))\"
      done" 2>&1 | tr '\n' ' ')
    echo "allow_swap $app on $node: ${res:-no limited containers}"
  done
done
exit 0
