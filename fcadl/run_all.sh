#!/bin/bash
# All conditions in rounds: round r runs every fault x service once (rep r), so stopping early
# still leaves a balanced set. Skips datasets that already have fault_inject.txt (resumable).
# Usage: run_all.sh [n_rounds]   (default 2 -> 32 datasets, about 2.6 h each)
cd "$(dirname "$0")"
source ./config.sh
ROUNDS=${1:-2}
for rep in $(seq 0 $((ROUNDS - 1))); do
  for fault in $FAULTS; do
    for svc in $FAULT_SERVICES; do
      out="$DATA_DIR/${svc}_${fault}_sin_${rep}"
      if [ -f "$out/fault_inject.txt" ]; then echo "skip $out"; continue; fi
      bash ./run_one.sh "$fault" "$svc" "$rep" || echo "FAILED ${svc}_${fault}_sin_${rep}" | tee -a "$DATA_DIR/failures.log"
    done
  done
done
