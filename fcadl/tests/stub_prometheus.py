"""Stub Prometheus /api/v1/query for range-vector queries of container_cpu_usage_seconds_total and
container_memory_rss. Serves synthetic counters for the 19 hotelReservation pods over the last
WINDOW, sampled about every 5 s with jitter (as the real scrapes), with a CPU-hog fault on the pod of
FAULT_SERVICE starting at the UNIX time in FAULT_TIME_FILE (the run script writes it). Timestamps are
laid out so the fault sits WINDOW/2 into the window, as in a real run.
Usage: stub_prometheus.py PORT FAULT_TIME_FILE FAULT_SERVICE"""
import json, os, re, sys, time
import numpy as np
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PODS = ["consul", "frontend", "geo", "jaeger", "memcached-profile-1", "memcached-rate-1", "memcached-reserve-1",
        "mongodb-geo", "mongodb-profile", "mongodb-rate", "mongodb-recommendation", "mongodb-reservation",
        "mongodb-user", "profile", "rate", "recommendation", "reservation", "search", "user"]
# who calls whom (shared load drives correlated CPU), roughly as in hotelReservation
LOAD = {"frontend": 1.0, "search": 0.8, "geo": 0.6, "rate": 0.6, "profile": 0.7, "recommendation": 0.5,
        "reservation": 0.3, "user": 0.3, "memcached-profile-1": 0.4, "memcached-rate-1": 0.4,
        "memcached-reserve-1": 0.2, "mongodb-geo": 0.1, "mongodb-profile": 0.1, "mongodb-rate": 0.1,
        "mongodb-recommendation": 0.1, "mongodb-reservation": 0.2, "mongodb-user": 0.1}


def series(window, fault_t, fault_svc):
    rng = np.random.default_rng(0)
    t0 = fault_t - window / 2
    n = int(window / 5)
    ts = t0 + np.arange(n) * 5 + rng.normal(0, 0.3, n)
    # time-varying load: sum of sinusoids as the sin workloads, plus per-pod noise
    load = 1 + 0.5 * np.sin(2 * np.pi * np.arange(n) / 700) + 0.3 * np.sin(2 * np.pi * np.arange(n) / 230)
    load = load * (1 + 0.4 * rng.standard_normal(n))   # request-level fluctuations shared along call paths
    out = {}
    for name in PODS:
        pod = f"{name}-hotelres-{abs(hash(name)) % 10**9:x}-{'abcde'}"
        k = LOAD.get(name, 0.02)
        inc = k * 0.05 * load + 0.01 * rng.random(n)
        if name == fault_svc:   # CPU hog: extra independent CPU after the fault, breaking the coupling
            after = ts >= fault_t
            inc[after] = 0.4 + 0.05 * rng.standard_normal(after.sum())
        out[pod] = np.c_[ts, np.cumsum(inc)]
    return out


class H(BaseHTTPRequestHandler):
    def do_GET(self):
        q = parse_qs(urlparse(self.path).query).get("query", [""])[0]
        m = re.search(r'\[(\d+)s\]', q)
        if "/api/v1/query" in self.path and not m:   # instant query (health check): empty vector
            body = json.dumps({"status": "success", "data": {"resultType": "vector", "result": []}}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(body); return
        if not m:
            self.send_response(400); self.end_headers(); return
        window = int(m.group(1))
        fault_t = float(open(FAULT_FILE).read()) if os.path.exists(FAULT_FILE) else time.time() - window / 2
        res = []
        for pod, v in series(window, fault_t, FAULT_SVC).items():
            metric = {"__name__": q.split("{")[0], "namespace": "hotelreservation", "pod": pod,
                      "id": f"/kubepods.slice/{pod}", "container": ""}
            vals = v if "cpu" in q else np.c_[v[:, 0], 1e8 + 1e6 * v[:, 1]]
            res.append({"metric": metric, "values": [[float(t), f"{x:.6f}"] for t, x in vals]})
        body = json.dumps({"status": "success", "data": {"resultType": "matrix", "result": res}}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass


FAULT_FILE, FAULT_SVC = sys.argv[2], sys.argv[3]
ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
