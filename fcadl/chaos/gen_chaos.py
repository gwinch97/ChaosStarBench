#!/usr/bin/env python3
"""Write one Chaos Mesh manifest per (fault, service) into chaos/<fault>/<service>.yaml.
Parameters follow the Social Network runs used for the paper (inferred from the published data
and the surviving manifests): CPU hog 2 workers at 100% load; memory hog 95% (1 worker) under a 512Mi limit, containers may swap;
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
# memhog: '95%' exactly as in the Social Network fault files. memStress takes 95% of total *host*
# memory (~59 GB), far above the 512Mi pod limit, so the stressor sits at the limit, swaps and is
# re-killed for the whole fault; that costs CPU in the target (Social Network: x2-3). It needs the
# containers to be allowed to swap (allow_swap.sh, called by run_one.sh); without swap it is simply
# OOM-killed and Chaos Mesh gives up after a few minutes.
# memhog_nn (no memory limit): a fixed 6120MiB, the steady ~6.1 GB plateau in the Social Network
# no-limit runs on an 8 GB node; Chaos Mesh 'size' is the total across workers.
MEM = "    memory:\n      workers: 1\n      size: '95%'\n"
MEM_NN = "    memory:\n      workers: 12\n      size: '6120MiB'\n"
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
