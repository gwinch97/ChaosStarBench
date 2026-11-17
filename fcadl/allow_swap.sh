#!/bin/bash
# Set cgroup v2 memory.swap.max on hotelReservation application containers.
#
#   allow_swap.sh [app ...]          memory.swap.max=max on containers that have a memory limit
#   SWAP=0 allow_swap.sh app ...     memory.swap.max=0 on all of the app's containers
#
# Why (memhog): the Social Network memory-leak runs (size: 95%, June 2025) show the stressor
# surviving the whole fault, its memory swapping between the 512Mi limit and a lower floor ~170
# times an hour, which costs CPU in the faulted container. On today's WSL2 kernel (cgroup v2),
# Kubernetes 1.28 without NodeSwap sets memory.swap.max=0 for limited containers, so the same
# stressor is OOM-killed and Chaos Mesh gives up after a few minutes. Allowing swap restores it.
#
# Why (memhog_nn, SWAP=0 on the target): with no memory limit the 95% stressor fills the 8 GB node.
# If it may swap, the node swaps it (Docker Desktop gives the node container swap) and thrashes,
# using ~20 host cores, instead of OOM-killing it; the Social Network no-limit runs show the
# stressor killed and regrowing (RSS ~6 GB median with deep drops). No swap for the target gives that.
#
# Never fails the caller: prints what it changed or why it could not.
cd "$(dirname "$0")"
source ./config.sh
VALUE=${SWAP:-max}
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
        [ \"$VALUE\" = max ] && [ \"\$(cat \$c/memory.max)\" = max ] && continue
        echo $VALUE > \$c/memory.swap.max && echo \"swap.max=\$(cat \$c/memory.swap.max) (memory.max=\$(cat \$c/memory.max))\"
      done" 2>&1 | tr '\n' ' ')
    echo "swap $VALUE $app on $node: ${res:-no matching containers}"
  done
done
exit 0
