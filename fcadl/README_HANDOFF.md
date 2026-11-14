# FC-ADL second deployment: hotelReservation on ChaosStarBench (WSL handoff)

Goal: collect FC-ADL datasets for DeathStarBench **hotelReservation** with the same protocol as the
Social Network datasets in the paper (time-varying Locust load, Chaos Mesh faults, Prometheus CPU at
5 s), on Giles's WSL Ubuntu machine. Deadline context: NOMS 2027 submission on 22 Nov 2026; data
should be collected by about 20 Nov.

Everything here was written and checked on a Mac without a cluster (see "What has been tested").
**Nothing has run on a real cluster yet.** Steps 3 and 4 below are the first real tests.

## What is in `fcadl/`

| File | Purpose |
|---|---|
| `config.sh` | All settings (namespace, fault services, timings, cluster size, output dir). Every value can be overridden from the environment. |
| `k8startup_hotel.sh [values file]` | Fresh minikube cluster (as `socialNetwork/k8startup.sh`: 5 nodes × 2 CPU × 8 GB, kubelet housekeeping 1 s, CSI hostpath, Prometheus local PV), hotelReservation via Helm, Prometheus, Chaos Mesh, chaosd on the nodes, port-forwards (frontend :5000, Prometheus :9090), health checks. |
| `values-fcadl.yaml`, `values-memlimit.yaml` | Helm overlays: CPU 50m / memory 128Mi requests on the 8 application services, no limits; `values-memlimit` adds a 512Mi memory limit (used for the `memhog` fault only; `memhog_nn` = noisy neighbour, no limit). |
| `chaos/<fault>/<service>.yaml`, `chaos/gen_chaos.py` | Chaos Mesh manifests: `cpuhog` (StressChaos, 2 workers, 100%), `memhog` and `memhog_nn` (StressChaos memory, 1 worker, 95%), `networkdelay` (NetworkChaos 50 ms ± 50 ms); one pod, 3600 s. Parameters follow the Social Network runs. |
| `locust/locust_hotel.py` | Time-varying load: `HOTEL_REQUEST=search|recommend|reserve`, users per second from `HOTEL_CSV`. Requests copy `hotelReservation/wrk2/scripts/hotel-reservation/mixed-workload_type_1.lua`. |
| `run_one.sh <fault> <service> <rep> [workload]` | One dataset: fresh cluster → 3 Locust streams (search ← `sin/<rep>/cp_workload.csv`, recommend ← `hts`, reserve ← `uts`) → 90 min → apply fault, record `fault_time.txt` → 60 min → remove fault → scrape last 2 h → `make_dataset.py`. ≈ 2.6 h. |
| `run_all.sh [rounds]` | Every fault × service, in rounds (round r = rep r), resumable (skips datasets with `fault_inject.txt`). Default 2 rounds = 32 datasets ≈ 85 h. Failures go to `$DATA_DIR/failures.log`. |
| `scrape_cpu.py` | Raw per-pod `container_cpu_usage_seconds_total` and `container_memory_rss` for the last window (as `socialNetwork/scrape_k8metrics_old.py`, which produced the published data), any namespace. |
| `make_dataset.py` | `cpu_usage.json` → `cpu_usage.csv` (CPU-seconds per 5 s, one column per pod) and `fault_inject.txt` (5 s sample index of the fault). |
| `tests/` | Local checks (below); `tests/fake_bin` holds fake `minikube`/`kubectl`/`helm` used only by `simulate_run.sh`. |

Output per dataset: `$DATA_DIR/<service>_<fault>_sin_<rep>/` with `cpu_usage.csv`, `fault_inject.txt`,
raw JSONs, `deployment.csv`, the manifest and values file used, Locust logs and `run.log`.
Default `DATA_DIR=~/projects/hotel-data`.

## Steps on WSL

1. **Get the code.** Branch `fcadl-paper-experiments` of `gwinch97/ChaosStarBench` (Giles to push it from
   `~/Developer/ChaosStarBench-wsl` on the Mac, or copy that folder over). Work in `ChaosStarBench/fcadl`.
2. **Tools.** Docker (WSL integration), minikube, kubectl, helm, jq, Python 3.10+. Create a venv and
   `pip install locust requests pandas numpy pyyaml jsonschema`; make sure `python3` and `locust` on
   `PATH` are that venv's (activate it before running). Check free resources: about 10+ cores and
   40+ GB RAM for the 5-node cluster (reduce `N_NODES` etc. in `config.sh` if needed, but keep it the
   same for all runs).
3. **Local tests on WSL** (no cluster): `python tests/test_chaos_schema.py`, `bash tests/test_locust.sh`,
   `bash tests/simulate_run.sh`. All three should pass as they did on the Mac.
4. **Bring the cluster up once and smoke-test:** `bash k8startup_hotel.sh`. Then check:
   - `kubectl get pods -n hotelreservation` all Running;
   - `curl "localhost:5000/hotels?inDate=2015-04-09&outDate=2015-04-10&lat=38.0235&lon=-122.095"`
     returns hotels (if empty, the databases were not seeded; hotelReservation services normally seed
     their MongoDB on start — check service logs);
   - `curl -s 'localhost:9090/api/v1/query?query=container_cpu_usage_seconds_total{namespace="hotelreservation"}' | jq '.data.result | length'`
     is > 0 and pods have a `pod` label;
   - a manual `kubectl apply -f chaos/cpuhog/search.yaml` shows in `kubectl get stresschaos -n hotelreservation`
     and the search pod's CPU rises in Prometheus; then `kubectl delete -f` it.
5. **Short real run:** `PRE_FAULT_S=900 FAULT_S=600 SCRAPE_WINDOW_S=1200 bash run_one.sh cpuhog search 99 0` (rep 99, workload folder 0)
   (≈ 30 min). Check `cpu_usage.csv` (one column per pod, no consul/jaeger), `fault_inject.txt` = 120 (fault 600 s before the end of a 1200 s window; full runs give 720),
   and that `search-hotelres` CPU jumps after that index. Delete the `_99` folder afterwards.
6. **Collection:** in tmux/screen: `bash run_all.sh 2`. Round 1 (16 datasets, ≈ 42 h) gives a complete
   balanced set; round 2 doubles it. Watch `$DATA_DIR/*/run.log` and `failures.log`.

## Decisions taken without Giles (change before collecting if wrong)

1. Fault services: search, recommendation, reservation, user (one per request type).
2. Load: the three Social Network sinusoidal workload CSVs, mapped search ← cp, recommend ← hts,
   reserve ← uts (reserve stream is 50% login, 50% reservation).
3. Memory limits: 512Mi for `memhog`, none for `memhog_nn`; the limits the Social Network `memhog`
   (non-NN) runs used are not recorded anywhere.
4. Traces (Jaeger) are not collected; FC-ADL only needs CPU.

## Known gaps

- The script that converted the published Social Network JSONs to CSV was not found. `make_dataset.py`
  uses the Fig. 2 notebook's steps; on `cp_cpuhog_sin_0` it matches 57% of values exactly (median
  difference 0) but not all. New hotel datasets are internally consistent.
- Several surviving Social Network manifests were edited after the paper's data was collected
  (e.g. `cpuhogchaos/hts_cpuhog.yaml` targets user-timeline; `cp_cpuhog.yaml` lasts 60 s). The
  published datasets themselves are labelled correctly (checked from the CPU data).
- FC-ADL's evaluation scripts are hard-coded for Social Network (services, root-cause names
  `<service>`, data path). For hotel datasets the root cause is `<service>-hotelres`; that needs a
  small config change in the FC-ADL repo once data exists.

## What has been tested (on the Mac, 14 Nov 2026)

| Test | Result |
|---|---|
| `helm template` of the hotelReservation chart with both overlays | 19 deployments; requests on the 8 app services; memory limits only with `values-memlimit.yaml`; service commands intact |
| `tests/test_chaos_schema.py` | 32 manifests valid against the Chaos Mesh v1alpha1 CRD schemas in `../chaos-mesh/crds`; every selector matches a pod label in the rendered chart |
| `tests/test_locust.sh` | 3 streams against a stub frontend; rate follows the CSV (5 → 15 → 30 rps); 1636 requests, 0 rejected by the stub's parameter checks |
| `tests/simulate_run.sh` | `run_one.sh` end to end with fake minikube/kubectl/helm, stub frontend and stub Prometheus: fault manifest applied and removed, 2,215 requests served, dataset written, `fault_inject=720` |
| FC-ADL on the simulated dataset | detection change point 359 (true 360); RCA top-1 `search-hotelres` (the injected service) |
| `bash -n` on all scripts | ok |
