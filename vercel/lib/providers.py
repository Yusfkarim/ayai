"""Vercel providers: ported funcs + KV pools + minters + catalog + chat router. NO Fly."""
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ported_raw as R
import shim

shim.install(R)
import kv

API_KEY = os.environ.get("VAPI_KEY") or os.environ.get("API_KEY") or ""
FB_KEYS = {
    "ca": os.environ.get("CA_FB_KEY") or "",
    "cb": os.environ.get("CB_FB_KEY") or "",
    "nv": os.environ.get("NV_FB_KEY") or "",
}
CRON_SECRET = os.environ.get("CRON_SECRET") or ""


# ═══════ KV overrides (rebind into R namespace — internal calls resolve here) ═══════
def _vpx_ach_load():
    d = kv.kv_jget("vpx:ach") or {}
    R.ACH_ST["accounts"] = d.get("accounts") or []
    R.ACH_ST["idx"] = int(d.get("idx") or 0)
    R.ACH_ST["signups"] = d.get("signups") or {"date": "", "n": 0}


def _vpx_ach_save():
    kv.kv_jset("vpx:ach", {"accounts": (R.ACH_ST.get("accounts") or [])[-400:],
                           "idx": R.ACH_ST.get("idx") or 0,
                           "signups": R.ACH_ST.get("signups") or {"date": "", "n": 0}})


def _vpx_gz_load():
    if R._GZ_MEM_LD[0]:
        return
    R._GZ_MEM_LD[0] = True
    try:
        d = kv.kv_jget("vpx:gzmem") or {}
        for k, v in (d.get("good") or {}).items():
            R._GZ_GOOD[k] = float(v)
        for k, v in (d.get("wall") or {}).items():
            R._GZ_WALL[k] = float(v)
        for k, v in (d.get("burned") or {}).items():
            p = k.split("\x00")
            if len(p) == 2:
                R._GZ_BURNED[(p[0], p[1])] = float(v)
        if d.get("catalog"):
            R._GZ_SYNC["catalog"] = d["catalog"]
            R._GZ_SYNC["t"] = d.get("cat_t") or 0
    except Exception:
        pass


def _vpx_gz_save():
    try:
        kv.kv_jset("vpx:gzmem", {
            "good": {k: v for k, v in list(R._GZ_GOOD.items())[:2000]},
            "wall": {k: v for k, v in list(R._GZ_WALL.items())[:2000]},
            "burned": {a + "\x00" + b: v for (a, b), v in list(R._GZ_BURNED.items())[:2000]},
            "catalog": R._GZ_SYNC.get("catalog") or {},
            "cat_t": R._GZ_SYNC.get("t") or 0})
    except Exception:
        pass


def _vpx_proxy_get(n=3):
    try:
        pxs = kv.kv_jget("vpx:px") or []
        random.shuffle(pxs)
        return pxs[:max(1, int(n))]
    except Exception:
        return []


def _vpx_proxy_mark_bad(px):
    try:
        pxs = [p for p in (kv.kv_jget("vpx:px") or []) if p != px]
        kv.kv_jset("vpx:px", pxs)
    except Exception:
        pass


R._ach_load = _vpx_ach_load
R._ach_save = _vpx_ach_save
R._gz_mem_load = _vpx_gz_load
R._gz_mem_save = _vpx_gz_save
R._proxy_get = _vpx_proxy_get
R._proxy_mark_bad = _vpx_proxy_mark_bad
try:
    _vpx_ach_load()
except Exception:
    pass
try:
    _vpx_gz_load()
except Exception:
    pass


# ═══════ catalogs ═══════
def _slug(v):
    return re.sub(r"[^a-zA-Z0-9]+", "-", str(v)).strip("-").lower()[:60] or "model"


def pol_models():
    c = kv.kv_jget("vpx:cat:pol") or {}
    if c.get("items") and time.time() - c.get("t", 0) < 21600:
        return c["items"]
    items = []
    try:
        import requests
        r = requests.get("https://text.pollinations.ai/models", timeout=15)
        for m in r.json():
            name = m.get("name")
            if not name:
                continue
            out = m.get("output_types") or m.get("output") or ["text"]
            if isinstance(out, str):
                out = [out]
            if "text" in out or not out:
                items.append({"id": "pol-" + name, "model": name})
        items = items[:12]
    except Exception:
        pass
    if not items:
        items = [{"id": "pol-openai", "model": "openai"}]
    kv.kv_jset("vpx:cat:pol", {"t": time.time(), "items": items})
    return items


def aff_models():
    c = kv.kv_jget("vpx:cat:aff") or {}
    if c.get("items") and time.time() - c.get("t", 0) < 21600:
        return c["items"]
    items = []
    try:
        live = R.fetch_models() or {}
        for mid, info in live.items():
            items.append({"id": "aff-" + str(mid), "model": str(mid),
                          "endpoint": (info or {}).get("endpoint") or ""})
        items = items[:40]
    except Exception:
        pass
    if items:
        kv.kv_jset("vpx:cat:aff", {"t": time.time(), "items": items})
    return items


def lr_models():
    return [{"id": "lr-nano", "model": "openai/gpt-5.4-nano",
             "name": "GPT-5.4 Nano (Lorka)"}]


def gz_models():
    cat = R._GZ_SYNC.get("catalog") or {}
    if not cat or time.time() - R._GZ_SYNC.get("t", 0) > 21600:
        try:
            R.sync_giz_models(force=True)
            cat = R._GZ_SYNC.get("catalog") or {}
            _vpx_gz_save()
        except Exception:
            pass
    return [{"id": "gz-" + _slug(v), "model": v, "name": lbl}
            for v, lbl in sorted(cat.items())][:40]


def ach_models():
    return [{"id": "ach-" + k, "model": k, "name": nm} for k, nm, _ in R.ACH_MODELS]


def full_catalog():
    out, seen = [], set()
    for fn in (pol_models, aff_models, lr_models, gz_models, ach_models):
        try:
            for it in fn() or []:
                if it.get("id") not in seen:
                    seen.add(it["id"])
                    out.append(it)
        except Exception:
            continue
    return out


# ═══════ chat router + fallback ═══════
def chat_once(model_id, messages, timeout=110):
    if model_id.startswith("pol-"):
        return R.pol_chat(model_id[4:] or "openai", messages, timeout)
    if model_id.startswith("lr-"):
        return R.lr_chat(messages, None, min(timeout, 75))
    if model_id.startswith("gz-"):
        for it in gz_models():
            if it["id"] == model_id:
                return R.gz_chat(messages, it["model"], min(timeout, 90))
        raise RuntimeError("gz model unknown: " + model_id)
    if model_id.startswith("ach-"):
        return R.ach_chat(messages, model_id[4:] or "consensus", min(timeout, 110))
    if model_id.startswith("aff-"):
        slug = model_id[4:]
        ep = ""
        for it in aff_models():
            if it["id"] == model_id:
                ep = it.get("endpoint") or ""
        q = next((str(m.get("content")) for m in reversed(messages)
                  if m.get("role") == "user"), "سڵاو")
        bot = R.AIFreeChat(model=slug, endpoint=ep or None, timeout=min(timeout, 120))
        return bot.chat(q, history=messages)
    raise RuntimeError("unknown model prefix: " + model_id)


ALIASES = {
    "gpt-5-mini": "ach-consensus", "gpt-5": "ach-consensus",
    "gpt-5-code": "ach-code", "gpt-5-math": "ach-math",
    "openai/gpt-4o-mini": "ach-gpt4o", "gpt-4o-mini": "ach-gpt4o",
    "gemini-2.5-flash": "ach-gemini", "gemini-2.5-flash-lite": "ach-gemini",
    "meta-llama/llama-3.1-8b-instruct": "ach-llama", "llama-3.1-8b": "ach-llama",
    "openai/gpt-5.4-nano": "lr-nano", "gpt-5.4-nano": "lr-nano",
    "openai": "pol-openai",
}


def chat(model_id, messages, timeout=110):
    model_id = ALIASES.get(model_id, model_id)
    order = [model_id, "pol-openai", "lr-nano"]
    try:
        affs = aff_models()
        if affs:
            order.append(affs[0]["id"])
    except Exception:
        pass
    last = None
    for mid in dict.fromkeys(order):
        try:
            return chat_once(mid, messages, timeout), mid
        except Exception as e:
            last = e
    raise last or RuntimeError("all providers failed")


# ═══════ minters (automatic account creation → KV pools) ═══════
def fb_signup_min(key, email, pw):
    import requests
    for px in _vpx_proxy_get(4) + [None]:
        try:
            kw = {"json": {"email": email, "password": pw, "returnSecureToken": True},
                  "headers": {"User-Agent": R.UA}, "timeout": (8, 20)}
            if px:
                kw["proxies"] = {"http": px, "https": px}
            r = requests.post("https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + key, **kw)
            if r.status_code == 200:
                j = r.json() or {}
                if j.get("idToken"):
                    return {"email": email, "password": pw,
                            "localId": j.get("localId") or "", "ts": time.time()}
                return None
            try:
                msg = (r.json() or {}).get("error", {}).get("message", "")
            except Exception:
                msg = ""
            if msg == "EMAIL_EXISTS":
                return "exists"
            if px:
                _vpx_proxy_mark_bad(px)
        except Exception:
            if px:
                _vpx_proxy_mark_bad(px)
    return None


_FB_PREFIX = ("komex", "heal", "arez", "hiva")
_FB_OFFS = (0, 3, 13, 40, 100, 250)


def mint_fb_pool(name, count=5, day_cap=2000, absmax=10000):
    key = FB_KEYS.get(name) or ""
    if not key:
        return {"minted": 0, "err": "no key"}
    meta = kv.kv_jget("vpx:poolmeta:" + name) or {}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    if meta.get("date") != today:
        meta = {"date": today, "n": 0, "next": meta.get("next") or random.randint(800000, 900000)}
    if int(meta.get("n") or 0) >= day_cap:
        return {"minted": 0, "err": "day-cap"}
    accs = kv.kv_jget("vpx:pool:" + name) or []
    have = {a.get("email") for a in accs}
    minted = 0
    for _ in range(count):
        if len(accs) >= absmax or int(meta.get("n") or 0) >= day_cap:
            break
        n = int(meta.get("next") or 800000) + random.randint(0, 500)
        made = None
        for pref in _FB_PREFIX:
            for off in _FB_OFFS:
                em = "%s%d@duidir.com" % (pref, n + off)
                if em in have:
                    continue
                pw = "%s#%d" % (em, random.randint(10000, 99999))
                r = fb_signup_min(key, em, pw)
                if r == "exists":
                    meta["next"] = n + off + 1
                    continue
                if r:
                    made = r
                    meta["next"] = n + off + 1
                    break
                time.sleep(0.5)
            if made:
                break
        if made:
            accs.append(made)
            have.add(made["email"])
            meta["n"] = int(meta.get("n") or 0) + 1
            minted += 1
        else:
            meta["next"] = n + 300
    kv.kv_jset("vpx:pool:" + name, accs[-absmax:])
    kv.kv_jset("vpx:poolmeta:" + name, meta)
    return {"minted": minted, "total": len(accs)}


def mint_ach(count=3):
    if not R.ACH_FB_KEY:
        return {"minted": 0, "err": "no key"}
    _vpx_ach_load()
    try:
        n0 = len(R._ach_alive())
    except Exception:
        n0 = 0
    for _ in range(count):
        try:
            if not R._ach_new_account():
                break
        except Exception:
            break
    _vpx_ach_load()
    try:
        n1 = len(R._ach_alive())
    except Exception:
        n1 = n0
    return {"minted": max(0, n1 - n0), "total": n1}


# ═══════ proxy harvest (lite) ═══════
_PX_URLS = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=8000",
    "https://proxylist.geonode.com/api/proxy-list?limit=200&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps",
]


def harvest_proxies(max_keep=60, deadline=150):
    import concurrent.futures as _cf
    import requests
    t0 = time.time()
    raw = []
    for u in _PX_URLS:
        if time.time() - t0 > 40:
            break
        try:
            r = requests.get(u, timeout=(8, 20), headers={"User-Agent": R.UA})
            if "geonode" in u:
                for p in (r.json().get("data") or []):
                    if p.get("ip") and p.get("port"):
                        raw.append("http://%s:%s" % (p["ip"], p["port"]))
            else:
                for ln in (r.text or "").splitlines():
                    ln = ln.strip()
                    if re.match(r"^\d+\.\d+\.\d+\.\d+:\d+$", ln):
                        raw.append("http://" + ln)
        except Exception:
            continue
    cands = list(dict.fromkeys(raw))[:150]
    good = []

    def _t(px):
        try:
            r = requests.get("http://www.google.com/generate_204",
                             proxies={"http": px, "https": px}, timeout=(5, 8))
            return px if r.status_code in (200, 204) else None
        except Exception:
            return None

    try:
        with _cf.ThreadPoolExecutor(max_workers=20) as ex:
            futs = [ex.submit(_t, px) for px in cands]
            for f in _cf.as_completed(futs, timeout=max(10, deadline - (time.time() - t0))):
                try:
                    r = f.result()
                except Exception:
                    r = None
                if r:
                    good.append(r)
                    if len(good) >= max_keep:
                        break
    except Exception:
        pass
    if good:
        try:  # giz needs cookie-forwarding proxies — qualify (else gz login-wall)
            good = R._gz_qualify(good) or good
        except Exception:
            pass
        kv.kv_jset("vpx:px", good[:max_keep])
    return {"proxies": len(good), "tested": len(cands)}


# ═══════ probes ═══════
def probe(provider):
    t0 = time.time()
    try:
        hello = [{"role": "user", "content": "Hi"}]
        if provider == "pol":
            R.pol_chat("openai", hello, 60)
        elif provider == "lr":
            R.lr_chat(hello, None, 60)
        elif provider == "aff":
            affs = aff_models()
            if not affs:
                return False, "no catalog"
            chat_once(affs[0]["id"], hello, 90)
        elif provider == "gz":
            items = gz_models()
            if not items:
                return False, "no catalog"
            chat_once(items[0]["id"], hello, 90)
        elif provider == "ach":
            R.ach_chat(hello, "consensus", 90)
        else:
            return False, "unknown"
        return True, round(time.time() - t0, 1)
    except Exception as e:
        return False, str(e)[:90]


def pool_stats():
    st = {}
    for name in ("ca", "cb", "nv"):
        accs = kv.kv_jget("vpx:pool:" + name) or []
        meta = kv.kv_jget("vpx:poolmeta:" + name) or {}
        st[name] = {"n": len(accs), "today": meta.get("n", 0)}
    try:
        _vpx_ach_load()
        st["ach"] = {"n": len(R._ach_alive())}
    except Exception:
        st["ach"] = {"n": 0}
    st["px"] = len(kv.kv_jget("vpx:px") or [])
    return st
