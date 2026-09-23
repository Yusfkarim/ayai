"""GET /v1/models — OpenAI-compatible model list. NO Fly."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

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

    def do_GET(self):
        try:
            cat = providers.full_catalog()
        except Exception:
            cat = []
        if not cat:
            cat = [{"id": "pol-openai"}, {"id": "lr-nano"}]
        data = [{"id": it["id"], "object": "model", "owned_by": "vpx",
                 "name": it.get("name") or it["id"]} for it in cat]
        return self._send(200, {"object": "list", "data": data})
