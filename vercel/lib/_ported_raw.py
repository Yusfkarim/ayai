"""Ported providers (mechanical copy from main.py @96cf9cc) — shims in shim.py"""
import base64, hashlib, json, os, random, re, threading, time, uuid
import requests

def _sys_keep(msgs, n=19):
    """#94U25: کورتکردنەوەی مێژوو بەبێ فەوتاندنی system — هەموو system ەکان + دوایین N"""
    try:
        msgs = list(msgs or [])
    except Exception:
        return []
    sys_m = [m for m in msgs if isinstance(m, dict) and m.get("role") == "system"]
    rest = [m for m in msgs if not (isinstance(m, dict) and m.get("role") == "system")]
    if len(rest) > n:
        rest = rest[-n:]
    return sys_m + rest

def _sys_txt(msgs, cap=32000):
    """#94U25+#94U26+#94U28: دەقی system ەکان — تا 32k (هەڵەی باسکەند → fallback؛ بڕینی بێدەنگ قەدەغە)"""
    try:
        return " ".join(str(m.get("content") or "") for m in (msgs or []) if isinstance(m, dict) and m.get("role") == "system")[:cap]
    except Exception:
        return ""

def pol_chat(model, history, timeout=110):
    """پرسیار بۆ pollinations — وەڵامی تەواو دەگەڕێنێتەوە (لەگەڵ دووبارەهەوڵ بۆ 429)"""
    msgs = _sys_keep(history, 19)  # #94U25
    last = "وەڵامێک نەگەڕایەوە"
    for attempt in range(3):
        try:
            r = requests.post(POL_URL, json={
                "model": model,
                "messages": msgs,
                "seed": random.randint(1, 999999),
            }, timeout=(15, timeout), headers={
                "Content-Type": "application/json",
                "User-Agent": UA,
            })
            if r.status_code == 429:
                last = "طلبات كثيرة بسرعة — انتظر قليلا وحاول مجددا."
                time.sleep(6 + 4 * attempt)
                continue
            if not r.ok:
                last = f"خطأ في الخادم البديل ({r.status_code})"
                time.sleep(2)
                continue
            ans = (r.text or "").strip()
            if ans:
                return ans
            time.sleep(2)
        except Exception as e:
            last = str(e)
            time.sleep(2)
    raise RuntimeError(last)

class EMError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code



def gz_chat(messages, model_id, timeout=90, cheap=False):  # #95U1؛ #95U3: cheap=probe هەرزان
    """چاتی GizAI — session ی نەناسراو ← infer → {"status":"completed","output":…}؛ #94U50: 429/401 → سێشن+پرۆکسی نوێ"""
    import time as _t
    if _t.time() < _GZ_BADC.get(model_id, 0):
        raise EMError("gz: cooldown")
    try:
        _gz_mem_load()
    except Exception:
        pass
    _ck95 = None
    try:  # #95U3: کاشی پرۆمپتی کورت (کۆنتێکست-تەواو، نەک تەنها دوا-نامە)
        _lu95 = next((m.get("content") or "" for m in reversed(messages) if m.get("role") != "system" and m.get("content")), "")
        if _lu95 and len(_lu95) <= 40 and _lu95 != "تەنها بە یەک وشە وەڵام بدەوە: باشم":
            import hashlib as _h95
            _ctx95 = _h95.md5(repr([(m.get("role"), (m.get("content") or "")[:200]) for m in messages]).encode()).hexdigest()[:12]
            _ck95 = (model_id, _ctx95)
            _hit95 = _GZ_CACHE.get(_ck95)
            if _hit95 and _t.time() - _hit95[1] < 300 and not cheap:
                return _hit95[0]
    except Exception:
        pass
    hist = _sys_keep([{"type": (m.get("role") or "user"), "content": m.get("content") or ""}
                        for m in messages if m.get("content")], 11)
    if not hist:
        raise EMError("gz: هیچ نامە")
    _last = EMError("gz: شکست")
    _allpx = _gz_qualify(_GZ_SEEDS + _px_list(10)[1:])  # #95U3: 8→10  # #94U60+61: seeds + حەوز → تەنها cookie-forward
    try:
        random.shuffle(_allpx)  # #94U54: هەر خولێک IP ی جیاواز
    except Exception:
        pass
    _now60 = _t.time()
    _use = [_p for _p in _allpx if _now60 > _GZ_WALL.get(_p, 0) and _now60 > _GZ_BURNED.get((_p, model_id), 0)]
    try:  # #94U60: GOOD-first (<6 کاتژمێر)
        _use.sort(key=lambda _p: 0 if _now60 - _GZ_GOOD.get(_p, 0) < 21600 else 1)
    except Exception:
        pass
    if cheap:  # #95U3: probe هەرزان — دایرێکت + باشترین 1
        _loop = [None] + (_use[:1] if _use else _allpx[:1])
    else:
        _loop = [None] + (_use if len(_use) >= 2 else _allpx[:2])  # دایرێکت یەکەم + proxy ـەکان
    _dead95 = _t.time() + min(timeout, 90)  # #95U1
    for _px in _loop:
        _rem95 = _dead95 - _t.time()  # #95U1
        if _rem95 <= 6:
            _last = EMError("gz: deadline")
            break
        try:
            s = requests.Session()
            s.headers.update({"User-Agent": GZ_UA, "Content-Type": "application/json",
                              "Origin": GZ_BASE, "Referer": GZ_BASE + "/assistant?mode=chat&baseModel=dynamic"})
            if _px:
                s.proxies.update({"http": _px, "https": _px})
            s.cookies.set("pfb9", GZ_PFB9, domain="www.giz.ai")
            r0 = s.post(GZ_BASE + "/api/data/spaces/spaceServer.createAnonymousSession",
                        json={"visitorId": _gz_rid(32), "session": {"mode": "chat", "shared": False,
                              "modeInput": {"baseModel": "dynamic", "settings": {"character": "AI", "responseMode": "text"},
                              "reasoning": {"level": "low", "mode": "default"}, "context": "general",
                              "reference": "auto", "showChoices": False}}}, timeout=(10, min(25, max(8, int(_rem95)))))  # #95U1
            sid = (r0.json() or {}).get("sessionId") if r0.status_code in (200, 201) else None
            if not sid:
                _sm = ""
                try:
                    _sm = " " + str((r0.json() or {}).get("message") or "")[:50]
                except Exception:
                    pass
                _last = EMError(f"gz: session {r0.status_code}{_sm}")
                continue
            inst = _gz_rid(21)
            inf = {"model": model_id,
                   "input": {"messages": hist, "sessionId": sid, "mode": "chat",
                             "settings": {"character": "AI", "responseMode": "text"}, "context": "general"},
                   "subscribeId": _gz_rid(22), "instanceId": inst}
            r = s.post(GZ_BASE + "/api/data/users/inferenceServer.infer", json=inf,
                       headers={"x-giz-instance-id": inst}, timeout=(15, min(45, max(10, int(_rem95)))))  # #95U1
        except Exception as e:
            if _px:  # #94U53: پرۆکسی مردوو → خراپ (strikes)
                try:
                    _proxy_mark_bad(_px)
                except Exception:
                    pass
            _last = EMError(f"gz: {str(e)[:60]}")
            continue
        if r.status_code in (429, 401, 403):
            _msg = ""
            try:
                _msg = (r.json() or {}).get("message") or ""
            except Exception:
                pass
            if "pay-as-you-go" in _msg:  # #94U51: مۆدێل پارەدارە — لە کاتالۆگ لابەرە
                try:
                    if _GZ_SYNC.get("catalog", {}).pop(model_id, None) is not None:
                        print(f"[GZ] پارەدار لابرا: {model_id}", flush=True)
                except Exception:
                    pass
                raise EMError(f"gz: {model_id} paywalled")
            if _px:  # #94U60: بیرگەوری — 429=(px,model)/کاتژمێر، 401/403=px/30خولەک
                try:
                    if r.status_code == 429:
                        _GZ_BURNED[(_px, model_id)] = _t.time() + 3700.0
                    else:
                        _GZ_WALL[_px] = _t.time() + 1800.0
                except Exception:
                    pass
            _last = EMError(f"gz: {r.status_code} {_msg[:40]}")
            continue
        if r.status_code != 201 and r.status_code != 200:
            _m2 = ""
            try:
                _m2 = " " + str((r.json() or {}).get("message") or "")[:50]
            except Exception:
                pass
            _last = EMError(f"gz: {r.status_code}{_m2}")  # #94U56؛ #94U57: 400 → IP ی دواتر (loop بەردەوام)
            if r.status_code == 400 and "identity" in _m2.lower():  # #95U5: gated-model (direct) / strip-proxy
                if not _px:
                    try:
                        if _GZ_SYNC.get("catalog", {}).pop(model_id, None) is not None:
                            print(f"[GZ] 🚫 gated لابرا: {model_id} (direct-400 identity)", flush=True)
                    except Exception:
                        pass
                else:
                    try:
                        _GZ_WALL[_px] = _t.time() + 1800.0
                    except Exception:
                        pass
            continue
        try:
            j = r.json()
        except Exception:
            _last = EMError("gz: parse")
            continue
        if (j.get("status") or "completed") != "completed":
            _last = EMError(f"gz: status={j.get('status')}")
            continue
        ans = (j.get("output") or "").strip()
        if not ans:
            _last = EMError("gz: وەڵام بەتاڵ")
            continue
        if _px:  # #94U60: GOOD
            try:
                _GZ_GOOD[_px] = _t.time()
            except Exception:
                pass
        if _ck95:
            try:  # #95U3: کاش + بیرگەوری
                _GZ_CACHE[_ck95] = (ans, _t.time())
                if len(_GZ_CACHE) > 500:
                    _cut95 = _t.time() - 300
                    for _k95 in [_k for _k, _v in _GZ_CACHE.items() if _v[1] < _cut95][:200]:
                        _GZ_CACHE.pop(_k95, None)
            except Exception:
                pass
        try:
            _gz_mem_save()
        except Exception:
            pass
        return ans
    if "429" in str(_last):
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["quota"]
        raise EMError("gz: کوانتای مۆدێڵ (~١ کاتژمێر)")
    if "401" in str(_last) or "403" in str(_last):
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["login"]
        raise EMError("gz: لۆگین-واڵ")
    try:
        _gz_mem_save()
    except Exception:
        pass
    print(f"[GZ] هەموو IP ـەکان شکستیان هێنا ({len(_loop)} هەوڵ): {_last}", flush=True)
    raise _last

def _px_list(n=3):
    """#94U49: [None, px1, ...] — یەکەم ڕاستەوخۆ، دواتر پرۆکسی تازە بۆ هەر لیمێتی IP"""
    try:
        pxs = [p for p in (_proxy_get(n) or []) if p][:n]
        return [None] + pxs
    except Exception:
        return [None]

class AIFreeError(Exception):
    pass

class AIFreeChat:
    def __init__(self, model, endpoint=None, timeout=120):
        self.model = model
        self.endpoint = endpoint if (endpoint or "").startswith("http") else BASE_URL + (endpoint or "")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": BASE_URL + "/chat/" + model,
        })
        self._nonce = ""

    def _fetch_nonce(self):
        n = ""
        try:
            n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
        except Exception:
            n = ""
        if not n:
            # ماڵپەرەکە نۆنس بەتاڵ دەدات مەگەر سەرەتا سەردانی پەڕەی چات بکرێت (کوکی سێشن)
            try:
                self.session.headers.pop("Content-Type", None)
                self.session.get(BASE_URL + "/chat/" + self.model, timeout=20)
                self.session.headers["Content-Type"] = "application/json"
                n = self.session.get(BASE_URL + "/api/chat-nonce", timeout=15).json().get("nonce", "")
            except Exception:
                n = ""
        return n

    @staticmethod
    def _proof():
        now = int(time.time() * 1000)
        start = now - random.randint(4000, 15000)
        return {"nonce": "", "keystrokeCount": random.randint(20, 120),
                "pasteEvents": 0, "totalTypingTime": now - start,
                "startTime": start, "submitTime": now}

    def chat(self, question, history=None):
        _sys = _sys_txt(history)  # #94U25b: system بخە ناو پرسیار (باسکەندەکە history ڕۆڵەکان پشتگوێ دەخات)
        _q = f"[Instructions: {_sys}]\n\n{question}" if _sys else question
        payload = {
            "model": self.model, "question": _q, "tone": "friendly",
            "format": "paragraph", "file": None,
            "conversationHistory": _sys_keep(history or [], 19),  # #94U25
            "interactionProof": self._proof(),
            "aiRole": "assistant", "aiName": "", "language": "auto",
        }
        last = None
        for attempt in range(3):
            try:
                if not self._nonce:
                    self._nonce = self._fetch_nonce()
                payload["interactionProof"]["nonce"] = self._nonce
                with self.session.post(self.endpoint, json=payload, stream=True,
                                       timeout=(15, self.timeout)) as r:
                    if r.status_code == 429:
                        raise AIFreeError("طلبات كثيرة بسرعة (429) — انتظر قليلا.")
                    if r.status_code in (403, 407, 502, 503):
                        raise ConnectionError(f"داخستن ({r.status_code})")
                    if r.status_code == 409:
                        raise AIFreeError("سێرڤەرەکە ئێستا بەردەست نییە (409).")
                    r.raise_for_status()
                    ctype = r.headers.get("content-type", "")
                    answer = ""
                    if "text/event-stream" in ctype:
                        for raw in r.iter_lines():
                            line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
                            if not line.startswith("data: "):
                                continue
                            d = line[6:].strip()
                            if d == "[DONE]":
                                break
                            try:
                                answer += json.loads(d).get("token", "")
                            except Exception:
                                pass
                    else:
                        answer = (r.json() or {}).get("answer", "")
                    if not answer:
                        raise ConnectionError("aff: وەڵامی بەتاڵ — نۆنسی نوێ پێویستە")
                    return answer
            except AIFreeError:
                raise
            except Exception as e:
                last = e
                self._nonce = ""
                time.sleep(1.2 * (attempt + 1))
        raise ConnectionError(str(last))

def _lr_anon_session():
    """سێشنی نەناسراوی نوێ — هەر سێشن = ١ نامە (بۆیە بۆ هەر داواکارییەک یەک دروست دەکەین)"""
    s = requests.Session()
    s.headers.update({"User-Agent": LR_UA, "Accept-Language": "en"})
    r = s.post(LR_B + "/api/auth/sign-in/anonymous", json={"newUser": True},
               headers={"Origin": LR_B, "Referer": LR_B + "/chat",
                        "Content-Type": "application/json"}, timeout=(10, 20))
    if r.status_code != 200:
        raise EMError(f"lr: signin {r.status_code}")
    return s

def _lr_um(role, text):
    return {"id": str(uuid.uuid4()), "role": role,
            "parts": [{"type": "text", "text": str(text)[:6000]}]}

def lr_chat(messages, model_id=None, timeout=75):
    """#96U3: چاتی lorka — سێشنی نەناسراو + مێژووی تەواو لە یەک داواکاریدا — SSE text-delta"""
    with _LR_SEM:
        sess = _lr_anon_session()
        sys_txt = " ".join(str(m.get("content")) for m in messages if m.get("role") == "system")[:8000]
        rest = [m for m in messages if m.get("role") != "system"][-12:]
        ums = []
        for i, m in enumerate(rest):
            role = "assistant" if m.get("role") == "assistant" else "user"
            txt = str(m.get("content"))
            if i == 0 and sys_txt and role == "user":
                txt = f"[ئاراستەی سیستەم: {sys_txt}]\n{txt}"
            ums.append(_lr_um(role, txt))
        if not ums:
            ums = [_lr_um("user", "سلام")]
        if ums[0]["role"] != "user":
            ums.insert(0, _lr_um("user", sys_txt or "بەردەوامبە"))
        body = {"id": str(uuid.uuid4()), "type": "chat",
                "visitorId": uuid.uuid4().hex, "messages": ums}
        r = sess.post(LR_B + "/api/v2/chat/anonymous", json=body, timeout=(10, timeout),
                      stream=True, headers={"Origin": LR_B, "Referer": LR_B + "/chat",
                                            "Content-Type": "application/json"})
        if r.status_code == 429:
            raise EMError("lr: لیمیت (429)")
        if r.status_code != 200:
            raise EMError(f"lr: HTTP {r.status_code}")
        parts = []
        for raw in r.iter_lines(chunk_size=None):
            ln = raw.decode("utf-8", "ignore").strip()
            if not ln.startswith("data:"):
                continue
            payload = ln[5:].strip()
            if payload == "[DONE]":
                break
            try:
                d = json.loads(payload)
            except Exception:
                continue
            if d.get("type") == "text-delta":
                parts.append(str(d.get("delta") or ""))
            elif d.get("type") == "error":
                raise EMError(f"lr: {str(d.get('errorText') or d.get('message') or 'error')[:80]}")
        out = "".join(parts).strip()
        if not out:
            raise EMError("lr: وەڵامی بەتاڵ")
        return out

def ach_chat(messages, model_key="consensus", timeout=110, depth=0):
    """چاتی AllChat — ڕۆتەیشنی ئەکاونت + دروستکردنی خۆکار لەسەر limitReached"""
    if depth == 0 and not (ACH_ST.get("accounts")):
        _ach_load()
    sys_txt = " ".join(str(m.get("content")) for m in messages if m.get("role") == "system")[:600]
    rest = [m for m in messages if m.get("role") != "system"]
    last = rest[-1] if rest else {"role": "user", "content": "سلام"}
    hist = [{"role": ("user" if m.get("role") == "user" else "assistant"),
             "content": str(m.get("content"))[:1200]} for m in rest[:-1]][-6:]
    umsg = str(last.get("content"))[:6000]
    if sys_txt:
        umsg = f"[رێنمایی کەسایەتی: {sys_txt}]\n\n{umsg}"
    # #97f: SmartRoute → ناچارکردنی COMPLEX بە پێچانەوەی کاتێگۆری — مۆدێلی پریمیۆمی تایبەت
    if model_key in ACH_SMART:
        umsg += ACH_WRAPS.get(model_key, ACH_WRAPS["consensus"])
        timeout = max(int(timeout or 0), 170)
    for _ in range(2):
        acc = _ach_pick()
        if not acc:
            raise EMError("ach: ئەکاونت نەدروست بوو")
        try:
            ans, cm = _ach_call(acc, model_key, umsg, hist, timeout)
            acc["n"] = int(acc.get("n") or 0) + 1
            if int(acc.get("n") or 0) >= ACH_BUDGET:
                acc["dead"] = 1
            with ACH_LOCK:
                _ach_save()
            if cm and cm.get("models"):
                print(f"[ACH] کۆنسێنسۆس: {' + '.join(cm['models'])} | multi={cm.get('multi')} | conf={cm.get('confidence')}", flush=True)
            # #97g: سەرچاوەکانی وێب → بەستەرەوە بە وەڵام
            if model_key == "web" and cm.get("sources"):
                _ln = "\n".join(f"🔗 {(t or 'سەرچاوە')[:48]}: {u}" for t, u in cm["sources"] if u)
                if _ln:
                    ans = ans.rstrip() + "\n\n" + _ln
            return ans
        except _AchLimit as e:
            s = str(e)
            acc["dead"] = 1
            with ACH_LOCK:
                _ach_save()
            if depth == 0:
                na = _ach_new_account()
                if na:
                    return ach_chat(messages, model_key, timeout, depth=1)
            raise EMError(f"ach: {s[:80]}")
        except EMError:
            raise
        except Exception as e:
            if depth == 0:
                acc["dead"] = 1
                with ACH_LOCK:
                    _ach_save()
                na = _ach_new_account()
                if na:
                    return ach_chat(messages, model_key, timeout, depth=1)
            raise EMError(f"ach: {str(e)[:80]}")
    raise EMError("ach: دووبارە بوونەوە سەرکەوتوو نەبوو")





def _gz_mem_load():
    """#95U3: GOOD/BURNED/WALL لە دیسک (deploy بیرگەوری ناسڕێتەوە)"""
    if _GZ_MEM_LD[0]:
        return
    _GZ_MEM_LD[0] = True
    _GZ_MEM_SV[0] = time.time()
    try:
        d = _json_load_safe(os.path.join(DATA_DIR, "gz_mem.json")) or {}
        for _k, _v in (d.get("good") or {}).items():
            _GZ_GOOD[_k] = float(_v)
        for _k, _v in (d.get("wall") or {}).items():
            _GZ_WALL[_k] = float(_v)
        for _k, _v in (d.get("burned") or {}).items():
            _p = _k.split("\x00")
            if len(_p) == 2:
                _GZ_BURNED[(_p[0], _p[1])] = float(_v)
        print(f"[GZ] 🧠 بیرگەوری بارکرا (GOOD {len(_GZ_GOOD)} WALL {len(_GZ_WALL)} BURN {len(_GZ_BURNED)})", flush=True)
    except Exception:
        pass

def _gz_mem_save():
    """#95U3: پاشەکەوت (throttle 60s)"""
    try:
        _now = time.time()
        if _now - _GZ_MEM_SV[0] < 60:
            return
        _GZ_MEM_SV[0] = _now
        _json_save(os.path.join(DATA_DIR, "gz_mem.json"),
                   {"good": dict(_GZ_GOOD), "wall": dict(_GZ_WALL),
                    "burned": {f"{_k[0]}\x00{_k[1]}": _v for _k, _v in _GZ_BURNED.items()}})
    except Exception:
        pass

def _gz_rid(n):
    import secrets as _sc, string as _st
    return "".join(_sc.choice(_st.ascii_letters + _st.digits + "-_") for _ in range(n))

def _gz_qualify(pxs):
    """#94U61: تەنها proxy ـی cookie-forward (httpbin echo) — stripکەرەکان = 400-identity (fail-open)"""
    import concurrent.futures as _cfq
    _now = time.time()
    _fresh = [p for p in pxs if _now - _GZ_PXOK.get(p, 0) < 3600]
    _todo = [p for p in pxs if p not in _fresh]
    if _todo:
        try:  # httpbin خۆی زیندووە؟ (دایرێکت)
            _r0 = requests.get("https://httpbin.org/headers", headers={"User-Agent": GZ_UA}, timeout=(5, 8))
            if _r0.status_code != 200:
                return pxs
        except Exception:
            return pxs
        _tok = _gz_rid(10)
        def _one(px):
            try:
                _r = requests.get("https://httpbin.org/headers", headers={"User-Agent": GZ_UA, "Cookie": f"gzx={_tok}"},
                                  proxies={"http": px, "https": px}, timeout=(5, 8))
                if _r.status_code == 200 and _tok in _r.text:
                    _GZ_PXOK[px] = time.time()
                    return px
            except Exception:
                pass
            return None
        try:
            _exq = _cfq.ThreadPoolExecutor(max_workers=min(len(_todo), 8))
            try:
                _futs = [_exq.submit(_one, p) for p in _todo]
                for _f in _cfq.as_completed(_futs, timeout=30):
                    try:
                        if _f.result():
                            _fresh.append(_f.result())
                    except Exception:
                        pass
            finally:
                _exq.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
    return _fresh if _fresh else pxs

def _ach_load():
    d = _json_load_safe(ACH_ACC_FILE) or {}
    ACH_ST["accounts"] = d.get("accounts") or []
    ACH_ST["idx"] = int(d.get("idx") or 0)
    ACH_ST["signups"] = d.get("signups") or {"date": "", "n": 0}

def _ach_save():
    _json_save(ACH_ACC_FILE, {"accounts": ACH_ST.get("accounts") or [],
                               "idx": ACH_ST.get("idx") or 0,
                               "signups": ACH_ST.get("signups") or {"date": "", "n": 0}})

def _ach_new_account():
    """ئەکاونتی تەواوی AllChat: mail.tm → signUp → verify(oobCode) → signIn — ~٢٥ چرکە"""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with ACH_LOCK:
        sg = ACH_ST.get("signups") or {"date": "", "n": 0}
        if sg.get("date") == today and int(sg.get("n") or 0) >= ACH_DAY_CAP:
            return None
    try:
        sess = requests.Session()
        em, pw, mtok = _ach_mail_new(sess)
        r = sess.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={ACH_FB_KEY}",
                      json={"email": em, "password": pw, "returnSecureToken": True}, timeout=(12, 30))
        d = r.json() or {}
        idtok, uid = d.get("idToken"), d.get("localId")
        if not idtok:
            print(f"[ACH] signUp fail: {r.status_code} {str(d)[:90]}", flush=True)
            return None
        # پشتڕاستکردنەوەی ئیمەیڵ — ناچاری (چات 403 email_unverified)
        try:
            sess.post(f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={ACH_FB_KEY}",
                      json={"requestType": "VERIFY_EMAIL", "idToken": idtok}, timeout=(12, 30))
            if mtok:
                code = _ach_wait_oob(sess, mtok)
                if code:
                    sess.post(f"https://identitytoolkit.googleapis.com/v1/accounts:update?key={ACH_FB_KEY}",
                              json={"oobCode": code}, timeout=(12, 30))
        except Exception:
            pass
        tok, _ = _ach_fb_login(sess, em, pw)
        acc = {"email": em, "pw": pw, "uid": uid, "tok": tok or idtok,
               "ts": time.time(), "day": today, "n": 0, "dead": 0}
        with ACH_LOCK:
            ACH_ST.setdefault("accounts", []).append(acc)
            _aa = ACH_ST.get("accounts") or []
            if len(_aa) > 320:
                _lv = [a for a in _aa if not a.get("dead")][-260:]
                _dd = [a for a in _aa if a.get("dead")][-60:]
                ACH_ST["accounts"] = _lv + _dd
            sg = ACH_ST.get("signups") or {"date": "", "n": 0}
            if sg.get("date") != today:
                sg = {"date": today, "n": 0}
            sg["n"] = int(sg.get("n") or 0) + 1
            ACH_ST["signups"] = sg
            _ach_save()
        print(f"[ACH] ئەکاونتی نوێ: {em[:18]}… (حەوز: {len(_ach_alive())})", flush=True)
        return acc
    except Exception as e:
        print(f"[ACH] new-acct: {str(e)[:80]}", flush=True)
        return None

def _ach_pick():
    accs = _ach_alive()
    if not accs:
        return _ach_new_account()
    a = accs[ACH_ST.get("idx", 0) % len(accs)]
    ACH_ST["idx"] = (ACH_ST.get("idx", 0) + 1) % len(accs)
    return a

class _AchLimit(Exception):
    pass

def _ach_call(acc, model_key, user_msg, history, timeout):
    """یەک داواکاری — دەگەڕێنێتەوە (وەڵام، consensus_meta) — limitReached → _AchLimit"""
    tok = _ach_tok(acc)
    if not tok:
        raise _AchLimit("no-token")
    hdrs = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json", **ACH_ORIG}
    body = {"userId": acc.get("uid"), "conversationId": "new",
            "userMessage": user_msg, "userMessageId": "u-" + uuid.uuid4().hex[:12],
            "assistantMessageId": "a-" + uuid.uuid4().hex[:12],
            "conversationHistory": history, "memoryLimit": 20 if model_key in ACH_SMART else 10}
    if model_key in ACH_SMART:
        ep = "allChatSmartRoute"
        body["mode"] = "smart"
        if model_key == "web":
            body["forceWebSearch"] = True  # #97g: NEWS_RESEARCH → perplexity/sonar + sources
    else:
        ep = "streamGeneralChat"
        body["model"] = ACH_REAL.get(model_key, "google/gemini-2.5-flash-lite")
    r = requests.post(f"{ACH_API}/{ep}", json=body, headers=hdrs, timeout=(12, timeout), stream=True)
    if r.status_code == 429:
        time.sleep(2)
        r = requests.post(f"{ACH_API}/{ep}", json=body, headers=hdrs, timeout=(12, timeout), stream=True)
    if r.status_code in (401, 403):
        raise _AchLimit(f"auth{r.status_code}")
    if r.status_code == 402:
        raise _AchLimit("tier402")
    parts, cmeta = [], None
    r.raw.decode_content = True
    for raw in r.iter_lines(chunk_size=None):
        if not raw:
            continue
        ln = raw.decode("utf-8", "ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
        if not ln.startswith("data:"):
            continue
        p = ln[5:].strip()
        if p == "[DONE]":
            break
        try:
            d = json.loads(p)
        except Exception:
            continue
        t = d.get("type") if isinstance(d, dict) else None
        if t == "content":
            parts.append(str(d.get("content") or ""))
        elif t == "limitReached":
            raise _AchLimit(str(d.get("reason") or "limit"))
        elif t == "error":
            raise _AchLimit(str(d.get("error") or d.get("message") or "err")[:90])
        elif t == "done":
            cm = d.get("consensus_meta") or {}
            md = d.get("metadata") or {}
            srcs = d.get("sources") or []
            if cm or md or srcs:
                cmeta = {"confidence": cm.get("confidence"), "points": (cm.get("consensus_points") or [])[:4],
                         "models": [x for x in (md.get("primaryModel"), md.get("secondaryModel")) if x],
                         "multi": bool(md.get("isMultiModelResponse")),
                         "sources": [(str(s.get("title") or ""), str(s.get("url") or "")) for s in srcs[:4] if s.get("url")]}
            break
    ans = "".join(parts).strip()
    if not ans:
        raise _AchLimit("empty")
    return ans, cmeta

def _json_save(path, obj):
    """#91A1 + #94U3 + #94U19b: نووسینی ATOMIC + شێفرەکردن + دژە-ڕەیس (per-path lock + tmp ی ناوازە)"""
    with _JSON_LOCKS_G:
        _lk = _JSON_LOCKS.setdefault(path, threading.Lock())
    with _lk:
        return _json_save_locked(path, obj)

def _json_load_safe(path, default=None):
    """#91A1 + #94U3: خوێندنەوەی بەهێز — کاڵفامکردنەوەی خۆکار ئەگەر شێفرەکرابێت + .bak"""
    fer = _get_fernet()
    for p in (path, path + ".bak"):
        if not os.path.exists(p):
            continue
        try:
            with open(p, "rb") as f:
                content = f.read()
            if content.startswith(_ENC_MAGIC):
                if fer:
                    dec = fer.decrypt(content[len(_ENC_MAGIC):])
                    return json.loads(dec.decode("utf-8"))
                else:
                    continue
            else:
                return json.loads(content.decode("utf-8"))
        except Exception:
            continue
    return default

def _ach_mail_new(sess):
    """ئیمەیڵی کاتی mail.tm — 429 → خستنەوە (٢ جار)"""
    em = "alchat" + uuid.uuid4().hex[:10] + "@uberip.com"
    pw = "Xq" + uuid.uuid4().hex[:12] + "A!"
    for i in range(3):
        try:
            sess.post("https://api.mail.tm/accounts", json={"address": em, "password": pw}, timeout=(12, 30))
            time.sleep(3 if i == 0 else 1)
            for j in range(2):
                rt = sess.post("https://api.mail.tm/token", json={"address": em, "password": pw}, timeout=(12, 30))
                if rt.status_code == 200 and (rt.json() or {}).get("token"):
                    return em, pw, rt.json()["token"]
                time.sleep(25 if rt.status_code == 429 else 4)
            return em, pw, None
        except Exception as e:
            if i == 2:
                print(f"[ACH] mail: {str(e)[:70]}", flush=True)
            time.sleep(5)
    return em, pw, None

def _ach_wait_oob(sess, mtok, want="oobCode="):
    """چاوەڕوانی نامەی Firebase — دەرهێنانی کۆد"""
    for _ in range(12):
        time.sleep(5)
        try:
            msgs = sess.get("https://api.mail.tm/messages",
                            headers={"Authorization": f"Bearer {mtok}", "Accept": "application/json"},
                            timeout=(12, 25)).json() or []
        except Exception:
            continue
        for it in (msgs if isinstance(msgs, list) else [])[:3]:
            try:
                full = sess.get(f"https://api.mail.tm/messages/{it['id']}",
                                headers={"Authorization": f"Bearer {mtok}", "Accept": "application/json"},
                                timeout=(12, 25)).json() or {}
            except Exception:
                continue
            m = re.search(r'oobCode=([a-zA-Z0-9_\-]+)', (full.get("text") or "") + (full.get("html") and str(full.get("html")) or ""))
            if m:
                return m.group(1)
    return None

def _ach_fb_login(sess, email, pw):
    """لۆگین — idToken ی تازە (بۆ توکنی بەسەڕبوو >٤٠خ)"""
    r = sess.post(f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={ACH_FB_KEY}",
                  json={"email": email, "password": pw, "returnSecureToken": True}, timeout=(12, 30))
    d = r.json() or {}
    return d.get("idToken"), d.get("localId")

def _ach_alive():
    today = time.strftime("%Y-%m-%d", time.gmtime())
    out = []
    for a in (ACH_ST.get("accounts") or []):
        if a.get("dead"):
            continue
        if int(a.get("n") or 0) >= ACH_BUDGET:
            continue
        if a.get("day") != today:
            a["day"], a["n"] = today, 0  # کوانتا ڕۆژانە نەبووە — ژماردنی ناوخۆ تەنیا
        out.append(a)
    return out

def _ach_tok(acc):
    """توکنی تازە ئەگەر بەسەڕبوو (>٣٥خ)"""
    if time.time() - float(acc.get("ts") or 0) < 2100 and acc.get("tok"):
        return acc["tok"]
    try:
        sess = requests.Session()
        tok, _ = _ach_fb_login(sess, acc.get("email") or "", acc.get("pw") or "")
        if tok:
            acc["tok"], acc["ts"] = tok, time.time()
            with ACH_LOCK:
                _ach_save()
            return tok
    except Exception:
        pass
    return acc.get("tok") or ""

def fetch_models(timeout=15):
    """نوێترین مۆدەڵەکان لە aifreeforever"""
    try:
        r = requests.get(BASE_URL + "/api/chat-models", timeout=timeout,
                         headers={"User-Agent": UA})
        models = {}
        for p in r.json().get("pages", []):
            if p.get("available") and p.get("endpoint") and p.get("id"):
                models[p["id"]] = {
                    "name": p.get("name") or p["id"],
                    "endpoint": p["endpoint"],
                }
        return models
    except Exception:
        return {}

def hide_names(items, key="id"):
    """ناوەکان دەشارێتەوە → سێرڤەری یەک، دوو، سێ… (ڕێکخست بە کلیدووشە)"""
    ordered, used = [], set()
    for keys in SERVER_PRIORITY:
        for it in items:
            low = str(it[key]).lower()
            if it[key] not in used and any(k in low for k in keys):
                used.add(it[key])
                ordered.append(it)
                break
    ordered += [it for it in items if it[key] not in used]
    out = []
    for i, it in enumerate(ordered, 1):
        num = KURDISH_NUMS[i - 1] if i <= len(KURDISH_NUMS) else str(i)
        it = dict(it)
        it["name"] = f"الخادم {num}"
        out.append(it)
    return out

def sync_giz_models(force=False):
    """ئۆتۆ-ئەپدێتی GizAI: کاتالۆگی CDN (٦ کاتژمێر) — بێ probe (کوانتا نەسوتێت)؛
    فیلتەر: gateway/* (پارەدار) و free-limit-0 و شاراوە دەر دەکرێن"""
    import time as _t
    if not force and _t.time() - _GZ_SYNC["t"] < 21600:
        return
    try:
        r = requests.get(GZ_CDN, headers={"User-Agent": GZ_UA}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[GZ-SYNC] catalog {r.status_code}", flush=True)
            return
        cands = _gz_parse_catalog(r.text)
        if not cands:
            print("[GZ-SYNC] parse شکستی هێنا — کاتالۆگی کۆن دەمێنێتەوە", flush=True)
            return
        cat = {}
        for c in cands:
            v = c["value"]
            if v in GZ_SKIP or v.startswith("gateway/") or c.get("free0"):
                continue
            cat[v] = c["label"]
        # #91A12: NEVER-SHRINK — ئەگەر نوێ < 70% ی کۆن → کۆن بمێنێتەوە (flake ی سایت)
        _oldc = _GZ_SYNC.get("catalog") or {}
        if _oldc and len(cat) < len(_oldc) * 0.7:
            print(f"[GZ-SYNC] ⚠️ نوێ زۆر بچووکە ({len(cat)} < 70% ی {len(_oldc)}) — کۆن پارێزرا", flush=True)
            return
        _GZ_SYNC["catalog"] = cat
        _GZ_SYNC["t"] = _t.time()
        print(f"[GZ-SYNC] کاتالۆگ {len(cands)} → تۆمارکراو {len(cat)}", flush=True)
    except Exception as e:
        print(f"[GZ-SYNC] {str(e)[:80]}", flush=True)

def _tmp_inbox():
    """#94U50: inbox ی کاتی — temp-mail.org سەرەتا، mail.tm جێگرەوە (429-دژە)؛ دەگەڕێنێتەوە (email, poll_fn)"""
    import random as _r
    _UA = _rand_ua()
    try:  # 1) temp-mail.org
        s = requests.Session(); s.headers.update({"User-Agent": _UA})
        mb = s.post("https://web2.temp-mail.org/mailbox", timeout=(10, 30)).json() or {}
        if mb.get("mailbox") and mb.get("token"):
            jwt = mb["token"]

            def _poll(n=14, gap=5):
                mh = {"Authorization": "Bearer " + jwt, "Accept": "application/json"}
                for _ in range(n):
                    time.sleep(gap)
                    try:
                        msgs = (s.get("https://web2.temp-mail.org/messages", headers=mh, timeout=(10, 25)).json() or {}).get("messages") or []
                    except Exception:
                        continue
                    if msgs and msgs[0].get("_id"):
                        try:
                            return s.get(f"https://web2.temp-mail.org/messages/{msgs[0].get('_id')}", headers=mh, timeout=(10, 25)).text or ""
                        except Exception:
                            continue
                return ""
            return mb["mailbox"], _poll
    except Exception:
        pass
    try:  # 2) mail.tm (کاتی 429)
        ms = requests.Session(); ms.headers.update({"User-Agent": _UA})
        dom = (ms.get("https://api.mail.tm/domains", timeout=(15, 30)).json() or {}).get("hydra:member") or []
        if not dom:
            return None, None
        addr = f"tmx{_r.randrange(100000, 999999)}{int(time.time()) % 100000}@{(dom[0] or {}).get('domain')}"
        pw = "Xk9!mQ2#vLp8$zRw"
        r = ms.post("https://api.mail.tm/accounts", json={"address": addr, "password": pw}, timeout=(15, 30))
        if r.status_code not in (200, 201):
            return None, None
        mtok = (ms.post("https://api.mail.tm/token", json={"address": addr, "password": pw}, timeout=(15, 30)).json() or {}).get("token")
        if not mtok:
            return None, None

        def _poll2(n=14, gap=5):
            mh2 = {"Authorization": f"Bearer {mtok}"}
            for _ in range(n):
                time.sleep(gap)
                try:
                    msgs = (ms.get("https://api.mail.tm/messages", headers=mh2, timeout=(15, 30)).json() or {}).get("hydra:member") or []
                except Exception:
                    continue
                if msgs and msgs[0].get("id"):
                    try:
                        d = ms.get(f"https://api.mail.tm/messages/{msgs[0].get('id')}", headers=mh2, timeout=(15, 30)).json() or {}
                        t = d.get("text") or ""
                        h = d.get("html") or ""
                        if isinstance(t, list):
                            t = " ".join(t)
                        if isinstance(h, list):
                            h = " ".join(h)
                        return f"{t}\n{h}"
                    except Exception:
                        continue
            return ""
        print(f"[INBOX] mail.tm جێگرەوە ✅ {addr}", flush=True)
        return addr, _poll2
    except Exception:
        return None, None

def _gz_parse_catalog(t):
    """#91A6: safe-wrapper — parser هەرگیز sync ەک ناکوژێنێت"""
    try:
        return _gz_parse_catalog__raw(t)
    except Exception:
        return None

def _rand_ua():
    """#91S: ناسنامەی هەڕەمەکی — هەر داواکارییەکی دەرەکی جیاواز"""
    return random.choice(_UA_POOL)


# ---- state inits ----
_GZ_BADC = {}  # model → cooldown تا

_GZ_BURNED = {}  # #94U60: (px,model) → کاتی 429 (کوانتای کاتژمێر)

_GZ_WALL = {}  # #94U60: px → کاتی 401/403 (واڵ 30خولەک)

_GZ_GOOD = {}  # #94U60: px → دوایین سەرکەوتن (GOOD-first)

_GZ_PXOK = {}  # #94U61: px → کاتی qualification (cookie-forward سەلمێنرا)

_GZ_SEEDS = ["http://103.237.102.191:11111", "http://38.194.246.34:999", "http://190.97.241.106:999"]  # #94U61: سەلمێنراو 201/429 (reach+cookie ✅)

_GZ_CACHE = {}  # #95U3: (model,ctx-hash) → (ans, t) — پرۆمپتی کورت ≤40پیت، TTL 5خولەک

_GZ_MEM_LD = [False]

_GZ_MEM_SV = [0.0]

_GZ_SYNC = {"t": 0.0, "thread": None, "labels": {}}

_LR_SEM = threading.Semaphore(4)


def _gz_parse_catalog__raw(raw):
    """JS-catalog → لیستی {value, label, free0} — سکەنی ئۆبجێکت-بە-ئۆبجێکت (خێرا، بێ json5)"""
    import re as _re
    i = raw.find("items:[")
    if i < 0:
        return []
    t = raw[i + len("items:"):]
    out = []
    seen = set()
    pos = 0
    n = len(t)
    while True:
        st = t.find("{value:", pos)
        if st < 0 or st >= n:
            break
        depth = 0
        instr = None
        esc = False
        en = -1
        lim = min(st + 9000, n)
        for idx in range(st, lim):
            ch = t[idx]
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == instr:
                    instr = None
                continue
            if ch in ("`", '"', "'"):
                instr = ch
                esc = False
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    en = idx
                    break
        if en < 0:
            pos = st + 7
            continue
        obj = t[st:en + 1]
        pos = en + 1
        mv = _re.search(r'value:\s*["\'`]([^"\'`]{1,80})["\'`]', obj)
        if not mv:
            continue
        v = mv.group(1)
        if v in seen:
            continue
        seen.add(v)
        ml = _re.search(r'label:\s*["\'`]([^"\'`]{0,120})["\'`]', obj)
        free0 = bool(_re.search(r'free:\s*\{[^}]*throttleLimit:\s*0', obj))
        out.append({"value": v, "label": (ml.group(1) if ml else v), "free0": free0})
    return out

