"""POST /v1/chat/completions — OpenAI-compatible chat. NO Fly."""
import json
import os
import random
import sys
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import providers


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _auth(self):
        want = providers.API_KEY
        if not want:
            return True
        got = (self.headers.get("Authorization") or "").strip()
        return got == "Bearer " + want

    def do_POST(self):
        if not self._auth():
            return self._send(401, {"error": {"message": "invalid API key", "type": "auth"}})
        try:
            ln = int(self.headers.get("Content-Length") or 0)
        except Exception:
            ln = 0
        try:
            data = json.loads(self.rfile.read(ln) or b"{}")
        except Exception:
            return self._send(400, {"error": {"message": "bad json", "type": "invalid_request"}})
        if data.get("stream"):
            return self._send(400, {"error": {"message": "streaming not supported in v1 (use stream:false)",
                                              "type": "invalid_request"}})
        model = data.get("model") or "pol-openai"
        messages = data.get("messages") or []
        if not messages:
            return self._send(400, {"error": {"message": "messages required", "type": "invalid_request"}})
        t0 = time.time()
        try:
            text, used = providers.chat(model, messages, timeout=240)
        except Exception as e:
            return self._send(502, {"error": {"message": str(e)[:200], "type": "all_failed"}})
        dt = time.time() - t0
        return self._send(200, {
            "id": "chatcmpl-vpx%d%d" % (int(t0), random.randint(100, 999)),
            "object": "chat.completion", "created": int(t0), "model": used,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                      "seconds": round(dt, 1)}})

    def do_GET(self):
        return self._send(200, {"ok": True, "service": "vpx-chat",
                                "usage": "POST /v1/chat/completions {model, messages}"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()
