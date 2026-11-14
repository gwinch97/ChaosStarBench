#!/bin/bash
# End-to-end dry run of run_one.sh on this machine: fake minikube/kubectl/helm (logged), a stub
# hotel frontend, real Locust, a stub Prometheus with a synthetic CPU-hog fault on `search`, then
# the real scraper and converter. Short timings (15 s load, 10 s fault).
cd "$(dirname "$0")/.."
export DATA_DIR=$(mktemp -d) FAKE_LOG=$(mktemp) FRONTEND_PORT=18501 PROM_PORT=19091 PRE_FAULT_S=15 FAULT_S=10
export PATH="$PWD/tests/fake_bin:$PWD/.venv-test/bin:$PATH"
.venv-test/bin/python tests/stub_hotel.py $FRONTEND_PORT $DATA_DIR/requests.jsonl & H=$!
.venv-test/bin/python tests/stub_prometheus.py $PROM_PORT $DATA_DIR/search_cpuhog_sin_0/fault_time.txt search & P=$!
sleep 1
bash ./run_one.sh cpuhog search 0 > $DATA_DIR/sim.out 2>&1; rc=$?
kill $H $P 2>/dev/null; pkill -f "fake_bin/kubectl port-forward" 2>/dev/null
echo "run_one.sh exit $rc"; echo "DATA_DIR=$DATA_DIR"
ls $DATA_DIR/search_cpuhog_sin_0
echo "--- fake cluster calls:"; grep -E "minikube\] delete|helm\] upgrade|manifest" $FAKE_LOG | sed 's/^/  /'
echo "--- requests served during the run: $(wc -l < $DATA_DIR/requests.jsonl), rejected: $(grep -c '"ok": false' $DATA_DIR/requests.jsonl)"
tail -3 $DATA_DIR/sim.out
