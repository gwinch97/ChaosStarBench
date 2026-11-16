#!/usr/bin/env python3
"""Write one Chaos Mesh manifest per (fault, service) into chaos/<fault>/<service>.yaml.
Parameters follow the Social Network runs used for the paper (inferred from the published data
and the surviving manifests): CPU hog 2 workers at 100% load; memory hog 400MiB (1 worker) under a 512Mi limit;
network delay 50 ms +/- 50 ms jitter; all on one pod for 3600 s. memhog_nn is a 6120MiB memory
hog (12 workers) with no pod memory limit (set at deploy time, see run_one.sh)."""
import os

NS = "hotelreservation"
SERVICES = ["search", "recommendation", "reservation", "user", "geo", "profile", "rate", "frontend"]
DUR = "3600s"


def stress(name, app, stressor):
    return f"""kind: StressChaos
apiVersion: chaos-mesh.org/v1alpha1
metadata:
  namespace: {NS}
  name: {name}
spec:
  selector:
    namespaces:
      - {NS}
    labelSelectors:
      app: {app}
  mode: one
  stressors:
{stressor}  duration: '{DUR}'
"""


def delay(name, app):
    return f"""kind: NetworkChaos
apiVersion: chaos-mesh.org/v1alpha1
metadata:
  namespace: {NS}
  name: {name}
spec:
  action: delay
  mode: one
  selector:
    namespaces:
      - {NS}
    labelSelectors:
      app: {app}
  delay:
    latency: '50ms'
    correlation: '100'
    jitter: '50ms'
  duration: '{DUR}'
"""


CPU = "    cpu:\n      workers: 2\n      load: 100\n"
# Memory sizes are absolute: Chaos Mesh's memStress (latest and v2.7.2) takes '95%' of total *host*
# memory (~59 GB here), so inside a 512Mi pod limit it was OOM-killed every few seconds instead of
# holding memory. Sizes reproduce what the Social Network data shows during its memory faults:
# memhog (512Mi limit): target steady at ~395-435 MiB; no-limit hog: steady ~6.1 GB on an 8 GB node
# (Social Network used several 510MiB workers for that).
MEM = "    memory:\n      workers: 1\n      size: '400MiB'\n"
MEM_NN = "    memory:\n      workers: 12\n      size: '6120MiB'\n"  # size is the total across workers
here = os.path.dirname(os.path.abspath(__file__))
for svc in SERVICES:
    app = f"{svc}-hotelres"
    files = {
        "cpuhog": stress(f"{svc}-cpuhog", app, CPU),
        "memhog": stress(f"{svc}-memhog", app, MEM),
        "memhog_nn": stress(f"{svc}-memhog-nn", app, MEM_NN),
        "networkdelay": delay(f"{svc}-delay", app),
    }
    for fault, text in files.items():
        os.makedirs(os.path.join(here, fault), exist_ok=True)
        open(os.path.join(here, fault, f"{svc}.yaml"), "w").write(text)
print("written", len(SERVICES) * 4, "manifests")
