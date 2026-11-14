"""Stub of the hotelReservation frontend: accepts the four endpoints the workload uses, checks
their parameters like frontend/server.go does (required keys, date and float formats) and logs
each request as JSON lines. Usage: stub_hotel.py PORT LOGFILE"""
import json, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from datetime import date

REQ = {"/hotels": ("GET", ["inDate", "outDate", "lat", "lon"]),
       "/recommendations": ("GET", ["require", "lat", "lon"]),
       "/user": ("POST", ["username", "password"]),
       "/reservation": ("POST", ["inDate", "outDate", "hotelId", "customerName", "username", "password", "number"])}
lock = threading.Lock()
log = open(sys.argv[2], "w")


class H(BaseHTTPRequestHandler):
    def handle_req(self, method):
        u = urlparse(self.path); q = {k: v[0] for k, v in parse_qs(u.query).items()}
        ok, why = True, ""
        if u.path not in REQ or REQ[u.path][0] != method:
            ok, why = False, "unknown endpoint"
        else:
            miss = [k for k in REQ[u.path][1] if k not in q]
            if miss: ok, why = False, f"missing {miss}"
            try:
                for k in ("inDate", "outDate"):
                    if k in q: date.fromisoformat(q[k])
                for k in ("lat", "lon"):
                    if k in q: float(q[k])
                if "inDate" in q and q["outDate"] <= q["inDate"]: ok, why = False, "outDate <= inDate"
                if u.path == "/recommendations" and q.get("require") not in ("dis", "rate", "price"): ok, why = False, "bad require"
            except ValueError as e:
                ok, why = False, str(e)
        with lock:
            log.write(json.dumps({"t": time.time(), "path": u.path, "ok": ok, "why": why}) + "\n"); log.flush()
        self.send_response(200 if ok else 400); self.end_headers(); self.wfile.write(b"{}")

    def do_GET(self): self.handle_req("GET")
    def do_POST(self): self.handle_req("POST")
    def log_message(self, *a): pass


ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
