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

# The kernel clock must run at the hardware rate: on WSL2 something adjusted the tick by up to
# 9%, which stretched every phase and left ~11% of 5 s samples empty (zeros) after alignment.
# Usage: clock_check LABEL [FILE]: with FILE, compare against the clocks saved there (whole run);
# without, measure over 10 s and save the clocks to $OUT/.clock_start.
clock_check() {
  python3 - "$1" "${2:-}" "$OUT/.clock_start" <<'PY'
import sys, time
label, ref, save = sys.argv[1:4]
now = lambda: (time.monotonic(), time.clock_gettime(time.CLOCK_MONOTONIC_RAW))
if ref:
    m0, r0 = map(float, open(ref).read().split())
else:
    m0, r0 = now(); time.sleep(10)
m1, r1 = now()
err = ((m1 - m0) - (r1 - r0)) / (r1 - r0)
print(f"clock check ({label}, {r1 - r0:.0f} s): monotonic/raw rate error {err:+.3%}")
if not ref: open(save, "w").write(f"{m1} {r1}")
sys.exit(0 if abs(err) < 0.005 else 1)
PY
}
clock_check start || { echo "ABORT: kernel clock is being adjusted (tick/freq), not collecting"; exit 1; }

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
# no fault_inject.txt on failure, so run_all.sh will redo this dataset
clock_check run "$OUT/.clock_start" || { echo "ABORT: kernel clock drifted during the run; dataset not written"; exit 1; }

python3 scrape_cpu.py "${SCRAPE_WINDOW_S}s" "$OUT" --namespace "$NAMESPACE" --prom "http://localhost:$PROM_PORT"
python3 make_dataset.py "$OUT" --duration "$SCRAPE_WINDOW_S" --step "$STEP_S"
kubectl get pods -A -o json | python3 -c 'import csv,json,sys; w=csv.writer(sys.stdout,quoting=csv.QUOTE_ALL,lineterminator="\n"); w.writerow(["name","namespace","node"]); [w.writerow([p["metadata"]["name"],p["metadata"]["namespace"],p["spec"].get("nodeName","")]) for p in json.load(sys.stdin)["items"]]' > "$OUT/deployment.csv"
cp "$CHAOS" "$VALUES" "$OUT/"
echo "== done $NAME $(date "+%Y-%m-%dT%H:%M:%S%z"), fault_inject=$(cat "$OUT/fault_inject.txt")"
