#!/bin/bash
# Run the three Locust streams for 30 s against the stub frontend with a stepped workload
# (5 -> 15 -> 30 rps, 10 s each) and report per-endpoint rates and parameter errors.
set -e
cd "$(dirname "$0")/.."
T=$(mktemp -d); PORT=18500
printf '5\n%.0s' {1..10} > $T/w.csv; printf '15\n%.0s' {1..10} >> $T/w.csv; printf '30\n%.0s' {1..10} >> $T/w.csv
.venv-test/bin/python tests/stub_hotel.py $PORT $T/req.jsonl & STUB=$!
sleep 1
for req in search recommend reserve; do
  HOTEL_REQUEST=$req HOTEL_CSV=$T/w.csv LOCUST_HOST=http://127.0.0.1:$PORT \
    .venv-test/bin/locust --headless -f locust/locust_hotel.py --only-summary --loglevel ERROR >$T/$req.log 2>&1 &
done
wait $(jobs -p | grep -v "^$STUB$") 2>/dev/null || true
sleep 2; kill $STUB
.venv-test/bin/python - "$T/req.jsonl" <<'PY'
import json, sys, collections
rows = [json.loads(l) for l in open(sys.argv[1])]
t0 = min(r["t"] for r in rows)
bad = [r for r in rows if not r["ok"]]
print(f"{len(rows)} requests, {len(bad)} rejected", collections.Counter(r["why"] for r in bad).most_common(3))
for p in ["/hotels", "/recommendations", "/user", "/reservation"]:
    ts = [r["t"] - t0 for r in rows if r["path"] == p]
    seg = [sum(1 for t in ts if a <= t < a + 10) / 10 for a in (0, 10, 20)]
    print(f"{p:17s} n={len(ts):4d}  rps in 0-10 s / 10-20 s / 20-30 s: " + " / ".join(f"{x:5.1f}" for x in seg))
PY
