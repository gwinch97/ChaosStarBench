#!/bin/bash
# Set cgroup v2 memory.swap.max on hotelReservation application containers.
#
#   allow_swap.sh [app ...]          memory.swap.max=max on containers that have a memory limit
#   SWAP=0 allow_swap.sh app ...     memory.swap.max=0 on all of the app's containers
#   SWAP=0 MEM_MAX=6451M allow_swap.sh app ...   also memory.max on the app's main container, and
#                                                the service's oom_score_adj set to -500
#
# Why oom_score_adj (memhog_nn): Kubernetes gives burstable pods' processes oom_score_adj 999 and
# Chaos Mesh's stressor 1000, so right after a restart (tiny RSS) the kernel sometimes killed the
# service instead of the stressor; the container restarted, the stressor went with it and the
# fault ended early (3 of the first 4 capped memhog_nn runs, e.g. user killed after 44 stressor
# kills). -500 for the service makes the stressor the victim every time.
#
# Why MEM_MAX (memhog_nn): hotel's other pods use ~0.8 GB of the 8 GB node, so an uncapped 95%
# stressor fills the node completely before it is killed; that starved the kubelet (~70% of 5 s
# scrapes lost on the node). In the Social Network run the stressor topped out at ~6.1-6.3 GiB
# with the node ~92% full (other pods ~1.1 GB). Capping the target container at ~6.3 GiB gives the
# same node fullness (~7.1 GB of 7.8) and keeps the noisy-neighbour squeeze.
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
MEMMAX=${MEM_MAX:-}
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
        if [ -n \"$MEMMAX\" ] && [ \"\$(cat \$c/memory.current)\" -gt 2000000 ]; then
          echo $MEMMAX > \$c/memory.max
          # make the stressor (oom_score_adj 1000) the OOM victim, never the service (999 by default)
          for p in \$(cat \$c/cgroup.procs); do
            [ \"\$(cat /proc/\$p/comm 2>/dev/null)\" = memStress ] || echo -500 > /proc/\$p/oom_score_adj 2>/dev/null
          done
          echo \"oom_score_adj: \$(for p in \$(cat \$c/cgroup.procs); do echo -n \"\$(cat /proc/\$p/comm)=\$(cat /proc/\$p/oom_score_adj) \"; done)\"
        fi
        echo $VALUE > \$c/memory.swap.max && echo \"swap.max=\$(cat \$c/memory.swap.max) (memory.max=\$(cat \$c/memory.max))\"
      done" 2>&1 | tr '\n' ' ')
    echo "swap $VALUE $app on $node: ${res:-no matching containers}"
  done
done
exit 0
