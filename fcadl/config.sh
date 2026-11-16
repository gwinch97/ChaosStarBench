# Shared settings for the FC-ADL hotelReservation experiments (sourced by the scripts).
# Every value can be overridden from the environment (the local simulation does this).
NAMESPACE=${NAMESPACE:-hotelreservation}
RELEASE=${RELEASE:-hotelres}
CHART=${CHART:-../hotelReservation/helm-chart/hotelreservation}
# Services that receive faults (Helm pods are labelled app=<service>-hotelres)
FAULT_SERVICES=${FAULT_SERVICES:-"search recommendation reservation user"}
FAULTS=${FAULTS:-"cpuhog memhog memhog_nn networkdelay"}
# Timing, as the Social Network runs (run_chaos_sin.sh): 90 min load, then a 60 min fault;
# the scrape keeps the last 2 h (1 h before the fault, 1 h of fault) at 5 s
PRE_FAULT_S=${PRE_FAULT_S:-5400}
FAULT_S=${FAULT_S:-3600}
SCRAPE_WINDOW_S=${SCRAPE_WINDOW_S:-7200}
STEP_S=${STEP_S:-5}
# Cluster, as `k8startup.sh 2 8000 5 1`: 5 nodes x 2 CPUs x 8 GB
NODE_CPUS=${NODE_CPUS:-2}
NODE_MEM_MB=${NODE_MEM_MB:-8000}
N_NODES=${N_NODES:-5}
# Output
DATA_DIR=${DATA_DIR:-$HOME/projects/hotel-data}
FRONTEND_PORT=${FRONTEND_PORT:-5000}
PROM_PORT=${PROM_PORT:-9090}
# Chaos Mesh image version. The chart's default tag is "latest" (a moving target): the Social
# Network data (June 2025) ran whatever was current then, and in the Nov 2026 build memStress
# sizes "95%" from total host memory, ignoring the container limit. Pin the newest release at
# the time of the Social Network runs (v2.7.2, May 2025; chart is 2.7.1).
CHAOS_MESH_TAG=${CHAOS_MESH_TAG:-v2.7.2}
