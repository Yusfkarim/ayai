"""GET /api/cron — pool top-up + proxy harvest + catalog sync + probes. NO Fly."""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import providers


class handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        want = providers.CRON_SECRET
        if not want:
            return True
        got = (self.headers.get("Authorization") or "").strip()
        if got == "Bearer " + want:
            return True
        try:
            q = parse_qs(urlparse(self.path).query)
            return (q.get("secret") or [""])[0] == want
        except Exception:
            return False

    def do_GET(self):
        if not self._auth():
            return self._send(401, {"error": "bad cron secret"})
        t0 = time.time()
        budget = 270  # stay under 300s Hobby wall
        out = {}
        try:
            out["harvest"] = providers.harvest_proxies(max_keep=60, deadline=120)
        except Exception as e:
            out["harvest"] = {"err": str(e)[:80]}
        for name in ("ca", "cb", "nv"):
            if time.time() - t0 > budget - 60:
                break
            try:
                out["mint_" + name] = providers.mint_fb_pool(name, count=6)
            except Exception as e:
                out["mint_" + name] = {"err": str(e)[:80]}
        if time.time() - t0 < budget - 60:
            try:
                out["mint_ach"] = providers.mint_ach(count=2)
            except Exception as e:
                out["mint_ach"] = {"err": str(e)[:80]}
        try:
            n = len(providers.full_catalog())
            out["catalog"] = {"models": n}
        except Exception as e:
            out["catalog"] = {"err": str(e)[:80]}
        probes = {}
        for p in ("pol", "lr", "aff", "gz", "ach"):
            if time.time() - t0 > budget - 10:
                break
            try:
                ok, info = providers.probe(p)
                probes[p] = {"ok": ok, "info": info}
            except Exception as e:
                probes[p] = {"ok": False, "info": str(e)[:60]}
        out["probes"] = probes
        try:
            import kv
            kv.kv_jset("vpx:health", {"t": time.time(), "probes": probes})
        except Exception:
            pass
        out["pools"] = providers.pool_stats()
        out["seconds"] = round(time.time() - t0, 1)
        return self._send(200, {"ok": True, **out})
