#!/bin/bash
# Stop the collection (tmux session "fcadl") cleanly once the dataset currently running is written,
# then free the machine: stop Locust and port-forwards, delete the cluster, and remove the folder
# of any dataset that had only just started. Resume later with the usual tmux/run_all.sh command;
# run_all.sh skips every dataset that has fault_inject.txt.
# Usage: bash stop_after_current.sh          (waits; run it in a second terminal or with nohup)
#        bash stop_after_current.sh --now    (stop immediately; the running dataset is redone later)
cd "$(dirname "$0")"
source ./config.sh
current() { for d in "$DATA_DIR"/*_sin_*; do [ -f "$d/fault_inject.txt" ] || { echo "$d"; return; }; done; }
CUR=$(current)
if [ "$1" != "--now" ] && [ -n "$CUR" ]; then
  echo "waiting for $(basename "$CUR") to finish ..."
  until grep -qE "^== done|ABORT" "$CUR/run.log" 2>/dev/null || ! tmux has-session -t fcadl 2>/dev/null; do sleep 2; done
fi
tmux kill-session -t fcadl 2>/dev/null && echo "stopped collection $(date +%T)"
sleep 3
pkill -f 'run_one.s[h]'; pkill -f 'locust [-]-headless'; pkill -f 'kubectl port-[f]orwar[d]'
for d in "$DATA_DIR"/*_sin_*; do
  [ -f "$d/fault_inject.txt" ] || { echo "removing unfinished $(basename "$d")"; rm -rf "$d"; }
done
minikube delete >/dev/null 2>&1 && echo "cluster deleted"
echo "done; $(ls -d "$DATA_DIR"/*_sin_*/fault_inject.txt 2>/dev/null | wc -l) datasets complete"
