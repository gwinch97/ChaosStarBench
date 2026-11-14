#!/usr/bin/env python3
"""Write one Chaos Mesh manifest per (fault, service) into chaos/<fault>/<service>.yaml.
Parameters follow the Social Network runs used for the paper (inferred from the published data
and the surviving manifests): CPU hog 2 workers at 100% load; memory hog 1 worker at 95%;
network delay 50 ms +/- 50 ms jitter; all on one pod for 3600 s. memhog_nn is the same memory
hog with the pod's memory limit removed (set at deploy time, see run_one.sh)."""
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
MEM = "    memory:\n      workers: 1\n      size: '95%'\n"
here = os.path.dirname(os.path.abspath(__file__))
for svc in SERVICES:
    app = f"{svc}-hotelres"
    files = {
        "cpuhog": stress(f"{svc}-cpuhog", app, CPU),
        "memhog": stress(f"{svc}-memhog", app, MEM),
        "memhog_nn": stress(f"{svc}-memhog-nn", app, MEM),
        "networkdelay": delay(f"{svc}-delay", app),
    }
    for fault, text in files.items():
        os.makedirs(os.path.join(here, fault), exist_ok=True)
        open(os.path.join(here, fault, f"{svc}.yaml"), "w").write(text)
print("written", len(SERVICES) * 4, "manifests")
