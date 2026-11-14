#!/bin/bash
# One FC-ADL hotelReservation dataset, following socialNetwork/.../run_chaos_sin.sh:
# fresh cluster -> time-varying load for PRE_FAULT_S -> fault for FAULT_S -> scrape last
# SCRAPE_WINDOW_S -> convert to cpu_usage.csv + fault_inject.txt.
# Usage: run_one.sh <fault: cpuhog|memhog|memhog_nn|networkdelay> <service> <rep> [workload_folder]
# Output: $DATA_DIR/<service>_<fault>_sin_<rep>/
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh
FAULT=$1; SVC=$2; REP=$3; WL=${4:-$REP}
NAME="${SVC}_${FAULT}_sin_${REP}"
OUT="$DATA_DIR/$NAME"
CHAOS="chaos/$FAULT/$SVC.yaml"
WLDIR="../socialNetwork/locust/workloads/sin/$WL"
[ -f "$CHAOS" ] || { echo "no manifest $CHAOS"; exit 1; }
[ -d "$WLDIR" ] || { echo "no workload folder $WLDIR"; exit 1; }
mkdir -p "$OUT"
exec > >(tee -a "$OUT/run.log") 2>&1
echo "== $NAME  $(date "+%Y-%m-%dT%H:%M:%S%z")  commit $(git rev-parse --short HEAD)"

VALUES=values-fcadl.yaml
[ "$FAULT" = memhog ] && VALUES=values-memlimit.yaml
minikube delete || true
bash ./k8startup_hotel.sh "$VALUES"

# three request streams, each following one of the Social Network sinusoidal workloads
PIDS=()
for pair in "search:cp" "recommend:hts" "reserve:uts"; do
  req=${pair%%:*}; csv=${pair##*:}
  HOTEL_REQUEST=$req HOTEL_CSV="$WLDIR/${csv}_workload.csv" LOCUST_HOST="http://localhost:$FRONTEND_PORT" \
    locust --headless -f locust/locust_hotel.py --only-summary >"$OUT/locust_$req.log" 2>&1 &
  PIDS+=($!)
done
echo "load started $(date "+%Y-%m-%dT%H:%M:%S%z")"
sleep "$PRE_FAULT_S"

kubectl apply -f "$CHAOS"
date +%s > "$OUT/fault_time.txt"
echo "fault applied $(date "+%Y-%m-%dT%H:%M:%S%z"): $CHAOS"
sleep "$FAULT_S"
kubectl delete -f "$CHAOS" --ignore-not-found
kill "${PIDS[@]}" 2>/dev/null || true

python3 scrape_cpu.py "${SCRAPE_WINDOW_S}s" "$OUT" --namespace "$NAMESPACE" --prom "http://localhost:$PROM_PORT"
python3 make_dataset.py "$OUT" --duration "$SCRAPE_WINDOW_S" --step "$STEP_S"
kubectl get pods -A -o json | jq -r '["name","namespace","node"], (.items[] | [.metadata.name, .metadata.namespace, .spec.nodeName]) | @csv' > "$OUT/deployment.csv"
cp "$CHAOS" "$VALUES" "$OUT/"
echo "== done $NAME $(date "+%Y-%m-%dT%H:%M:%S%z"), fault_inject=$(cat "$OUT/fault_inject.txt")"
