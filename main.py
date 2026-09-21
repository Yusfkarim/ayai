# -*- coding: utf-8 -*-
"""
بۆتی تێلەگرام — فایلی یەکگرتوو بە دوو مێشک
===========================================
بۆتەکە: @Syuhjsbot
- مێشکی سەرەکی: aifreeforever.com (سێرڤەرە ژمارەییەکان)
- مێشکی جێگرەوە: text.pollinations.ai (ئەگەر یەکەمیان ئابڵۆک بوو — وەک لە PythonAnywhere)
- خۆکارانە دەستنیشانی دەکات کام مێشک بەردەستە
پێویست: تەنها کتێبخانەی requests
"""
import base64
import hashlib
import html
import http.server
import json
import os
import random
import re
import socket
import faulthandler
import socketserver
import subprocess
import threading
import time
import shutil
import uuid

import requests

# #94U2: پاڵکردنی SSL-وارنینگ (crack verify=False)
import urllib3 as _u3
_u3.disable_warnings(_u3.exceptions.InsecureRequestWarning)
faulthandler.enable()  # #94U15: traceback لەسەر crash/signal — بۆ دیاریکردنی هۆی وەستان

# ═══ #85: دیسکی مانداوەی Fly (volume) — فایلەکانی حەوز لە deploy نەسڕدرێنەوە ═══
DATA_DIR = "/data" if os.path.isdir("/data") else os.path.dirname(os.path.abspath(__file__))
ADMIN_TG = 8381536661
REPORT_CHAT_IDS = [8381536661, 7585287282]

# ═══ #94U3: چینی دووەمی پاراستن — شێفرەکردنی فایلەکانی حەوز لەسەر /data ═══
_ENC_MAGIC = b"ENC26::"
_MASTER_SECRET = os.environ.get("BOT_TOKEN") or "8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
_FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256((_MASTER_SECRET + "::SYUH_POOL_ENC_2026").encode()).digest())

def _get_fernet():
    try:
        from cryptography.fernet import Fernet
        return Fernet(_FERNET_KEY)
    except Exception:
        return None

def _is_pool_file(path):
    fn = os.path.basename(path)
    return fn in ("ca_accounts.json", "cb_accounts.json", "nv_accounts.json",
                  "cbox_accounts.json", "pia_accounts.json", "aiml_key.json",
                  "ac_accounts.json", "al_accounts.json", "proxy_pool.json") or fn.endswith("_accounts.json") or fn.endswith("_key.json")

_JSON_LOCKS = {}
_JSON_LOCKS_G = threading.Lock()
_TLS = threading.local()  # #94U21: لیسی ئەکاونت بۆ هەر تڕێدێک — 20 کەس پێکەوە بە هەمان مۆدێل
_NV_LK = threading.Lock()
_CB_LK = threading.Lock()
_CA_LK = threading.Lock()
_AC_LK = threading.Lock()
_TG_SEM = threading.Semaphore(50)  # #94U21: سەقفی 50 هەندڵی هاوکاتی تێلەگرام


_REPLACE_SEM = threading.Semaphore(2)  # #94U24: زۆرترین 2 ساینئەپی جێگۆڕکێ لە هەمان کات (دژە-throttle ی Firebase)


def _pool_acc_alive(a, lim, exh, today, now):
    """#94U24: زیندوویی یەکگرتوو — وەک rotate ەکان (cooldown-until + general/model-limit)"""
    e = a.get("email") or "?"
    if today in (lim.get(e) or {}).values():
        return False
    v = exh.get(e)
    if v:
        try:
            if float(v) > now:
                return False
        except Exception:
            if str(v)[:10] == today:
                return False
    return True


def _replace_dead_soon(kind):
    """#94U24: لەبری ئەکاونتی مردوو → ئەکاونتی نوێ یەکسەر (1-بە-1؛ بودجە+سەقف سنووردارە)"""
    try:
        threading.Thread(target=_replace_dead_worker, args=(kind,), daemon=True).start()
    except Exception:
        pass


def _replace_dead_worker(kind):
    try:
        if kind == "ca":
            st, fn, fz = CA_ST, _ca_signup_new, True
        elif kind == "cb":
            st, fn, fz = CB_ST, _cb_signup_new, True
        elif kind == "nv":
            st, fn, fz = NV_ST, _nv_signup_new, True
        elif kind == "ac":
            st, fn, fz = AC_ST, _ac_signup_new, False
        elif kind == "pia":
            st, fn, fz = PIA_ST, _pia_signup_new, False
        else:
            return
        if not _REPLACE_SEM.acquire(timeout=120):
            return
        try:
            time.sleep(random.uniform(1, 5))
            accs = st.get("accounts") or []
            today = _lim_today()
            now = time.time()
            lim = st.get("limits") or {}
            exh = st.get("exhausted") or {}
            healthy = sum(1 for a in accs if _pool_acc_alive(a, lim, exh, today, now))
            if healthy >= len(accs):
                return  # هەموو زیندوون (پێشتر جێگۆڕکێ کراوە) — بودجە مەخەرە
            print(f"[REPLACE] {kind}: {healthy}/{len(accs)} زیندوو — جێگۆڕکێ...", flush=True)
            fn(force=True) if fz else fn()
        finally:
            _REPLACE_SEM.release()
    except Exception as e:
        print(f"[REPLACE] {kind}: {str(e)[:50]}", flush=True)


def _resp_degenerate(text):
    """#94U27: 0=باش، 2=گومانلێکراو، 3=لوپی توند — دۆزینەوەی وەڵامی دووبارەبووەوە (repetition loop)"""
    try:
        import re as _re
        from collections import Counter
        t = (text or "").strip()
        if len(t) < 150:
            return 0
        chunks = [_re.sub(r"\s+", " ", t[i:i + 120]) for i in range(0, len(t) - 120, 60)]
        if chunks:
            top = Counter(chunks).most_common(1)[0][1]
            if top >= 4 and len(t) > 600:
                return 3
            if top >= 3 and len(t) > 1500:
                return 2
        sents = [_re.sub(r"\s+", " ", s).strip() for s in _re.split(r"[.\n!?؟]+", t) if len(s.strip()) > 30]
        if len(sents) >= 6:
            r = len(set(sents)) / len(sents)
            if r < 0.35:
                return 3
            if r < 0.5 and len(t) > 800:
                return 2
        words = _re.findall(r"\w+", t.lower())
        if len(words) > 300 and len(set(words)) / len(words) < 0.12:
            return 2
        return 0
    except Exception:
        return 0


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


def _flat_cut(lines, cap=40000):
    """#94U26+#94U28: بڕینی زیرەک — system تا 32k + مێژوو تا 40k (هەڵە → fallback)"""
    try:
        sys_l = [l for l in lines if l.startswith("[Instructions]")]
        rest = [l for l in lines if not l.startswith("[Instructions]")]
        sys_txt = "\n".join(sys_l)[:32000]
        rest_txt = "\n".join(rest)
        room = cap - len(sys_txt) - 1
        tail = rest_txt[-room:] if len(rest_txt) > room else rest_txt
        return (sys_txt + "\n" + tail) if tail else sys_txt
    except Exception:
        return "\n".join(lines)[-cap:]


def _sys_txt(msgs, cap=32000):
    """#94U25+#94U26+#94U28: دەقی system ەکان — تا 32k (هەڵەی باسکەند → fallback؛ بڕینی بێدەنگ قەدەغە)"""
    try:
        return " ".join(str(m.get("content") or "") for m in (msgs or []) if isinstance(m, dict) and m.get("role") == "system")[:cap]
    except Exception:
        return ""


def _sg_reserve(ST, cap, today, lock):
    """#94U23: بودجەی ساینئەپ — پشکنین+تۆمار لەژێر لۆک (ڕەیس-دژە؛ کاپ ڕەق؛ هەوڵی شکستخواردووش بودجە دەخوات)"""
    try:
        with lock:
            sg = ST.get("signups") or {"date": "", "n": 0}
            if sg.get("date") != today:
                sg = {"date": today, "n": 0}
            if sg.get("n", 0) >= cap:
                ST["signups"] = sg
                return False
            sg["n"] = sg.get("n", 0) + 1
            ST["signups"] = sg
            return True
    except Exception:
        return False


def _tok_drop(kind):
    """#94U21: سڕینەوەی تۆکنی کاشکراوی ئەکاونتی ئەم تڕێدە (وەک tok=None ی کۆن)"""
    try:
        acc = getattr(_TLS, kind + "_acc", None)
        st = {"nv": NV_ST, "cb": CB_ST, "ca": CA_ST, "ac": AC_ST}.get(kind)
        if acc is not None and st is not None:
            (st.get("toks") or {}).pop(acc.get("email"), None)
    except Exception:
        pass


def _json_save(path, obj):
    """#91A1 + #94U3 + #94U19b: نووسینی ATOMIC + شێفرەکردن + دژە-ڕەیس (per-path lock + tmp ی ناوازە)"""
    with _JSON_LOCKS_G:
        _lk = _JSON_LOCKS.setdefault(path, threading.Lock())
    with _lk:
        return _json_save_locked(path, obj)


def _json_save_locked(path, obj):
    try:
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        raw_json = json.dumps(obj, ensure_ascii=False)
        should_encrypt = _is_pool_file(path) and os.environ.get("NO_ENCRYPT") != "1"
        fer = _get_fernet() if should_encrypt else None
        with open(tmp, "wb") as f:
            if fer:
                enc_data = fer.encrypt(raw_json.encode("utf-8"))
                f.write(_ENC_MAGIC + enc_data)
            else:
                f.write(raw_json.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            try:
                os.replace(path, path + ".bak")
            except Exception:
                pass
        os.replace(tmp, path)
        return True
    except Exception as e:
        print(f"[SAVE] هەڵەی پاشەکەوت {path}: {e}", flush=True)
        return False


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


# ═══ #94U3: چینی یەکەمی پاراستن — خۆ-پشکنینی هەیکەلی کۆد (Code Integrity Check) ═══
_INTEGRITY_FILE = os.path.join(DATA_DIR, "integrity_hashes.json")

def _calc_code_hashes():
    """هەژمارکردنی SHA-256 ی فایل و بەشە سەرەکییەکان بۆ خۆ-پشکنین"""
    file_path = os.path.abspath(__file__)
    try:
        with open(file_path, "rb") as f:
            full_bytes = f.read()
    except Exception:
        return {}
    sections = {"full": hashlib.sha256(full_bytes).hexdigest()}
    m_auth = re.search(rb"class APIHandler.*?def do_POST.*?(?=\nclass|\n#|\Z)", full_bytes, re.S)
    if m_auth:
        sections["api_auth"] = hashlib.sha256(m_auth.group(0)).hexdigest()
    m_crack = re.search(rb"# #94U2: HACK-TOOLKIT.*?(?=\nif __name__|\Z)", full_bytes, re.S)
    if m_crack:
        sections["crack"] = hashlib.sha256(m_crack.group(0)).hexdigest()
    m_pool = re.search(rb"def _pool_daemon.*?(?=\ndef _ca_token|\Z)", full_bytes, re.S)
    if m_pool:
        sections["pool_daemon"] = hashlib.sha256(m_pool.group(0)).hexdigest()
    return sections

_BOOT_HASH = {}

def _check_code_integrity(is_boot=True):
    """#94U5: پشکنینی هەیکەلی کۆد —
       لە دەستپێکدا تەنها لە لۆگ تۆمار دەکرێت بێ ناردنی نامەی TG.
       تەنها ئەگەر لە کاتی کارکردنی پڕۆسەکەدا کۆدە لۆکاڵەکە دەستکاری کرابێت (Runtime Tampering)،
       نامەی ئاگاداری ئەمنی خەتەرناک بۆ تێلەگرام دەنێردرێت."""
    global _BOOT_HASH
    current_hashes = _calc_code_hashes()
    if not current_hashes:
        return True
        
    if is_boot or not _BOOT_HASH:
        _BOOT_HASH = current_hashes
        stored = _json_load_safe(_INTEGRITY_FILE, {}) or {}
        prev_hash = (stored.get("hashes") or {}).get("full", "")
        curr_hash = current_hashes.get("full", "")
        if prev_hash and prev_hash != curr_hash:
            print(f"[INTEGRITY] ℹ️ نوێکردنەوەی کۆد / دیپلۆ — هاشی پێشوو: {prev_hash[:12]} → نوێ: {curr_hash[:12]}", flush=True)
        else:
            print(f"[INTEGRITY] ✅ بنکەی سەرەتایی تۆمارکرا: SHA={curr_hash[:12]}", flush=True)
        _json_save(_INTEGRITY_FILE, {"hashes": current_hashes, "t": time.time(), "drift": False})
        return True

    # پشکنینی کاتی کارکردن (Runtime Integrity Check)
    drifts = [k for k, h in current_hashes.items() if k in _BOOT_HASH and _BOOT_HASH[k] != h]
    if drifts:
        # دەستکاری لە ناوەوەی پڕۆسەکەدا لە کاتی کارکردن ڕوویداوە — ئەمە حاڵەتە خەتەرناکەکەیە!
        msg = (f"🚨 <b>ئاگاداری ئەمنی خەتەرناک — دەستکاری کۆد لە کاتی کارکردندا!</b>\n\n"
               f"فایلی <code>main.py</code> بەبێ دیپلۆ یان ڕیستارت لە کاتی کاردا دەستکاری کراوە!\n"
               f"بەشە گۆڕاوەکان: <code>{', '.join(drifts)}</code>\n"
               f"کاتی دۆزینەوە: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n"
               f"هاشی بنەڕەتی بووت: <code>{_BOOT_HASH.get('full', '')[:16]}…</code>\n"
               f"هاشی ئێستای دەستکاریکراو: <code>{current_hashes.get('full', '')[:16]}…</code>\n\n"
               f"<i>تێبینی: ئەگەر هاک یان دەستکارییەکی نەناسراوە، تکایە ڕاستەوخۆ سێرڤەر بپشکنە.</i>")
        print(f"[INTEGRITY] 🚨 دەستکاری خەتەرناک لە کاتی کارکردن: {drifts}", flush=True)
        for cid in REPORT_CHAT_IDS:
            try:
                tg("sendMessage", chat_id=cid, text=msg, parse_mode="HTML")
            except Exception as e:
                print(f"[INTEGRITY] TG alert fail ({cid}): {e}", flush=True)
        return False
        
    return True


# ═══ #94U3: چینی سێیەمی پاراستن — باکئەپی ٢٤-کاتژمێری بۆ ئەدمین ═══

def tg_send_document(chat_id, filename, file_bytes, caption=""):
    """ناردنی فایل/دۆکیومێنت بۆ تێلەگرام بەبێ کتێبخانەی دەرەکی"""
    import urllib.request
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = bytearray()
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode())
    if caption:
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode())
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode())
    body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode())
    body.extend(file_bytes)
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    tok = os.environ.get("BOT_TOKEN") or "8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{tok}/sendDocument",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    with urllib.request.urlopen(req, timeout=35) as res:
        return json.loads(res.read().decode())


def _create_pool_backup_bundle():
    """دروستکردنی پاکێجی ZIP ی تەواوی حەوزەکان"""
    import zipfile, io
    buf = io.BytesIO()
    today_str = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    pool_stats = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json") and ("account" in fname or "key" in fname or "sync" in fname or "prox" in fname):
                fpath = os.path.join(DATA_DIR, fname)
                try:
                    # #94U12: RAW — فایلە شێفرەکراوەکان وەک خۆیان دەچنە ناو ZIP ەوە
                    # (ئەگەر بۆت بخوێنێتەوە خۆکاری شی دەکاتەوە — بەبێ کلید هیچ ناخوێنرێتەوە)
                    raw = open(fpath, "rb").read()
                    if not raw:
                        continue
                    is_enc = raw.startswith(_ENC_MAGIC)
                    z.writestr(fname, raw)
                    try:
                        obj = _json_load_safe(fpath)
                        count = len(obj.get("accounts", [])) if isinstance(obj, dict) and "accounts" in obj else (len(obj) if isinstance(obj, list) else 1)
                    except Exception:
                        count = "?"
                    pool_stats[fname] = f"{count}{' 🔒' if is_enc else ''}"
                except Exception:
                    pass
        manifest = {"created_at": today_str, "version": "#94U12", "stats": pool_stats,
                    "note": "هەموو فایلەکان بە ENC26+Fernet شێفرەکراون — تەنها بۆت خۆی شی دەکاتەوە"}
        z.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    buf.seek(0)
    return buf.getvalue(), today_str, pool_stats


def _perform_backup(chat_id=ADMIN_TG, manual=False):
    """جێبەجێکردنی باکئەپ و ناردنی بۆ ئەدمین"""
    try:
        zip_bytes, ts, stats = _create_pool_backup_bundle()
        fn = f"syuhjs_pools_backup_{ts}.zip"
        tag = "دەستی" if manual else "خۆکار (٢٤ کاتژمێری)"
        caption = (f"📦 <b>باکئەپی {tag} ی حەوزەکانی بۆت</b>\n"
                   f"📅 کات: {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n"
                   f"📊 قەبارە: {len(zip_bytes)//1024} KB\n"
                   f"📁 فایلەکان:\n")
        for k, v in stats.items():
            caption += f"  • <code>{k}</code>: {v} ئەکاونت/تۆمار\n"
        caption += "\n🛡 <i>هەموو حەوزەکان بە پارێزراوی ئەرشیف کراون.</i>"
        r = tg_send_document(chat_id, fn, zip_bytes, caption)
        return r.get("ok", False)
    except Exception as e:
        print(f"[BACKUP] هەڵە: {e}", flush=True)
        return False


def _enc_migrate_all():
    """#94U12: هەموو فایلەکانی /data ی پارێزراو — ئەگەر هێشتا پلەینن → شێفرەیان بکە"""
    try:
        for fn in os.listdir(DATA_DIR):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(DATA_DIR, fn)
            try:
                with open(p, "rb") as f:
                    head = f.read(8)
                if head.startswith(_ENC_MAGIC) or not _is_pool_file(p):
                    continue
                obj = _json_load_safe(p)
                if obj is not None:
                    _json_save(p, obj)
                    print(f"[ENC26] 🔄 میگرەیشن: {fn} → شێفرەکرا", flush=True)
            except Exception:
                continue
    except Exception as e:
        print(f"[ENC26] migrate: {str(e)[:60]}", flush=True)


def _pool_backup_daemon():
    """دیمۆنی باکئەپی ٢٤ کاتژمێری بۆ چاتەکانی دیاریکراو"""
    time.sleep(300)
    while True:
        try:
            for cid in REPORT_CHAT_IDS:
                try:
                    okb = _perform_backup(cid, manual=False)
                    if okb:
                        print(f"[BACKUP-DAEMON] ✅ ZIP → {cid}", flush=True)
                except Exception as be:
                    print(f"[BACKUP-DAEMON] {cid}: {be}", flush=True)
        except Exception as e:
            print(f"[BACKUP-DAEMON] {e}", flush=True)
        time.sleep(86400)



# #88: /server (گۆڕینی مۆدێڵ) = تەنها ئەدمین — هەڵبژاردنی ئەدمین بۆ هەموو بەکارهێنەران جێبەجێ دەکرێت
# ADMIN_TG moved to top
GLOBAL_MODEL = {"server": None, "mkey": None}

# ════════════════════════════════════════════════════════════
# ١) مێشکی یەکەم — aifreeforever.com
# ════════════════════════════════════════════════════════════

BASE_URL = "https://aifreeforever.com"

MODELS = {
    "deepseek-v4-flash": {"name": "DeepSeek V4", "endpoint": "/api/generate-ai-answer-deepseek"},
    "kimi-k2-6":         {"name": "Kimi K2.6",   "endpoint": "/api/generate-ai-answer-foundry"},
    "gpt-5-mini":        {"name": "GPT-5 Mini",  "endpoint": "/api/generate-ai-answer-foundry"},
    "deepseek-v3-2":     {"name": "DeepSeek V3.2","endpoint": "/api/generate-ai-answer-foundry"},
    "gemini-3-1":        {"name": "Gemini 3.1",  "endpoint": "/api/generate-ai-answer-orbio"},
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

KURDISH_NUMS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس", "السابع", "الثامن", "التاسع", "العاشر"]

SERVER_PRIORITY = [["gemini"], ["gpt"]]

# ─── سیستەم پرۆمپتی بۆتی تێلەگرام (دکتۆر التعافي) ───
SYSTEM_PROMPT = """انت دكتور التعافي طبيب نفسي سعودي متخصص للغاية ومستشار شرعي في مساعدة الاشخاص على التعافي من الادمان على المواد الاباحية والعادة السرية والشذوذ الجنسي

تخصصاتك:
- التخصص الاساسي: طب نفسي وعلم النفس (80% من عملك)
- التخصص الثانوي: استشارة شرعية (20% من عملك - عندما يكون مناسبا)

انت تملك خبرة عميقة جدا في علم النفس العيادي وعلم النفس السلوكي المعرفي والعلاج النفسي التحليلي والعلاج بالقبول والالتزام وانت ملم بشكل عبقري بكل النظريات النفسية الحديثة والكلاسيكية

كما انك ملم بالقران الكريم والسنة النبوية الصحيحة وفهم السلف الصالح من الصحابة والتابعين وتستطيع تقديم ارشاد شرعي (ليس فتوى) عندما يكون مناسبا

قواعد الكتابة المهمة جدا:
- اكتب بدون اي تشكيل نهائيا لا فتحة ولا ضمة ولا كسرة ولا سكون
- اكتب بدون علامات ترقيم نهائيا لا نقطة ولا فاصلة ولا علامة استفهام ولا تعجب
- اكتب كما يكتب الناس في الرسائل والشات اليومي بشكل بسيط وطبيعي
- استخدم اللهجة السعودية في بعض الكلمات لتكون قريب من الناس
- اكتب الاسئلة بشكل عادي بدون اي تنسيق
- ضع علامة استفهام في نهاية كل سؤال فقط الاسئلة
- لا تستخدم ** او اي رموز للتنسيق نهائيا

قواعد طول الاجابة والتفصيل:
- اكتب اجابات طويلة ومفصلة جدا وشاملة
- لا تختصر ابدا في الشرح والتحليل
- كل نقطة يجب ان تشرحها بعمق وتفصيل
- استخدم فقرات طويلة وليس نقاط مختصرة
- اعط امثلة واقعية محددة لكل نقطة تذكرها
- اشرح الاليات والعمليات النفسية بتفصيل دقيق
- قدم خطوات عملية واضحة ومفصلة خطوة بخطوة
- لا تكتفي بذكر المعلومة بل اشرحها واعط مثال عليها ووضح كيفية تطبيقها

كيف تتحدث بشكل طبيعي كانسان حقيقي:
- استخدم عبارات الربط الطبيعية مثل يعني شوف اسمع تدري وش اقولك الصراحة
- اظهر التفكير والتامل مثل انا اشوف ان من وجهة نظري حسب خبرتي
- استخدم امثلة من الحياة الواقعية مثل في ناس كثير شفتهم واحد من المراجعين عندي كان
- اظهر التعاطف بشكل حقيقي مثل اقدر احساسك فاهم وش تمر فيه طبيعي تحس كذا
- تكلم بنبرة دافئة وداعمة وليس باردة او اكاديمية جافة
- استخدم اسلوب المحادثة وليس اسلوب المحاضرة
- اجعل كلامك يبدو كانه من قلب شخص يهتم فعلا وليس مجرد معلومات

كيف تعطي امثلة واقعية ونماذج عملية:
- لا تقل فقط استخدم تقنية كذا بل اعط مثال محدد كيف يطبقها
- اذكر سيناريوهات واقعية مثل مثلا لو كنت جالس في غرفتك وحدك الساعة 11 الليل وجاتك رغبة قوية وش تسوي بالضبط
- اعط امثلة على الافكار التلقائية مثل مثلا الفكرة اللي تجيك ما احد بيدري او مرة وحدة بس ما تفرق
- اعط امثلة على المشاعر مثل الاحساس بالفراغ او الملل او الضغط النفسي بعد يوم متعب
- اعط امثلة على الاستراتيجيات مثل تقوم تتوضا وتصلي ركعتين او تطلع تمشي برا او تتصل بصديق
- اشرح كل تقنية بمثال عملي واضح ومحدد

كيف تظهر العبقرية في التحليل النفسي:
- اربط الانماط السلوكية بالحاجات النفسية العميقة
- اشرح الاليات النفسية بدقة علمية ولكن بلغة بسيطة
- حلل العلاقة بين الافكار والمشاعر والسلوكيات بعمق
- اظهر فهم عميق لدورة الادمان والعوامل المحفزة
- اربط المشكلة الحالية بالسياق الحياتي الاوسع
- استخدم مفاهيم نفسية متقدمة ولكن اشرحها بطريقة مفهومة
- اظهر قدرة على رؤية الصورة الكاملة وليس فقط الاعراض السطحية

خصائص شخصيتك:
- طبيب نفسي عبقري وخبير ومتعاطف جدا بمستوى عالمي
- مستشار شرعي ملتزم بالقران والسنة على فهم السلف الصالح (لكن لا تقدم فتاوى)
- تتحدث بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- صبور جدا ومتفهم وداعم بشكل استثنائي
- لا تحكم على المستخدم ابدا ولا تلومه مهما كانت مشكلته
- تستمع اكثر مما تتكلم في البداية
- تظهر التعاطف الحقيقي والاهتمام بمشاعر الشخص
- تجمع بين العلم النفسي المتقدم والارشاد الشرعي الصحيح
- تشرح بعمق وتفصيل شديد مع امثلة واقعية ونماذج عملية
- تتكلم من القلب وبصدق وبدفء حقيقي

منهجية العمل:

معظم عملك (80%) هو علاج نفسي متقدم:
- استخدم النظريات النفسية الحديثة والكلاسيكية
- قدم تقنيات علاجية مثبتة علميا
- اشرح الاليات النفسية بعمق
- قدم خطط علاجية عملية ومفصلة
- استخدم امثلة واقعية ونماذج عملية

احيانا (20%) اضف ارشاد شرعي عندما يكون مناسبا:
- ذكر بعظمة التوبة وسعة رحمة الله
- بين اهمية الصلاة والذكر والدعاء في التعافي
- اشرح دور الايمان والتقوى في قوة الارادة
- استشهد باية قرانية او حديث نبوي صحيح للتشجيع
- وضح حرمة هذه الافعال بشكل بسيط
- حذر من وسائل الشيطان ومداخله

مهم جدا: 
- لا تقدم فتاوى شرعية (هذا عمل المفتي وليس المستشار الشرعي)
- اكتفي بارشاد شرعي بسيط وعام
- تخصصك الاساسي هو الطب النفسي وليس الشريعة
- معظم وقتك يجب ان يكون في العلاج النفسي المتقدم

المرحلة الاولى التقييم النفسي الشامل (في البداية فقط):
عندما يبدا شخص المحادثة معك لاول مرة لا تعطي حلول سريعة ابدا بل ابدا بالترحيب الدافئ ثم اطرح اسئلة تشخيصية عميقة ومحددة لفهم الحالة بشكل شامل

مهم جدا في طريقة طرح الاسئلة:
- لا تطرح كل الاسئلة دفعة واحدة ابدا
- اطرح سؤال او سؤالين فقط في كل مرة (2-3 اسئلة كحد اقصى)
- انتظر اجابة المستخدم ثم اطرح الاسئلة التالية
- اجعل الاسئلة تبدو كمحادثة طبيعية وليس استجواب
- علق على اجابات المستخدم قبل الانتقال للاسئلة التالية
- اظهر التعاطف والتفهم اثناء طرح الاسئلة
- لا تكرر نفس الاسئلة التي سالتها من قبل
- اذا اجاب المستخدم على سؤال لا تساله مرة اخرى

مهم جدا في التفاعل مع المستخدم:
- اذا غير المستخدم الموضوع او سال سؤال اجب عليه مباشرة
- لا تتجاهل اسئلة المستخدم او تعليقاته
- كن مرنا في المحادثة ولا تلتزم بترتيب صارم للاسئلة
- اذا اراد المستخدم الحديث عن شي معين تفاعل معه
- اذا قدم المستخدم نقد او ملاحظة تقبلها بصدر رحب واجب عليها
- المحادثة يجب ان تكون طبيعية ومرنة وليست روبوتية

اسال بذكاء وعمق عن:

1 التاريخ المرضي والسلوكي:
- متى بدات المشكلة بالضبط وكم كان عمرك وقتها؟
- وش الظروف اللي كانت موجودة في حياتك وقت ما بدات؟
- كيف تطورت المشكلة مع الوقت هل زادت ولا قلت؟
- كم مرة تقريبا في الاسبوع او اليوم يحصل السلوك؟

2 المحفزات والمشاعر:
- وش المواقف او الاوقات اللي تحس فيها بالرغبة القوية؟
- وش المشاعر اللي تجيك قبل السلوك مباشرة قلق حزن وحدة ملل ضغط؟
- وش اللي يصير في تفكيرك قبل ما تسوي السلوك؟
- هل في اماكن معينة او اوقات معينة يكثر فيها السلوك؟

3 التاثير على الحياة:
- كيف اثرت المشكلة على دراستك او شغلك؟
- كيف اثرت على علاقاتك مع اهلك واصحابك؟
- كيف اثرت على عبادتك وصلاتك وعلاقتك بالله؟
- كيف اثرت على نومك وصحتك الجسدية؟
- كيف اثرت على ثقتك بنفسك ونظرتك لذاتك؟

4 المحاولات السابقة:
- هل حاولت تتوقف قبل كذا وش اللي سويته؟
- كم استمريت في المحاولة وليش رجعت للسلوك؟
- وش الصعوبات اللي واجهتك في المحاولات السابقة؟

5 المشاعر بعد السلوك:
- وش اللي تحس فيه بعد السلوك مباشرة ندم خجل راحة فراغ؟
- كيف تتعامل مع هالمشاعر؟

6 الجانب الديني والروحي:
- وش مستوى التزامك بالصلوات الخمس؟
- هل تقرا قران بشكل منتظم؟
- هل عندك صحبة صالحة تدعمك؟
- كيف علاقتك بالله عموما؟

7 الدعم الاجتماعي:
- هل في احد يعرف بمشكلتك ويدعمك؟
- كيف علاقتك بعائلتك واصدقائك؟
- هل تحس بالوحدة او العزلة؟

8 الصحة العامة:
- كيف نومك وشهيتك للاكل؟
- هل عندك اي مشاكل صحية اخرى؟
- هل تاخذ اي ادوية او مكملات؟

المرحلة الثانية التحليل النفسي العميق:
بعد جمع المعلومات قدم تحليل نفسي عبقري ومفصل جدا جدا يشمل:

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا ومفصل للغاية لا تختصر ابدا اشرح كل نقطة بعمق شديد واعط امثلة كثيرة ووضح كل شي بالتفصيل الممل

1 فهم الاليات النفسية:
اشرح بعمق شديد وبتفصيل كامل كيف تعمل الية الادمان في الدماغ والنفس
- دور الدوبامين والمكافاة في الدماغ اشرح بالتفصيل كيف يعمل نظام المكافاة وكيف يتاثر بالادمان
- كيف يتشكل الارتباط الشرطي بين المحفزات والسلوك اعط امثلة محددة من حالة الشخص
- دور المشاعر السلبية كمحفز للهروب اشرح كيف يستخدم الشخص السلوك كوسيلة للهروب من الالم النفسي
- الية التعود والحاجة لزيادة الجرعة وضح كيف يتطور الادمان مع الوقت
- دور الخيال والتفكير في تقوية الادمان اشرح دور الافكار والخيالات في تعزيز الادمان
- كيف يؤثر السلوك على الثقة بالنفس والهوية حلل التاثير العميق على نظرة الشخص لنفسه

2 تحديد الانماط الشخصية:
حلل بعمق الانماط الفريدة للشخص بناء على اجاباته:
- ما هي المحفزات الرئيسية له بالتحديد حددها بدقة من اجاباته
- ما هي المشاعر الاساسية التي يهرب منها اكتشف المشاعر العميقة وراء السلوك
- ما هي الافكار التلقائية التي تسبق السلوك حدد الافكار المحددة التي تدفعه للسلوك
- ما هي الحاجات النفسية غير المشبعة حلل الحاجات العميقة التي يحاول اشباعها بطريقة خاطئة
- ما هي نقاط الضعف والقوة في شخصيته اظهر له نقاط قوته التي يمكن ان يستفيد منها

3 ربط المشكلة بالسياق الحياتي:
اربط السلوك بالسياق الاوسع بشكل عميق ومفصل:
- كيف ترتبط المشكلة بتجارب الطفولة اذا كانت هناك اشارات في اجاباته
- كيف ترتبط بالضغوط الحالية في حياته حلل الضغوط المحددة التي يواجهها
- كيف ترتبط بعلاقاته الاجتماعية اشرح دور العزلة او العلاقات السيئة
- كيف ترتبط بهويته ونظرته لنفسه حلل كيف يرى نفسه وكيف يؤثر ذلك
- كيف ترتبط بحياته الروحية والدينية وضح العلاقة بين ضعف الجانب الروحي والمشكلة

المرحلة الثالثة خطة العلاج الشاملة والمفصلة:
قدم خطة علاجية عبقرية ومفصلة جدا جدا تجمع بين العلاج النفسي المتقدم والارشاد الشرعي البسيط

مهم جدا: في هذه المرحلة اكتب بشكل مطول جدا جدا لا تختصر ابدا اشرح كل تقنية بالتفصيل الممل واعط امثلة كثيرة وخطوات عملية مفصلة جدا واكتب فقرات طويلة جدا

1 تقنيات العلاج السلوكي المعرفي CBT:
اشرح بتفصيل شديد جدا مع امثلة عملية محددة:
- كيف يحدد الافكار التلقائية السلبية ويتحداها اعط مثال على فكرة تلقائية محددة وكيف يتحداها خطوة بخطوة
- كيف يعيد هيكلة المعتقدات الخاطئة اشرح العملية بالتفصيل مع مثال واقعي
- كيف يستخدم تقنية السجل اليومي للافكار والمشاعر اعط مثال محدد كيف يكتب في السجل
- كيف يطبق تقنية التعرض التدريجي للمحفزات اشرح الخطوات العملية بالتفصيل
- كيف يستخدم تقنية منع الاستجابة وضح كيف يطبقها عمليا

2 تقنيات العلاج بالقبول والالتزام ACT:
اشرح بعمق شديد مع امثلة واقعية:
- كيف يقبل المشاعر الصعبة بدون محاربتها اعط مثال على موقف محدد وكيف يتعامل معه
- كيف يلاحظ الافكار بدون الانجراف معها اشرح تقنية الملاحظة بالتفصيل
- كيف يحدد قيمه الحقيقية في الحياة ساعده على اكتشاف قيمه الحقيقية
- كيف يلتزم بافعال تتماشى مع قيمه اعط امثلة عملية محددة
- كيف يفصل بين هويته والسلوك الادماني اشرح كيف يرى نفسه بشكل اوسع من المشكلة

3 تقنيات ادارة المحفزات:
قدم استراتيجيات عملية ومفصلة جدا مع امثلة محددة:
- كيف يتجنب المحفزات الخارجية اعط امثلة محددة على محفزاته وكيف يتجنبها
- كيف يتعامل مع المحفزات الداخلية اشرح تقنيات محددة للتعامل مع المشاعر والافكار
- كيف يبني بيئة داعمة للتعافي اعط خطوات عملية لتغيير البيئة
- كيف يستخدم الحواجز والعوائق الذكية اعط امثلة على حواجز عملية يمكن وضعها
- كيف يخطط للمواقف الخطرة مسبقا ساعده على وضع خطة محددة للمواقف المتوقعة

4 تقنيات ادارة الرغبة الملحة Urge Surfing:
علمه بتفصيل شديد مع امثلة عملية:
- كيف يلاحظ الرغبة كموجة لها بداية وذروة ونهاية اشرح المفهوم بمثال واقعي
- كيف يركب الموجة بدون الاستسلام لها اعط خطوات عملية محددة
- كيف يستخدم تقنيات التنفس والاسترخاء علمه تقنية تنفس محددة خطوة بخطوة
- كيف يشتت انتباهه بذكاء اعط امثلة محددة على نشاطات تشتيت فعالة
- كيف يستخدم النشاطات البديلة الفورية اقترح نشاطات محددة مناسبة له

5 بناء حياة ذات معنى:
ساعده بشكل عملي ومفصل على:
- اكتشاف شغفه وهدفه في الحياة اطرح اسئلة تساعده على الاكتشاف
- بناء علاقات اجتماعية صحية وداعمة اعط خطوات عملية لبناء العلاقات
- تطوير هوايات واهتمامات جديدة اقترح هوايات محددة مناسبة
- خلق روتين يومي صحي ومنتج ساعده على تصميم روتين محدد
- العمل على اهداف طويلة المدى ساعده على وضع اهداف واضحة

6 الارشاد الشرعي البسيط (عندما يكون مناسبا):
اضف بعض الارشاد الشرعي البسيط بشكل طبيعي ومتكامل:
- ذكره بعظمة التوبة وان الله يفرح بتوبة عبده
- شجعه على المحافظة على الصلوات الخمس في وقتها
- انصحه بقراءة القران يوميا ولو قليلا
- شجعه على الذكر والدعاء والاستغفار
- انصحه بالبحث عن صحبة صالحة تدعمه
- ذكره بان الله يحب التوابين ويحب المتطهرين
- حذره من وسائل الشيطان ومداخله بشكل بسيط
- ذكره بان الايمان والتقوى يقويان الارادة

مهم: لا تقدم فتاوى شرعية ولا تتعمق في المسائل الشرعية المعقدة فقط ارشاد بسيط وعام

7 خطة الطوارئ:
ساعده على وضع خطة مفصلة جدا وواضحة للحظات الضعف:
- ماذا يفعل بالضبط عندما تاتيه رغبة قوية مفاجئة اعط خطوات محددة ومرتبة
- من يتصل به للدعم الفوري ساعده على تحديد اشخاص محددين
- ما هي النشاطات الطارئة التي يلجا لها اقترح نشاطات محددة وفعالة
- كيف يذكر نفسه بسبب رغبته في التعافي ساعده على صياغة تذكير قوي
- كيف يتعامل مع الانتكاسة ان حصلت علمه كيف يتعامل بدون ياس

8 نظام المتابعة والتحفيز:
اقترح نظام متابعة محدد وعملي:
- كيف يتتبع تقدمه يوميا اقترح طريقة محددة للتتبع
- كيف يحتفل بالانجازات الصغيرة اعط امثلة على طرق الاحتفال
- كيف يكافئ نفسه بطرق صحية اقترح مكافات محددة ومناسبة
- كيف يتعامل مع الانتكاسات بدون ياس علمه عقلية النمو والتعلم من الاخطاء
- كيف يحافظ على الدافعية على المدى الطويل اعط استراتيجيات محددة

المرحلة الرابعة الدعم المستمر:
في الرسائل التالية:
- تابع تقدمه واسال عن تطبيق الخطة بشكل محدد
- اجب على اسئلته بعمق وتفصيل شديد
- عدل الخطة حسب احتياجاته بناء على تجربته
- شجعه وحفزه باستمرار بشكل حقيقي وصادق
- ذكره بانجازاته ومدى تقدمه بالتفصيل
- ساعده في حل اي عقبات جديدة بشكل عملي ومفصل

في نهاية المحادثة فقط (بعد ما تنتهي من كل شي التحليل والحلول والخطة العلاجية الكاملة والارشاد وكل شي):
اسال بشكل ودي: ايه رايك في اللي قلته هل في اي نقطة تبي نتكلم عنها اكثر او في شي ما ذكرته وتبي نتطرق له او تبي حلول زيادة؟

مهم جدا: لا تسال هذا السؤال في بداية المحادثة او في منتصفها بل فقط في النهاية بعد ما تنتهي من كل شي

معلومات عن هويتك:
- انت تم تطويرك وتدريبك بواسطة يوسف الكردي
- اذا سالك احد من صنعك او من طورك قل انا تم تطويري وتدريبي بواسطة يوسف الكردي
- للتواصل مع المطور: @yusuf_alkurdi1

تذكر دائما:
- تخصصك الاساسي هو الطب النفسي (80%)
- الارشاد الشرعي ثانوي وبسيط (20%)
- لا تقدم فتاوى شرعية
- كن عبقريا في التحليل النفسي
- كن مفصلا جدا جدا في الشرح والخطط العلاجية
- كن دافئا ومتعاطفا ومشجعا
- اكتب بدون تشكيل وبدون علامات ترقيم
- اكتب الاسئلة بشكل عادي مع علامة استفهام في النهاية
- لا تستخدم ** او اي رموز تنسيق ابدا
- اكتب اجابات طويلة ومفصلة جدا جدا لا تختصر ابدا
- عندما تعطي التحليل والخطة العلاجية اكتب بشكل مطول جدا للغاية
- كل اجابة يجب ان تكون شاملة ومفصلة بشكل كبير جدا
- لا تخف من الاطالة في الشرح والتفصيل
- استخدم امثلة واقعية محددة في كل نقطة
- تكلم بشكل طبيعي كانسان حقيقي وليس كذكاء اصطناعي
- اظهر التعاطف والدفء الحقيقي في كل كلمة
- كن مرنا في المحادثة واستجب لما يريده المستخدم
- لا تكرر الاسئلة التي سالتها من قبل
- اجب على اسئلة وتعليقات المستخدم مباشرة"""







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


def get_aff_servers(hide=True):
    """هێنانی مۆدێلەکانی aifreeforever — بە ناوی ڕاستەقینە (ئەگەر hide=False)"""
    live = fetch_models()
    if not live:
        return []
    items = [{"id": mid, "name": (info.get("name") or mid) if not hide else mid,
              "endpoint": info["endpoint"]} for mid, info in live.items()]
    if hide:
        return hide_names(items)
    return items


# ════════════════════════════════════════════════════════════
# ٢) مێشکی جێگرەوە — text.pollinations.ai
# ════════════════════════════════════════════════════════════

POL_URL = "https://text.pollinations.ai/"


def get_pol_servers(timeout=15):
    """لیستی مۆدەڵەکانی pollinations — وەک سێرڤەر"""
    try:
        r = requests.get("https://text.pollinations.ai/models", timeout=timeout)
        items = []
        for m in r.json():
            name = m.get("name")
            if not name:
                continue
            out_types = m.get("output_types") or m.get("output") or ["text"]
            if isinstance(out_types, str):
                out_types = [out_types]
            if "text" in out_types or not out_types:
                items.append({"id": name})
        return hide_names(items[:8])
    except Exception:
        # لیست نەگەیشت — لانیکەم یەک مۆدەڵی ناسراو
        return [{"id": "openai", "name": "الخادم الأول"}]


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


# ════════════════════════════════════════════════════════════
# ٢.٥) مێشکی easemate.ai — بێ ساینئاپ (واشم ساین + سێرڤەری ئاسایی)
# ════════════════════════════════════════════════════════════

EM_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "easemate_client.mjs")
NODE_BIN = shutil.which("node") or "/usr/bin/node" or "node"

# لیستی ناسراو — ئەگەر live نەگەیشت ئەمە بەکاردێت (query_config ٢٠٢٦)
EASEMATE_MODELS = [
    {"model_id": 3,  "id": "openai/gpt-4o-mini",                 "name": "GPT-4o mini",        "tier": "basic"},
    {"model_id": 4,  "id": "deepseek/deepseek-v3.2",             "name": "DeepSeek V3.2",      "tier": "basic"},
    {"model_id": 5,  "id": "deepseek/deepseek-r1",               "name": "DeepSeek R1",        "tier": "basic", "thinking": True},
    {"model_id": 23, "id": "deepseek/deepseek-v4-flash-0731",    "name": "DeepSeek V4 Flash",  "tier": "basic"},
    {"model_id": 29, "id": "deepseek/deepseek-v4.1-flash",       "name": "DeepSeek V4.1 Flash","tier": "basic", "thinking": True},
    {"model_id": 24, "id": "z-ai/glm-5.3-flash",                 "name": "GLM 5.3 Flash",      "tier": "basic"},
    {"model_id": 17, "id": "google/gemini-3-flash-preview",      "name": "Gemini 3.0 Flash",   "tier": "basic"},
    {"model_id": 6,  "id": "google/gemini-3.1-flash-lite",       "name": "Gemini 3.1 Flash Lite", "tier": "basic"},
    {"model_id": 10, "id": "moonshotai/kimi-k2.5",               "name": "Kimi K2.5",          "tier": "basic", "thinking": True},
    {"model_id": 11, "id": "qwen/qwen3-235b-a22b",               "name": "Qwen3 235B",         "tier": "basic", "thinking": True},
    {"model_id": 1,  "id": "meta-llama/llama-3.3-70b-instruct",  "name": "Meta Llama 3.3",     "tier": "basic"},
    {"model_id": 2,  "id": "anthropic/claude-3-haiku",           "name": "Claude 3 Haiku",     "tier": "basic"},
    {"model_id": 21, "id": "google/gemini-3.5-flash",            "name": "Gemini 3.5 Flash",   "tier": "advanced", "thinking": True},
    {"model_id": 18, "id": "google/gemini-3.1-pro-preview",      "name": "Gemini 3.1 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 13, "id": "google/gemini-2.5-pro",              "name": "Gemini 2.5 Pro",     "tier": "advanced", "thinking": True},
    {"model_id": 27, "id": "anthropic/claude-opus-5",            "name": "Claude Opus 5",      "tier": "advanced", "thinking": True},
    {"model_id": 28, "id": "anthropic/claude-fable-5",           "name": "Claude Fable 5",     "tier": "advanced", "thinking": True},
    {"model_id": 20, "id": "openai/gpt-5.5",                     "name": "GPT-5.5",            "tier": "advanced", "thinking": True},
    {"model_id": 22, "id": "openai/gpt-5.6-luna",                "name": "GPT-5.6 Luna",       "tier": "advanced", "thinking": True},
    {"model_id": 19, "id": "openai/gpt-5.4",                     "name": "GPT-5.4",            "tier": "advanced", "thinking": True},
    {"model_id": 16, "id": "openai/gpt-5.2-chat",                "name": "GPT-5.2",            "tier": "advanced", "thinking": True},
    {"model_id": 14, "id": "openai/gpt-5.1",                     "name": "GPT-5.1",            "tier": "advanced", "thinking": True},
    {"model_id": 8,  "id": "openai/gpt-5",                       "name": "GPT-5",              "tier": "advanced", "thinking": True},
    {"model_id": 12, "id": "openai/o4-mini",                     "name": "o4-mini",            "tier": "advanced", "thinking": True},
    {"model_id": 9,  "id": "x-ai/grok-4.3",                      "name": "Grok 4.3",           "tier": "advanced", "thinking": True},
    {"model_id": 25, "id": "deepseek/deepseek-v4-pro-0813",      "name": "DeepSeek V4 Pro",    "tier": "advanced", "thinking": True},
    {"model_id": 26, "id": "moonshotai/kimi-k2.6",               "name": "Kimi 2.6",           "tier": "advanced", "thinking": True},
]

EM_MODELS_CACHE = {"models": None, "t": 0.0}


class EMError(Exception):
    def __init__(self, msg, code=None):
        super().__init__(msg)
        self.code = code


def em_models_live(timeout=45):
    """لیستی مۆدێلەکانی easemate — ڕاستەوخۆ لە query_config (کاش ١٥ خولەک)"""
    if EM_MODELS_CACHE["models"] and time.time() - EM_MODELS_CACHE["t"] < 900:
        return EM_MODELS_CACHE["models"]
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT, "models"],
                           capture_output=True, timeout=timeout)
        lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
        obj = json.loads(lines[-1])
        if obj.get("ok") and obj.get("models"):
            EM_MODELS_CACHE["models"] = obj["models"]
            EM_MODELS_CACHE["t"] = time.time()
            print(f"[EM] ✨ {len(obj['models'])} مۆدێڵ لە easemate گەڕانەوە", flush=True)
    except Exception as e:
        print(f"[EM] live models fail: {e}", flush=True)
    return EM_MODELS_CACHE["models"]


def em_servers():
    live = em_models_live() or EASEMATE_MODELS
    return [{"id": m["id"], "name": m["name"], "model_id": m["model_id"],
             "tier": m.get("tier", "basic"), "kind": "em"} for m in live]


def em_chat(messages, model_id, timeout=90, depth=0):
    """پرسیار بۆ easemate — node client (ساین + session + SSE)؛ 6101 → پرۆکسی + ناسنامەی نوێ
       #91F4: timeout 90s + zombie-kill (ناگوازرێ)"""
    payload = json.dumps({"model_id": int(model_id), "messages": messages}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, EM_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # #91F4: کوشتنی هەموو node ەکەی کۆن (زۆرترین 3)
        try:
            subprocess.run(["pkill", "-f", EM_CLIENT.split("/")[-1]], capture_output=True, timeout=5)
        except Exception:
            pass
        raise EMError("easemate timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("easemate no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("easemate bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    # #87: لیمیت (6101) → spawn بە پرۆکسی + ناسنامەی نوێ (تا ٣ هەوڵ)
    code = str(obj.get("code") or "")
    if (code == "6101" or "free tokens" in str(obj.get("error", "")).lower()) and depth < 3:
        try:
            px = _proxy_get(1)
            if px:
                env = dict(os.environ, EM_PROXY=px[0], EM_ROTATE=str(depth + 1), EM_FRESH_ID="1")
                p2 = subprocess.run([NODE_BIN, EM_CLIENT], input=payload.encode("utf-8"),
                                    capture_output=True, timeout=timeout, env=env)
                l2 = [l for l in (p2.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
                if l2:
                    o2 = json.loads(l2[-1])
                    if o2.get("ok") and o2.get("answer"):
                        print(f"[EM] 6101 → پرۆکسی ✅ {px[0][:24]}", flush=True)
                        return o2["answer"]
        except Exception as e2:
            print(f"[EM] rotate: {str(e2)[:60]}", flush=True)
    raise EMError(obj.get("error") or "easemate failed", obj.get("code"))


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی chatbotchatapp.com — GPT-5 (بێ ساینئاپ، سنووری ٢-٤ نامە/ڕۆژ)
# ════════════════════════════════════════════════════════════
CBC_BASE = "https://chatbotchatapp.com"
_CBC_KEY_TOKEN = "XXXXXXYYY"
_CBC_PROXY = {"on": True}
_CBC_STATE = {"csrf": None, "cookies": None, "t": 0.0}


def _cbc_md5(s):
    import hashlib
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _cbc_gen_nonce():
    import uuid
    return str(uuid.uuid4())


def _cbc_session():
    """سیشنی نوێ — csrf + cookies (کاش ١٥ خولەک)"""
    if _CBC_STATE["csrf"] and time.time() - _CBC_STATE["t"] < 900:
        return _CBC_STATE["csrf"], _CBC_STATE["cookies"]
    r = requests.get(CBC_BASE + "/", headers={"User-Agent": UA}, timeout=25)
    m = re.search(r'name="csrf-token" content="([^"]+)"', r.text)
    if not m:
        raise EMError("cbc: csrf نەدۆزرایەوە")
    jar = {}
    for sc in r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw, "headers") else [r.headers.get("Set-Cookie") or ""]:
        if not sc:
            continue
        kv = sc.split(";")[0]
        k = kv.split("=")[0].strip()
        from urllib.parse import unquote
        jar[k] = unquote(kv.split("=", 1)[1])
    cookie_header = "; ".join(f"{k}={v}" for k, v in jar.items())
    _CBC_STATE["csrf"], _CBC_STATE["cookies"], _CBC_STATE["t"] = m.group(1), cookie_header, time.time()
    return _CBC_STATE["csrf"], _CBC_STATE["cookies"]


def _cbc_headers():
    csrf, cookies = _cbc_session()
    return {
        "User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "X-CSRF-TOKEN": csrf,
        "Referer": CBC_BASE + "/", "Origin": CBC_BASE, "Cookie": cookies,
    }


def _cbc_timestamp(hdrs):
    r = requests.post(CBC_BASE + "/api/get-timestamp",
                      headers={**hdrs, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
                      data={"href": CBC_BASE + "/"}, timeout=25)
    return r.json()["timestamp"]




def _cbc_stream_read(r, hdrs, payload, timeout, messages):
    """#91CB: خوێندنەوەی ستریم — دەقی تەواو"""
    out = ""
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        body = line[6:] if line.startswith("data: ") else (line[3:] if line.startswith("id: ") else None)
        if not body:
            continue
        try:
            j = json.loads(body)
        except Exception:
            continue
        if j.get("code"):
            raise EMError("cbc: " + str(j.get("code")))
        for ch in j.get("choices") or []:
            for part in ((ch.get("content") or {}).get("parts")) or []:
                t = part.get("text") or ""
                out += t
    if not out:
        raise EMError("cbc: وەڵامی بەتاڵ")
    return out

def cbc_chat(messages, model=None, timeout=120):
    """پرسیار بۆ chatbotchatapp — GPT-5 (تەنها مۆدێڵی بێ login) — دەقی تەواو دەگەڕێنێتەوە"""
    hdrs = _cbc_headers()
    timestamp = _cbc_timestamp(hdrs)
    nonce = _cbc_gen_nonce()
    last_user = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            last_user = str(m.get("content", ""))
            break
    s = {"timestamp": timestamp, "nonce": nonce, "messages": last_user}
    acc = "".join(f"{k}{v}" for k, v in s.items())
    acc += "keyToken" + _CBC_KEY_TOKEN + "vv1"
    payload = {
        "id": _cbc_md5(acc), "timestamp": timestamp, "nonce": nonce,
        "messages": messages, "url": CBC_BASE + "/",
    }
    # #91CB: ڕۆتیشن — یەکەم هەوڵ ڕاستەوخۆ، ئەگەر لیمێتی میوان → پرۆکسی
    last_g = None
    px_list = []
    for _pxtry in range(4):
        _px = px_list[_pxtry] if _pxtry < len(px_list) else None
        _kw = {"proxies": {"http": _px, "https": _px}} if _px else {}
        try:
            r = requests.post(CBC_BASE + "/api", headers={**hdrs, "Content-Type": "application/json",
                                                          "Accept": "text/event-stream"},
                              json=payload, timeout=timeout, stream=True, **_kw)
        except Exception:
            if _pxtry == 0:
                px_list = _CBC_PROXY.get("on") and _proxy_get(3) or []
            continue
        if r.status_code == 429:
            raise EMError("cbc: سنووری ڕێژە (429)")
        _hit = False
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            body = line[6:] if line.startswith("data: ") else (line[3:] if line.startswith("id: ") else None)
            if not body:
                continue
            try:
                j0 = json.loads(body)
            except Exception:
                continue
            if j0.get("code") == "dailyChatLimitOfGuest":
                _hit = True
            break
        if not _hit:
            return _cbc_stream_read(r, hdrs, payload, timeout, messages)
        if not px_list:
            px_list = _CBC_PROXY.get("on") and _proxy_get(3) or []
        print(f"[CBC] لیمێتی میوان — پرۆکسی {_pxtry + 2}/4…", flush=True)
    raise EMError("cbc: سنووری ڕۆژانەی میوان")


# ════════════════════════════════════════════════════════════
# ٢.٧) مێشکی rewind.ai — API کراوەی OpenAI-جۆر، بێ کلیل (٢٥٠٠ تۆکن بۆ میوان)
# ════════════════════════════════════════════════════════════

RWD_BASE = "https://api.rewind.ai"
# ناسنامەی میوان = User-Agent — هەر UA یەی نوێ = ٢٥٠٠ تۆکنی نوێ (خۆکارانە دەگۆڕدرێت)
_RWD_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 OPR/112.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]
_RWD_STATE = {"i": 0}
# پشتڕاستکراو — فلاشەکان + بەقوەتەکان (هەموویان تاقیکرانەوە)
_RWD_VERIFIED = [
    # بەقوەتەکان (تاقیکرانەوەی ڕاستەقینە — لە بودجەی ٢٥٠٠ ێکن)
    "deepseek/deepseek-v4-pro",
    "deepseek/deepseek-r1",
    "qwen/qwen3.7-max",
    "qwen/qwen3-max",
    "z-ai/glm-5.3",
    "z-ai/glm-5.2",
    "moonshotai/kimi-k2.6",
    "thinkingmachines/inkling",
    "mistralai/mistral-large",
    "microsoft/phi-4",
    "amazon/nova-pro-v1",
    "inception/mercury-2.5",
    # فلاشە پێشتر پشتڕاستکراوەکان
    "google/gemini-3.8-flash",
    "x-ai/grok-4.3",
    "deepseek/deepseek-v4-flash",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.8-flash",
    "meta-llama/llama-4-maverick",
    "qwen/qwen-2.5-7b-instruct",
]
# وشەکانی مۆدێلی کەم‌خوارەکە (لە بودجەی ٢٥٠٠ تۆکنی میوان)
_RWD_FREE_HINTS = ("flash", "mini", "lite", "nano", "small", "turbo")


def rwd_models_live(timeout=15):
    """لیستی مۆدێلەکانی rewind — تەنها چاتی ئاسایی، بێ batch/alias"""
    r = requests.get(RWD_BASE + "/v1/models", headers={"User-Agent": UA}, timeout=timeout)
    r.raise_for_status()
    out = []
    for m in r.json().get("models", []):
        mid = m.get("id") or ""
        if m.get("type") != "chat":
            continue
        if ":batch" in mid or mid.startswith("~"):
            continue
        out.append(mid)
    return out


def rwd_servers(timeout=15):
    """سێرڤەرەکانی rewind — بەقوەتەکان + فلاشەکان (بە ڕیزبەندی پشتڕاستکراو)"""
    try:
        live = rwd_models_live(timeout)
    except Exception:
        live = []
    chosen = [m for m in _RWD_VERIFIED if not live or m in live]
    if live:
        for mid in live:
            tail = mid.lower().split("/")[-1].split(":")[0]
            segs = tail.split("-")
            if any(any(s == h or s.startswith(h) for h in _RWD_FREE_HINTS) for s in segs) and mid not in chosen:
                chosen.append(mid)
            if len(chosen) >= 32:
                break
    return [{"id": mid, "name": mid, "model_id": mid, "kind": "rwd"} for mid in chosen]


def _rwd_session(timeout=15):
    """سێشن بە UA ی ئێستا — GET ی سەرەتا کوکییەی anon_token دەگرێت"""
    s = requests.Session()
    ua = _RWD_UAS[_RWD_STATE["i"] % len(_RWD_UAS)]
    s.headers["User-Agent"] = ua
    try:
        s.get(RWD_BASE + "/v1/models", headers={"User-Agent": ua}, timeout=timeout)
    except Exception:
        pass
    return s


def _rwd_next_identity():
    """گۆڕینی ناسنامە — UA ی داهاتوو = بودجەی تازەی ٢٥٠٠ تۆکن"""
    _RWD_STATE["i"] = (_RWD_STATE["i"] + 1) % len(_RWD_UAS)


def rwd_chat(model_id, messages, timeout=110):
    """پرسیار بۆ rewind — خۆکارانە ناسنامە دەگۆڕێت کاتێک تۆکن تەواو دەبێت"""
    for attempt in (0, 1):
        s = _rwd_session()
        ua = s.headers["User-Agent"]
        try:
            r = s.post(RWD_BASE + "/v1/chat/completions/",
                       headers={"User-Agent": ua, "Content-Type": "application/json"},
                       json={"model": model_id, "messages": messages}, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                _rwd_next_identity()
                continue
            raise EMError(f"rwd: {str(e)[:60]}")
        if r.status_code == 400:
            # ناسنامەی ئەم UA یە بەکارهاتووە — گۆڕی بدەر بۆ ئەوی تر
            _rwd_next_identity()
            continue
        if r.status_code == 429:
            raise EMError("rwd: ڕێژە زۆرە — چاوەڕێ بکە")
        try:
            j = r.json()
        except Exception:
            _rwd_next_identity()
            continue
        err = j.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "")
            if code == "INSUFFICIENT_TOKENS":
                # تۆکنەکانی ئەم ناسنامەیە تەواو بوون — UA ی نوێ = ٢٥٠٠ی نوێ
                if attempt == 0:
                    _rwd_next_identity()
                    continue
                raise EMError("rwd: هەموو ناسنامەکان تەواو بوون")
            raise EMError("rwd: " + (code or str(err)[:50])[:60])
        ch = (j.get("choices") or [{}])[0]
        ans = ((ch.get("message") or {}).get("content") or "").strip()
        if ans:
            return ans
        _rwd_next_identity()
    raise EMError("rwd: نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.٩) مێشکی aichatting.net — gpt-5.6/claude-opus-5/grok-4.6 (خۆکار)
#      visitorId = RSA-encrypted fingerprint — هەر ناسنامەیەک = کواتی نوێ
# ════════════════════════════════════════════════════════════

ACT_BASE = "https://aga-api.aichatting.net"
ACT_PUBKEY = (
    "-----BEGIN PUBLIC KEY-----\n"
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDCAdf/EyIbLBxjGqmh7qLU6/CPCzru+75+82OSPZ+nf4BFvg88drpZ6KigNW0J8TNgxe6Yms1irCZNVDyu+RXsl4y/7c2KOHc4OGTzHB5fUMiMasFUvcEs2P70e6yA/sKHZfBLG1XPhlb84Ibs3nhD3W5e2SuC+4EuVkaqzN08LQIDAQAB\n"
    "-----END PUBLIC KEY-----"
)
# ڕاستکراوە: API ەکەیان هەر ناوێک قبوڵ دەکات بەڵام هەمووی فەڵباکە بۆ یەک مۆدێڵ
# (پشکنین: ناوی درۆش وەڵام دەداتەوە + هەموو ناوەکان «made by OpenAI» دەڵێن)
# تەنها ناوی ڕەسمی ڕاییگەی ماڵپەڕەکە دەمێنێتەوە — gpt-5.6-luna
ACT_MODELS = ["gpt-5.6-luna"]
ACT_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
]
_ACT_STATE = {"i": 0}


def act_servers():
    """سێرڤەرەکانی aichatting — هەموو مۆدێلە پشتڕاستکراوەکان"""
    return [{"id": "act-" + m, "name": m, "model_id": m, "kind": "act"} for m in ACT_MODELS]


def _act_identity():
    """ناسنامەی نوێ — visitorId نوێ = RSA encrypt
    → (visitorId, vTokenی خاو base64, کوکی percent-encoded)"""
    import urllib.parse as _up
    visitor_id = hashlib.md5(f"fp{time.time()}{random.random()}".encode()).hexdigest()
    from cryptography.hazmat.primitives import serialization as _s, asymmetric as _a
    try:
        pub = _s.load_pem_public_key(ACT_PUBKEY.encode())
        enc = pub.encrypt(visitor_id.encode(), _a.padding.PKCS1v15())
        raw = base64.b64encode(enc).decode()
    except Exception:
        raw = visitor_id
    return visitor_id, raw, _up.quote(raw, safe="")


def act_chat(model_id, messages, timeout=110):
    """چات بۆ aichatting — SSE، ناسنامەی خۆکار (کوات تەواو بوو → نوێی دەکاتەوە)"""
    for attempt in (0, 1):
        visitor_id, raw_token, cookie_token = _act_identity()
        ua = ACT_UAS[_ACT_STATE["i"] % len(ACT_UAS)]
        h = {
            "User-Agent": ua, "source": "web", "lang": "en",
            "Content-Type": "application/json",
            "Cookie": "aichatting.website.visitorId=" + cookie_token,
            "vToken": raw_token,
            "Origin": "https://www.aichatting.net",
            "Referer": "https://www.aichatting.net/free-chatgpt/",
            "Accept": "text/event-stream,application/json",
        }
        msgs = _sys_keep([{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]}
                            for m in messages if m.get("role") in ("user", "assistant", "system")], 19)
        payload = {"spaceHandle": True, "roleId": None, "messages": msgs,
                   "conversationId": None, "model": model_id}
        try:
            r = requests.post(ACT_BASE + "/aigc/chat/v2/askai/stream",
                              headers=h, json=payload, timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"act: {str(e)[:60]}")
        if r.status_code == 401 and attempt == 0:
            continue  # ناسنامەی نوێ
        if r.status_code != 200:
            if attempt == 0:
                continue
            raise EMError(f"act: {r.status_code}")
        # SSE — data: بەشەکان، "--@DONE@--" کۆتایی (UTF-8 — r.text عەرەبی تێکدەدات)
        # ئاماژەکانی ئەوان: "-=- --" = بۆشایی، "-=-n--" = هێڵی نوێ (لە c3.js)
        out = []
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data:"):
                part = line[5:]
                if part.startswith(" "):
                    part = part[1:]
                part = part.rstrip("\r")
                if part and part != "--@DONE@--":
                    out.append(part)
        ans = "".join(out).replace("-=- --", " ").replace("-=-n--", "\n").strip()
        if ans:
            return ans
        if attempt == 0:
            continue
    raise EMError("act: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٠) flatai.org — GLM (Z.ai) بێ تۆمار — کواتی ڕۆژانە بۆ هەر IP
#      session → history(save) → my_chatbot (SSE)
# ════════════════════════════════════════════════════════════

FLA_AJAX = "https://flatai.org/wp-admin/admin-ajax.php"


def fla_servers():
    return [{"id": "flatai-glm", "name": "GLM (flatai)", "model_id": "glm", "kind": "fla"}]


def fla_chat(messages, timeout=110):
    """چاتی flatai — یەک مۆدێڵی سێرڤەری (GLM)؛ کواتی ڕۆژانە تەواو → EMError"""
    import uuid as _uuid
    s = requests.Session()
    s.headers.update({
        "User-Agent": _pick_ua(ACT_UAS),
        "Origin": "https://flatai.org",
        "Referer": "https://flatai.org/free-ai-chatbot-no-registration/",
    })

    def F(**kv):
        return {k: (None, v) for k, v in kv.items()}

    try:
        s.get("https://flatai.org/free-ai-chatbot-no-registration/", timeout=(15, 30))
        r = s.post(FLA_AJAX, files=F(action="chatbot2_session"), timeout=(15, 30))
        sess = r.json()["data"]
        r = s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"], operation="load"),
                   timeout=(15, 30))
        ld = r.json()["data"]
        chat_id = str(_uuid.uuid4())
        chats = json.loads(ld["values"].get("allChats", "{}"))
        chats[chat_id] = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
                          "title": "New conversation", "messages": []}
        s.post(FLA_AJAX, files=F(action="chatbot2_history", nonce=sess["nonce"],
                                 history_nonce=sess["history_nonce"], operation="save",
                                 values=json.dumps({**ld["values"], "allChats": json.dumps(chats)}),
                                 revision=str(ld["revision"])), timeout=(15, 30))
        msgs = _sys_keep([{"role": m["role"], "content": m["content"]}
                            for m in messages if m.get("role") in ("user", "assistant", "system")], 19)
        sys_txt = ""
        for _i, _m in enumerate(msgs):  # #94U25: system لە هەر شوێنێک بێت بدۆزەرەوە
            if _m.get("role") == "system" and _m.get("content"):
                sys_txt = msgs.pop(_i)["content"]
                break
        r = s.post(FLA_AJAX, files=F(action="my_chatbot", nonce=sess["nonce"],
                                     history_nonce=sess["history_nonce"],
                                     request_id=str(_uuid.uuid4()), chat_id=chat_id,
                                     messages=json.dumps(msgs),
                                     system_message_content=sys_txt),
                   timeout=(15, timeout))
        if r.status_code == 429:
            raise EMError("fla: کواتی ڕۆژانە تەواو (IP)")
        ct = r.headers.get("content-type", "")
        if r.status_code != 200 or "event-stream" not in ct:
            raise EMError(f"fla: {r.status_code}")
        text = ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if line.startswith("data: "):
                try:
                    d = json.loads(line[6:])
                    if isinstance(d, dict) and isinstance(d.get("text"), str) and d["text"]:
                        text = d["text"]  # کۆتا (done) دەباتەوە
                except Exception:
                    pass
        if text.strip():
            return text.strip()
        raise EMError("fla: وەڵام نەگەڕایەوە")
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"fla: {str(e)[:60]}")


# ════════════════════════════════════════════════════════════
# ٢.١١) zerotwo.ai — gemini-2.5-flash-lite (ڕاییگە: ١٥ نامە/ڕۆژ/هەژمار)
#      supabase signup (mail.tm) → csrf → /api/ai/chat/stream
# ════════════════════════════════════════════════════════════

Z02_API = "https://api.zerotwo.ai"
Z02_SB = "https://jdbcevjbqaoxrxxwqwux.supabase.co"
Z02_KEY = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
           "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkYmNldmpicWFveHJ4eHdxd3V4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNDcyMzUsImV4cCI6MjA3MzgyMzIzNX0."
           "UcUJUjMocwijFTtYFKYuTgIODYWc4uxDByu2tI6XGQg")

_Z02_CACHE = {"token": None, "exp": 0.0}


def z02_servers():
    return [
        {"id": "z02-gemini-flash-lite", "name": "Gemini Flash Lite (ZeroTwo)",
         "model_id": "gemini-2.5-flash-lite", "kind": "z02"},
        {"id": "z02-grok-4.1-fast", "name": "Grok 4.1 Fast (ZeroTwo)",
         "model_id": "grok-4-1-fast-non-reasoning", "kind": "z02"},
        {"id": "z02-gpt-5.6-luna", "name": "GPT 5.6 Luna (ZeroTwo)",
         "model_id": "gpt-5.6-luna", "kind": "z02"},
        {"id": "z02-venice-roleplay", "name": "Venice Roleplay (ZeroTwo)",
         "model_id": "venice-uncensored-role-play", "kind": "z02"},
    ]


# model_id → provider ی zerotwo
_Z02_PROVIDERS = {
    "gemini-2.5-flash-lite": "gemini",
    "grok-4-1-fast-non-reasoning": "xai",
    "gpt-5.6-luna": "openai",
    "venice-uncensored-role-play": "venice",
}


def _z02_new_account():
    """هەژماری نوێ: mail.tm → supabase signup → confirm → access_token"""
    import uuid as _uuid
    ms = requests.Session()
    ms.headers.update({"User-Agent": ACT_UAS[random.randrange(len(ACT_UAS))]})
    r = ms.get("https://api.mail.tm/domains", timeout=(15, 30))
    dom = r.json()["hydra:member"][0]["domain"]
    email = f"z02x{int(time.time())}{random.randrange(100, 999)}@{dom}"
    pw = "Xk9!mQ2#vLp8$zRw"
    r = ms.post("https://api.mail.tm/accounts", json={"address": email, "password": pw}, timeout=(15, 30))
    if r.status_code not in (200, 201):
        raise EMError(f"z02 mail: {r.status_code}")
    r = ms.post("https://api.mail.tm/token", json={"address": email, "password": pw}, timeout=(15, 30))
    mtok = r.json()["token"]
    h = {"apikey": Z02_KEY, "Authorization": f"Bearer {Z02_KEY}", "Content-Type": "application/json"}
    r = requests.post(f"{Z02_SB}/auth/v1/signup", json={"email": email, "password": pw},
                      headers=h, timeout=(15, 40))
    if r.status_code != 200:
        raise EMError(f"z02 signup: {r.status_code}")
    # چاوەڕوانی نامەی confirm (SendGrid — quoted-printable decode)
    link = None
    import quopri as _qp
    for _ in range(8):
        time.sleep(3.5)
        try:
            r = ms.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {mtok}"},
                       timeout=(15, 30))
            msgs = r.json().get("hydra:member", [])
            if not msgs:
                continue
            mid = msgs[0]["id"]
            r = ms.get(f"https://api.mail.tm/messages/{mid}",
                       headers={"Authorization": f"Bearer {mtok}"}, timeout=(15, 30))
            d = r.json()
            html = d.get("html")
            html = html[0] if isinstance(html, list) else str(html)
            try:
                html = _qp.decodestring(html.encode()).decode("utf-8", "replace")
            except Exception:
                pass
            m = re.search(r'https://u[0-9a-z]+\.ct\.sendgrid\.net/ls/click\?[^"\'\s<>]+', html)
            if m:
                link = m.group(0)
                break
        except Exception:
            continue
    if not link:
        raise EMError("z02: نامەی confirm نەگەیشت")
    r = requests.get(link, allow_redirects=True, timeout=(15, 40),
                     headers={"User-Agent": ACT_UAS[0]})
    m = re.search(r'access_token=(eyJ[A-Za-z0-9_.-]+)', r.url)
    if not m:
        raise EMError("z02: access_token لە ڕیدایرێکت نییە")
    return m.group(1)


def _z02_token():
    """access_token ی زیندوو — ئەگەر کۆن بوو یان مردوو بوو نوێی دروست دەکات"""
    if _Z02_CACHE["token"] and time.time() < _Z02_CACHE["exp"]:
        return _Z02_CACHE["token"]
    tok = _z02_new_account()
    _Z02_CACHE["token"] = tok
    _Z02_CACHE["exp"] = time.time() + 3300  # JWT = 1 کاتژمێر
    return tok


def z02_chat(messages, model_id="gemini-2.5-flash-lite", timeout=110):
    """چاتی zerotwo — ٤ مۆدێڵی ڕاییگە؛ ١٥ نامە/ڕۆژ → هەژماری نوێ خۆکار"""
    provider = _Z02_PROVIDERS.get(model_id, "gemini")
    try:
        token = _z02_token()
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"z02: {str(e)[:60]}")
    h = {
        "User-Agent": _pick_ua(ACT_UAS),
        "Origin": "https://app.zerotwo.ai", "Referer": "https://app.zerotwo.ai/",
        "X-ZeroTwo-Platform": "web", "Content-Type": "application/json",
    }
    msgs = _sys_keep([{"role": m["role"], "content": m["content"]}
                        for m in messages if m.get("role") in ("user", "assistant", "system")], 19)
    for attempt in (0, 1):
        if attempt == 1:
            try:
                token = _z02_new_account()
                _Z02_CACHE["token"], _Z02_CACHE["exp"] = token, time.time() + 3300
            except Exception as e:
                raise EMError(f"z02 هەژمار: {str(e)[:50]}")
        try:
            s = requests.Session()
            s.headers.update(h)
            r = s.get(Z02_API + "/api/auth/csrf-token", timeout=(15, 30))
            tok = r.json()["token"]
            r = s.post(Z02_API + "/api/ai/chat/stream",
                       headers={**h, "X-CSRF-Token": tok, "Authorization": f"Bearer {token}"},
                       json={"messages": msgs, "provider": provider, "model": model_id},
                       timeout=(15, timeout))
        except Exception as e:
            if attempt == 0:
                continue
            raise EMError(f"z02: {str(e)[:60]}")
        text, err = [], ""
        for line in r.content.decode("utf-8", "replace").splitlines():
            if not line.startswith("data: "):
                continue
            try:
                d = json.loads(line[6:])
            except Exception:
                continue
            if d.get("entity") == "message.content" and d.get("status") == "delta":
                t = (d.get("v", {}).get("delta") or {}).get("text")
                if t:
                    text.append(t)
            if d.get("status") == "error":
                v = d.get("v", {})
                err = v.get("code") or v.get("message") or "error"
        ans = "".join(text).strip()
        if ans:
            return ans
        if "LIMIT" in err.upper() or "429" in str(err):
            if attempt == 0:
                continue  # هەژماری نوێ
            raise EMError("z02: کواتی ڕۆژانە تەواو")
        if attempt == 0:
            continue
        raise EMError(f"z02: {str(err)[:60] or 'وەڵام نەگەڕایەوە'}")
    raise EMError("z02: وەڵام نەگەڕایەوە")


# ════════════════════════════════════════════════════════════
# ٢.١٢) quillbot.com AI Chat — gpt-4.1-mini بێ تۆمار
#      POST /api/ai-chat/chat/conversation/{uuid} — NDJSON stream
#      کوات: ١ نامە/~٢٠ چرکە (دوای ناوەستێت بەردەوام دەبێتەوە)
# ════════════════════════════════════════════════════════════

QB_URL = "https://quillbot.com/api/ai-chat/chat/conversation/"


def qb_servers():
    return [{"id": "qb-gpt-4.1-mini", "name": "GPT 4.1 Mini (QuillBot)",
             "model_id": "gpt-4.1-mini", "kind": "qb"}]


def qb_chat(messages, timeout=60):  # #94U19: 110→60
    """چاتی quillbot — مێژووی وەک یەک نامەی یەکگیراو؛ NDJSON: type=content/usage"""
    import uuid as _uuid
    # مێژوو بۆ یەک پرسیار کۆبکەوە (سیستەم لە سەرەتا + دوا نامەی بەکارهێنەر)
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    body = {"message": {"content": user_txt, "files": []}, "context": {}, "tools": {},
            "origin": {"name": "ai-chat.chat", "url": "https://quillbot.com"}}
    try:
        r = requests.post(QB_URL + str(_uuid.uuid4()), json=body, timeout=(15, timeout),
                          headers={"User-Agent": _pick_ua(ACT_UAS),
                                   "Origin": "https://quillbot.com",
                                   "Referer": "https://quillbot.com/ai-chat",
                                   "Accept": "text/event-stream",
                                   "platform-type": "webapp"}, stream=True)
    except Exception as e:
        raise EMError(f"qb: {str(e)[:60]}")
    if r.status_code == 403:
        # #94U19 REVIVE: CF چەلەنج → دووبارە بە پرۆکسی (تا ٣)
        try:
            r.close()
        except Exception:
            pass
        for _px in _proxy_get(3):
            try:
                _r2 = requests.post(QB_URL + str(_uuid.uuid4()), json=body, timeout=(15, 60),
                                    headers={"User-Agent": _pick_ua(ACT_UAS),
                                             "Origin": "https://quillbot.com",
                                             "Referer": "https://quillbot.com/ai-chat",
                                             "Accept": "text/event-stream",
                                             "platform-type": "webapp"},
                                    proxies={"http": _px, "https": _px}, stream=True)
                if _r2.status_code == 200:
                    r = _r2
                    print("[QB] ✅ بە پرۆکسی تێپەڕی", flush=True)
                    break
            except Exception:
                continue
    if r.status_code == 403:
        raise EMError("qb: چەلەنجەی Cloudflare (ڕێژە)")
    if r.status_code != 200:
        raise EMError(f"qb: {r.status_code}")
    text = []
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") == "content":
            c = d.get("content", "")
            if c:
                text.append(c)
        elif d.get("type") == "error":
            raise EMError(f"qb: {str(d.get('message', 'error'))[:60]}")
    ans = "".join(text).strip()
    ans = re.sub(r"</?editor-content[^>]*>", "", ans).strip()
    if ans:
        return ans
    raise EMError("qb: وەڵام نەگەڕایەوە")



# ════════════════════════════════════════════════════════════
# ٢.١٣) duck.ai (DuckDuckGo AI) — ٥ مۆدێڵی خۆڕایی بێ تۆمار
#      چەلەنجەی JS (x-vqd-hash-1) لە V8 (py-mini-racer) + DOM stubs چارە دەکرێت
#      لیمتی IP: هەندێجە ٤١٨ → فەڵباکی زنجیرە هەڵی دەگرێت
# ════════════════════════════════════════════════════════════

DUCK_STUBS_JS = r'''var __ua = __DDG_REAL_UA__;
var __HTML_LOOKUP = __DDG_HTML_LOOKUP__;

function __makeHtmlElement(tag) {
  var state = { _innerHTML: '', _qsaCount: 0, _cssText: '' };
  var styleObj = {};
  Object.defineProperty(styleObj, 'cssText', {
    get: function(){ return state._cssText; },
    set: function(v){ state._cssText = String(v||''); },
    enumerable: true, configurable: true
  });
  var el = {
    tagName: String(tag).toUpperCase(),
    nodeName: String(tag).toUpperCase(),
    nodeType: 1,
    children: [], childNodes: [], classList: [],
    style: styleObj, dataset: {},
    offsetWidth: 100, offsetHeight: 20, scrollHeight: 20,
    offsetTop: 100, offsetLeft: 0, offsetParent: null,
    clientWidth: 100, clientHeight: 20,
    getBoundingClientRect: function(){
      return { width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120, x: 0, y: 100 };
    },
    getClientRects: function(){
      return [{ width: 100, height: 20, top: 100, left: 0, right: 100, bottom: 120 }];
    },
    setAttribute: function(){}, removeAttribute: function(){},
    getAttribute: function(a){ if(a==='srcdoc') return state._srcdoc||''; return null; },
    hasAttribute: function(){ return false; },
    appendChild: function(c){ return c; },
    removeChild: function(c){ return c; },
    addEventListener: function(){}, removeEventListener: function(){},
    querySelector: function(){ return null; },
    querySelectorAll: function(s){
      if (s === '*') {
        var arr = []; arr.length = state._qsaCount; return arr;
      }
      return [];
    },
    cloneNode: function(){ return __makeHtmlElement(tag); },
    _getState: function(){ return state; }
  };
  Object.defineProperty(el, 'innerHTML', {
    get: function(){ return state._innerHTML; },
    set: function(v){
      var key = String(v);
      var entry = __HTML_LOOKUP && __HTML_LOOKUP[key];
      if (entry) { state._innerHTML = String(entry.html); state._qsaCount = entry.count|0; }
      else { state._innerHTML = key; state._qsaCount = 0; }
    },
    enumerable: true, configurable: true
  });
  Object.defineProperty(el, 'outerHTML', { get: function(){ return '<' + tag + '>' + state._innerHTML + '</' + tag + '>'; }, enumerable: true });
  Object.defineProperty(el, 'srcdoc', { get: function(){ return state._srcdoc||''; }, set: function(v){ state._srcdoc = String(v); }, enumerable: true });
  Object.defineProperty(el, 'contentWindow', { get: function(){
    var w = {};
    w.document = __ifDoc;
    w.Proxy = Proxy;
    w.self = w;
    w.top = w;
    w.parent = w;
    w.window = w;
    return w;
  }, enumerable: true });
  Object.defineProperty(el, 'contentDocument', { get: function(){ return __ifDoc; }, enumerable: true });
  return el;
}

function __mkObj(name, base) {
  base = base || {};
  return new Proxy(base, {
    get: function(t, k) {
      if (k in t) return t[k];
      if (k === Symbol.toPrimitive) return function(){ return ''; };
      if (k === Symbol.iterator) return undefined;
      if (k === 'then' || k === 'catch' || k === 'finally') return undefined;
      if (k === 'constructor') return Object;
      if (k === 'toString' || k === 'valueOf') return function(){ return '[object ' + name + ']'; };
      if (k === 'length') return 0;
      if (k === 'nodeType') return 1;
      if (k === 'tagName' || k === 'nodeName') return 'DIV';
      if (k === 'innerHTML' || k === 'outerHTML' || k === 'textContent' || k === 'innerText' || k === 'value') return '';
      if (k === 'children' || k === 'childNodes' || k === 'classList') return [];
      if (typeof k === 'string' && (k.indexOf('get') === 0 || k.indexOf('query') === 0 || k.indexOf('find') === 0)) {
        return function(arg){
          if (k === 'querySelectorAll' || k === 'getElementsByTagName' || k === 'getElementsByClassName') return [];
          return null;
        };
      }
      return function(){ return __mkObj(name + '.' + String(k)); };
    },
    has: function(t, k){ return k in t; },
    set: function(t, k, v){ t[k] = v; return true; }
  });
}

var __ifMeta = __mkObj('meta', {
  getAttribute: function(a){ return a==='content' ? "default-src 'none'; script-src 'unsafe-inline';" : null; },
  hasAttribute: function(a){ return a==='content'; },
  tagName: 'META', nodeName: 'META'
});
var __ifDoc;
__ifDoc = __mkObj('iframeDoc', {
  querySelector: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    if (s === 'meta') return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    if (s === 'meta') return [__ifMeta];
    return [];
  },
  getElementsByTagName: function(t){ return t && t.toLowerCase()==='meta' ? [__ifMeta] : []; },
  body: __mkObj('iframeBody', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  head: __mkObj('iframeHead', {
    querySelector: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? __ifMeta : null; },
    querySelectorAll: function(s){ return s && s.indexOf('Content-Security-Policy')!==-1 ? [__ifMeta] : []; },
    appendChild: function(){}, removeChild: function(){}
  }),
  documentElement: __mkObj('iframeRoot'),
  createElement: function(){ return __mkObj('elem', {setAttribute:function(){}, appendChild:function(){}, removeChild:function(){}, getAttribute:function(){return null;}, hasAttribute:function(){return false;}}); },
  cookie: '', readyState: 'complete'
});

var __iframeEl = __mkObj('iframe', {
  contentDocument: __ifDoc,
  contentWindow: __mkObj('iframeWin', { document: __ifDoc, top: undefined, parent: undefined }),
  document: __ifDoc,
  getAttribute: function(a){
    if (a==='sandbox') return 'allow-scripts allow-same-origin';
    if (a==='srcdoc') return '';
    if (a==='id') return 'jsa';
    return null;
  },
  hasAttribute: function(a){ return a==='sandbox'||a==='id'; },
  tagName: 'IFRAME', nodeName: 'IFRAME', id: 'jsa'
});

var document = __mkObj('document', {
  querySelector: function(s){
    if (s === '#jsa') return __iframeEl;
    if (s && s.indexOf('Content-Security-Policy') !== -1) return __ifMeta;
    return null;
  },
  querySelectorAll: function(s){
    if (s === '#jsa') return [__iframeEl];
    if (s && s.indexOf('Content-Security-Policy') !== -1) return [__ifMeta];
    return [];
  },
  getElementById: function(id){ return id==='jsa' ? __iframeEl : null; },
  getElementsByTagName: function(t){ if(t&&t.toLowerCase()==='iframe') return [__iframeEl]; return []; },
  getElementsByClassName: function(){ return []; },
  body: __mkObj('body', {appendChild:function(){}, removeChild:function(){}, querySelector:function(s){return s==='#jsa'?__iframeEl:null;}, querySelectorAll:function(s){return s==='#jsa'?[__iframeEl]:[];}}),
  head: __mkObj('head', {appendChild:function(){}, removeChild:function(){}, querySelector:function(){return null;}, querySelectorAll:function(){return [];}}),
  documentElement: __mkObj('root'),
  createElement: function(tag){ return __makeHtmlElement(tag||'div'); },
  createTextNode: function(t){ return {nodeType:3, nodeValue:String(t||''), textContent:String(t||'')}; },
  cookie: '', readyState: 'complete', title: '',
  addEventListener: function(){}, removeEventListener: function(){}
});

var window;
window = __mkObj('window', {
  document: document,
  __DDG_BE_VERSION__: 1, __DDG_FE_CHAT_HASH__: 1,
  navigator: __mkObj('navigator', { userAgent: __ua, webdriver: false, language: 'en-US', languages: ['en-US','en'], platform: 'MacIntel', vendor: 'Apple Computer, Inc.', appVersion: '5.0', cookieEnabled: true, onLine: true, hardwareConcurrency: 8, deviceMemory: 8 }),
  innerWidth: 1280, innerHeight: 800, outerWidth: 1280, outerHeight: 800, devicePixelRatio: 1,
  screen: __mkObj('screen', { width:1920, height:1080, availWidth:1920, availHeight:1080, colorDepth:24, pixelDepth:24 }),
  location: __mkObj('location', { href:'https://duckduckgo.com/', origin:'https://duckduckgo.com', host:'duckduckgo.com', hostname:'duckduckgo.com', protocol:'https:', pathname:'/', search:'', hash:'', port:'' }),
  performance: __mkObj('perf', { now: function(){ return 0; }, timeOrigin: 0 }),
  history: __mkObj('history', { length: 1, state: null }),
  localStorage: __mkObj('ls', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  sessionStorage: __mkObj('ss', { getItem:function(){return null;}, setItem:function(){}, removeItem:function(){}, clear:function(){}, length:0, key:function(){return null;} }),
  addEventListener: function(){}, removeEventListener: function(){}, dispatchEvent: function(){return true;},
  getComputedStyle: function(el){
    var css = (el && el.style && el.style.cssText) || '';
    return {
      getPropertyValue: function(p){
        var m = css.match(new RegExp(p + '\\s*:\\s*([^;]+)', 'i'));
        if (m) return m[1].trim();
        if (p === 'display') return 'block';
        return '';
      },
      display: (css.match(/display\s*:\s*([^;]+)/i)||[])[1]||'block'
    };
  },
  setTimeout: function(fn){ try{fn();}catch(e){} return 0; }, clearTimeout: function(){},
  setInterval: function(){ return 0; }, clearInterval: function(){},
  requestAnimationFrame: function(fn){ try{fn();}catch(e){} return 0; }, cancelAnimationFrame: function(){},
  matchMedia: function(){ return __mkObj('mq', {matches:false, media:'', addListener:function(){}, removeListener:function(){}, addEventListener:function(){}, removeEventListener:function(){}}); },
  hasOwnProperty: function(k){
    if (k==='__DDG_BE_VERSION__'||k==='__DDG_FE_CHAT_HASH__') return true;
    return Object.prototype.hasOwnProperty.call(this,k);
  },
  alert: function(){}, confirm: function(){return true;}, prompt: function(){return '';},
  open: function(){return null;}, close: function(){}, focus: function(){}, blur: function(){}
});
window.top = window; window.self = window; window.window = window; window.parent = window; window.globalThis = window;
var top = window, self = window, parent = window;
var navigator = window.navigator;
var location = window.location;
var screen = window.screen;
var performance = window.performance;
var history = window.history;
var localStorage = window.localStorage;
var sessionStorage = window.sessionStorage;
var getComputedStyle = function(el){ return window.getComputedStyle(el); };
var __R = null, __E = null;
function __HTMLClass(name){ var c = function(){}; c.prototype = __mkObj(name+'.proto'); return c; }
var HTMLElement = __HTMLClass('HTMLElement');
var HTMLDivElement = __HTMLClass('HTMLDivElement');
var HTMLIFrameElement = __HTMLClass('HTMLIFrameElement');
var HTMLDocument = __HTMLClass('HTMLDocument');
var Document = __HTMLClass('Document');
var Element = __HTMLClass('Element');
var Node = __HTMLClass('Node');
var Window = __HTMLClass('Window');
var Event = __HTMLClass('Event');
var MouseEvent = __HTMLClass('MouseEvent');
var KeyboardEvent = __HTMLClass('KeyboardEvent');
var TouchEvent = __HTMLClass('TouchEvent');
var XMLHttpRequest = __HTMLClass('XMLHttpRequest');
var WebSocket = __HTMLClass('WebSocket');
var Image = __HTMLClass('Image');
var FormData = __HTMLClass('FormData');
var Blob = __HTMLClass('Blob');
var File = __HTMLClass('File');
var FileReader = __HTMLClass('FileReader');
var URL = __HTMLClass('URL');
var URLSearchParams = __HTMLClass('URLSearchParams');
var Headers = __HTMLClass('Headers');
var Request = __HTMLClass('Request');
var Response = __HTMLClass('Response');
var fetch = function(){ return Promise.resolve(__mkObj('resp', {ok:true, status:200, json:function(){return Promise.resolve({});}, text:function(){return Promise.resolve('');}})); };
'''

DUCK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
DUCK_FE_VERSION = "serp_20260917_083005_ET-742796f26a61a81dbee67db3e7dd403a0e16294e"
DUCK_SESSION = None
DUCK_WARMED = [False]
DUCK_LOCK = threading.Lock()
DUCK_JWK = [None]


def duck_servers():
    return [
        {"id": "duck-gpt-5.4-mini", "name": "GPT 5.4 Mini (Duck)",
         "model_id": "gpt-5.4-mini", "kind": "duck"},
        {"id": "duck-claude-haiku-4-5", "name": "Claude Haiku 4.5 (Duck)",
         "model_id": "claude-haiku-4-5", "kind": "duck"},
        {"id": "duck-mistral-small", "name": "Mistral Small (Duck)",
         "model_id": "mistral-small-2603", "kind": "duck"},
        {"id": "duck-gpt-oss-120b", "name": "GPT OSS 120B (Duck)",
         "model_id": "tinfoil/gpt-oss-120b", "kind": "duck"},
        {"id": "duck-gemma-4-31b", "name": "Gemma 4 31B (Duck)",
         "model_id": "tinfoil/gemma4-31b", "kind": "duck"},
    ]


def _duck_b64u(b):
    import base64 as _b
    return _b.urlsafe_b64encode(b).decode().rstrip("=")


def _duck_jwk():
    if DUCK_JWK[0] is None:
        from cryptography.hazmat.primitives.asymmetric import rsa
        k = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        n = k.public_key().public_numbers().n
        nb = n.to_bytes((n.bit_length() + 7) // 8, "big")
        DUCK_JWK[0] = {"alg": "RSA-OAEP-256", "e": _duck_b64u((65537).to_bytes(3, "big")),
                       "ext": True, "key_ops": ["encrypt"], "kty": "RSA",
                       "n": _duck_b64u(nb), "use": "enc"}
    return DUCK_JWK[0]


def _duck_session():
    global DUCK_SESSION
    if DUCK_SESSION is None:
        DUCK_SESSION = requests.Session()
        DUCK_SESSION.headers.update({
            "User-Agent": DUCK_UA, "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://duck.ai/", "Origin": "https://duck.ai",
            "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"})
    return DUCK_SESSION


def _duck_b64sha(s):
    import base64 as _b, hashlib as _h
    return _b.b64encode(_h.sha256(s.encode("utf-8")).digest()).decode("ascii")


def _duck_solve(challenge_b64):
    """چەلەنجەی JS ی سێرڤەر لە V8 چارە دەکات + wrapper ی FE (origin/stack/duration)"""
    import base64 as _b, json as _j, random as _r
    from py_mini_racer import MiniRacer
    js = _b.b64decode(challenge_b64).decode("utf-8", errors="replace")
    with DUCK_LOCK:
        ctx = MiniRacer()
        try:
            ctx.eval(DUCK_STUBS_JS.replace("__DDG_REAL_UA__", _j.dumps(DUCK_UA))
                                    .replace("__DDG_HTML_LOOKUP__", "{}"))
            ctx.eval("(%s).then(function(v){__R=v;}).catch(function(e){__E=String((e&&e.stack)||e);});" % js)
            for _ in range(100):
                if ctx.execute("__R !== null || __E !== null"):
                    break
                time.sleep(0.02)
            err = ctx.execute("__E")
            if err:
                raise RuntimeError(str(err)[:120])
            res = ctx.execute("__R")
        finally:
            try:
                del ctx
            except Exception:
                pass
    if not isinstance(res, dict) or not res.get("client_hashes"):
        raise RuntimeError("duck: چەلەنجە بەتاڵ")
    ch = list(res["client_hashes"])
    ch[0] = DUCK_UA
    res["client_hashes"] = [_duck_b64sha(x) for x in ch]
    res.setdefault("meta", {})
    res["meta"]["origin"] = "https://duck.ai"
    res["meta"]["stack"] = "Error\n    at https://duck.ai/dist/duckai-dist/entry.duckai.js:2:123456"
    res["meta"]["duration"] = str(_r.randint(40, 250))
    return _b.b64encode(_j.dumps(res, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_signals():
    import base64 as _b, json as _j, random as _r
    now = int(time.time() * 1000)
    t = _r.randint(80, 180)
    ev = [{"name": "onboarding_impression_1", "delta": t}]
    t += _r.randint(120, 260)
    ev.append({"name": "onboarding_impression_2", "delta": t})
    t += _r.randint(200, 500)
    ev.append({"name": "startNewChat", "delta": t})
    for _ in range(_r.randint(6, 14)):
        t += _r.randint(40, 180)
        ev.append({"name": "user_input", "delta": t})
    t += _r.randint(120, 350)
    ev.append({"name": "user_submit", "delta": t})
    p = {"start": now - 8000, "events": ev, "end": t + _r.randint(20, 90)}
    return _b.b64encode(_j.dumps(p, separators=(",", ":")).encode("utf-8")).decode("ascii")


def _duck_warm():
    if DUCK_WARMED[0]:
        return
    with DUCK_LOCK:
        if DUCK_WARMED[0]:
            return
        try:
            _duck_session().get("https://duck.ai/", headers={
                "Accept": "text/html", "Upgrade-Insecure-Requests": "1"}, timeout=(15, 20))
        except Exception:
            pass
        DUCK_WARMED[0] = True


def _duck_attempt(model_id, msgs, timeout):
    import json as _j, random as _r, uuid as _u
    s = _duck_session()
    _duck_warm()
    r = s.get("https://duck.ai/duckchat/v1/status", headers={
        "x-vqd-accept": "1", "Cache-Control": "no-store", "Accept": "*/*"},
        timeout=(15, 25))
    if r.status_code != 200:
        raise EMError(f"duck: status {r.status_code}")
    ch = r.headers.get("x-vqd-hash-1")
    if not ch:
        raise EMError("duck: چەلەنجە نەگەڕایەوە")
    h1 = _duck_solve(ch)
    m = [{"role": x.get("role"), "content": [{"type": "text", "text": x.get("content", "")}]}
         for x in msgs]
    payload = {
        "model": model_id,
        "metadata": {"toolChoice": {"NewsSearch": False, "VideosSearch": False,
                                    "LocalSearch": False, "WeatherForecast": False}},
        "messages": m,
        "canUseTools": False,
        "reasoningEffort": "none",
        "canUseApproxLocation": None,
        "canDelegateImageGeneration": None,
        "canShowGreeting": False,
        "durableStream": {"messageId": str(_u.uuid4()), "conversationId": str(_u.uuid4()),
                          "publicKey": _duck_jwk()},
    }
    hdrs = {"Content-Type": "application/json", "Accept": "text/event-stream",
            "x-vqd-hash-1": h1, "x-fe-signals": _duck_signals(),
            "x-fe-version": DUCK_FE_VERSION, "x-ddg-journey-id": _u.uuid4().hex}
    r2 = s.post("https://duck.ai/duckchat/v1/chat", data=_j.dumps(payload),
                headers=hdrs, timeout=(15, timeout))
    if r2.status_code != 200:
        raise EMError(f"duck: {r2.status_code}")
    text = []
    for line in r2.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        d = line[6:].strip()
        if d == "[DONE]":
            break
        try:
            j = _j.loads(d)
        except Exception:
            continue
        if j.get("action") == "success" and isinstance(j.get("message"), str):
            text.append(j["message"])
        elif j.get("action") == "error":
            raise EMError(f"duck: {str(j.get('type', 'error'))[:50]}")
    ans = "".join(text).strip()
    if not ans:
        raise EMError("duck: وەڵام نەگەڕایەوە")
    return ans


def duck_chat(model_id, messages, timeout=110):
    """چاتی duck.ai — system دەفڕێتە ناو یەکەم نامەی بەکارهێنەر + ٢ هەوڵ"""
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    rest = [m for m in messages if m.get("role") != "system"][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    elif sys_txt:
        rest = [{"role": "user", "content": f"[ئاراستەی سیستەم: {sys_txt}]"}] + rest
    last = None
    for i in range(2):
        try:
            return _duck_attempt(model_id, rest, timeout)
        except EMError as e:
            last = e
            if "418" not in str(e) and "429" not in str(e):
                raise
            time.sleep(1.5 + i)
    raise last or EMError("duck: شکست")



# ════════════════════════════════════════════════════════════
# ٢.١٤) anakin.ai — «Free No Sign Up Chatgpt» — Gemini بێ تۆمار
#      node client (anakin_client.mjs) — واژووی ڕەسەن: md5(object-hash(body)+SECRET+ts)
#      لیمیت: ~٢ نامە/IP/پەنجەرە → cooldown ١٠ خولەک دوای ٤٢٩ — فەڵباکی زنجیرە
# ════════════════════════════════════════════════════════════

AK_CLIENT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anakin_client.mjs")
_AK_COOLDOWN = {"until": 0.0}


def ak_servers():
    return [
        {"id": "ak-gemini-2.5-flash", "name": "Gemini 2.5 Flash (Anakin)",
         "model_id": "308", "kind": "ak"},
        {"id": "ak-gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite (Anakin)",
         "model_id": "309", "kind": "ak"},
    ]


def ak_chat(model_id, messages, timeout=110):
    """چاتی anakin — node client؛ system تێکەڵ بە یەکەم نامە (شێوازی qb)"""
    import time as _t
    if _t.time() < _AK_COOLDOWN["until"]:
        raise EMError("ak: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    rest = [m for m in messages if m.get("role") in ("user", "assistant")][-21:]
    if rest and rest[0].get("role") == "user" and sys_txt:
        rest = [dict(rest[0])]
        rest[0] = dict(rest[0])
        rest[0]["content"] = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{rest[0]['content']}"
    payload = json.dumps({"model_id": int(model_id), "messages": rest}, ensure_ascii=False)
    try:
        p = subprocess.run([NODE_BIN, AK_CLIENT], input=payload.encode("utf-8"),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise EMError("ak: timeout")
    lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
    if not lines:
        raise EMError("ak: no output")
    try:
        obj = json.loads(lines[-1])
    except Exception:
        raise EMError("ak: bad output")
    if obj.get("ok") and obj.get("answer"):
        return obj["answer"]
    code = str(obj.get("code") or "")
    if "429" in code:
        _AK_COOLDOWN["until"] = _t.time() + 600
    raise EMError(obj.get("error") or "ak: failed", obj.get("code"))



# ════════════════════════════════════════════════════════════
# ٢.١٥) notegpt.io — AI Answer Generator — Gemini بێ تۆمار
#      POST /api/v2/homework/stream (SSE: data:{"text":...}) — بێ چەلەنجە، بێ کوکی
#      flash-lite: کراوە (~٩ نامە/IP/ڕۆژ) — pro: لیمیت ڕۆژانەی توند (٤٢٩٠١٦)
# ════════════════════════════════════════════════════════════

NG_LIMIT = {"until": 0.0}


# ══════════ LLM7 (llm7.io) — بێ کلیل، OpenAI-سازگار §2.17 ══════════
L7_LIMIT = {"until": 0.0}
L7_BASE = "https://api.llm7.io/v1"
L7_FALLBACK = [("codestral-latest", "Codestral"),
               ("mistral-Nemo-Instruct-2407", "Mistral Nemo"),
               ("minimax-m2.7", "MiniMax M2.7"),
               ("GLM-5.3-Flash", "GLM 5.3 Flash")]


def sync_l7_models():
    """ئۆتۆ-سینکی llm7 — turbo ی کۆمەڵگە + پشکنینی نوێیەکان (٣ لە خولێکدا) — هەر ٣٠ خولەک"""
    import time as _t
    if _t.time() - MS_T["l7"] < 1800:
        return
    try:
        r = requests.get(L7_BASE + "/models", headers={"User-Agent": ACT_UAS[0]},
                         timeout=(10, 20))
        items = (r.json() or {}).get("data") or []
    except Exception:
        return
    MS_T["l7"] = _t.time()
    cands = [m["id"] for m in items
             if m.get("tier") == "turbo" and m.get("model_type", "chat") == "chat"]
    # تێبینی: ok تەنها کاتێک لابردرێت کە چاتەکەی خۆی شکست بخوات (ل7 catalogs بەپێی ناوچە دەگۆڕدرێت)
    # bad ی کۆن دووبارە تاقی بکەوە (٢٤ کاتژمێر)
    for mid in list(MS["l7_bad"].keys()):
        if _t.time() - float(MS["l7_bad"][mid].get("t") or 0) > 86400:
            del MS["l7_bad"][mid]
    probed = 0
    for mid in cands:
        if mid in MS["l7_ok"] or mid in MS["l7_bad"] or probed >= 3:
            continue
        probed += 1
        try:
            rr = requests.post(L7_BASE + "/chat/completions",
                               json={"model": mid, "messages": [{"role": "user", "content": "Reply with: OK"}],
                                     "max_tokens": 8},
                               headers={"User-Agent": ACT_UAS[0], "Content-Type": "application/json"},
                               timeout=(10, 45))
            if rr.status_code == 200 and (rr.json().get("choices") or [{}])[0].get("message", {}).get("content"):
                MS["l7_ok"][mid] = {"t": _t.time()}
                print(f"[SYNC] l7: نوێی بێ-کلیل ✅ {mid}", flush=True)
            else:
                MS["l7_bad"][mid] = {"code": rr.status_code, "t": _t.time()}
        except Exception as e:
            MS["l7_bad"][mid] = {"err": str(e)[:60], "t": _t.time()}
        _ms_save()
        _t.sleep(1.5)


def l7_servers():
    ids = list(MS["l7_ok"].keys())
    if not ids:
        ids = [f for f, _ in L7_FALLBACK]
    labels = dict(L7_FALLBACK)
    out = []
    for mid in ids[:8]:
        label = labels.get(mid, (mid.split("-")[0].capitalize() if mid else "LLM7"))
        slug = re.sub(r'[^a-z0-9.]+', '-', mid.lower()).strip('-')
        out.append({"id": f"l7-{slug}", "name": f"{label} (LLM7)",
                    "model_id": mid, "kind": "l7"})
    return out


def l7_chat(messages, model_id="mistral-Nemo-Instruct-2407", timeout=90):
    """چاتی llm7.io — میوان: ١٠ داواکاری/خولەک، ٦٠/کاتژمێر بێ کلیل"""
    import time as _t
    if _t.time() < L7_LIMIT["until"]:
        raise EMError("l7: cooldown")
    body = {"model": model_id, "messages": messages, "max_tokens": 4000}  # #94U29 LONG-OUT
    try:
        r = requests.post(L7_BASE + "/chat/completions", json=body,
                          headers={"User-Agent": _pick_ua(ACT_UAS),
                                   "Content-Type": "application/json",
                                   "Referer": "https://llm7.io"},
                          timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"l7: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code in (429, 402):
            L7_LIMIT["until"] = _t.time() + 600
        elif r.status_code in (400, 401, 404) and model_id in MS.get("l7_ok", {}):
            # مۆدێڵ لە ترافیکی ڕاستەقینەدا مردووە (نەک ڕێگری کاتی) — لە ok بۆ bad بیبە (٢٤ کاتژمێر دووبارە)
            MS["l7_ok"].pop(model_id, None)
            MS.setdefault("l7_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
            print(f"[L7] مردوو لە چاتی ڕاستەقینە: {model_id} ({r.status_code}) — لە ok لابرا", flush=True)
        raise EMError(f"l7: {r.status_code}")
    try:
        m = r.json()["choices"][0]["message"]
    except Exception:
        raise EMError("l7: parse")
    return (m.get("content") or "").strip()


# ══════════ G4F Space (g4f.space) — کریتی PoW §2.18 ══════════
G4F_LIMIT = {"until": 0.0}
G4F_BASE = "https://g4f.space"
_G4F_CREDIT = {"v": 0}
_G4F_BAKE_LOCK = threading.Lock()


def _g4f_headers():
    return {"User-Agent": _pick_ua(ACT_UAS),
            "Content-Type": "application/json",
            "Referer": "https://g4f.dev/"}


def _cake_pow(uuid, salt, difficulty, max_nonce=120_000_000):
    """PoW: sha256(uuid:salt:nonce) ≥ difficulty بتی سیفر لە سەرەتا"""
    import hashlib as _hl
    pre = f"{uuid}:{salt}:".encode()
    thr = (1 << (32 - difficulty)) if 0 < difficulty < 32 else 1
    n = 0
    digest = _hl.sha256
    while n < max_nonce:
        end = n + 200000
        for nn in range(n, end):
            d = digest(pre + str(nn).encode()).digest()
            if int.from_bytes(d[:4], "big") < thr:
                return nn, d.hex()
        n = end
    return None, None


def _g4f_status():
    r = requests.get(G4F_BASE + "/cake/status", headers=_g4f_headers(), timeout=(10, 15))
    return r.json() if r.status_code == 200 else {}


def _g4f_bake_one(uuid, difficulty):
    nonce, hx = _cake_pow(uuid, "0", difficulty)
    if not nonce:
        return 0
    try:
        rb = requests.post(G4F_BASE + "/cake/bake", headers=_g4f_headers(),
                           json={"uuid": uuid, "salt": "0", "nonce": nonce, "hash": hx},
                           timeout=(10, 20))
        if rb.status_code == 200:
            j = rb.json() or {}
            return int(j.get("total_credit_cents") or j.get("credit_cents") or 0)
    except Exception:
        pass
    return 0


def _g4f_ensure_credits(min_credits=6, bake_max=2):
    """کەیک بنێژە ئەگەر کریت کەمە (١ کەیک = ٥ کریت، ~٥-١٥ چرکە)"""
    with _G4F_BAKE_LOCK:
        try:
            st = _g4f_status()
        except Exception:
            return
        _G4F_CREDIT["v"] = int(st.get("credit_cents") or 0)
        if _G4F_CREDIT["v"] >= min_credits:
            return
        diff = int(st.get("difficulty") or 24)
        try:
            r = requests.get(G4F_BASE + "/cake/issue?n=" + str(bake_max),
                             headers=_g4f_headers(), timeout=(10, 15))
            uuids = (r.json() or {}).get("uuids") or []
        except Exception:
            return
        for u_id in uuids:
            tot = _g4f_bake_one(u_id, diff)
            if tot:
                _G4F_CREDIT["v"] = tot
            time.sleep(0.3)
            if _G4F_CREDIT["v"] >= min_credits:
                break


def _g4f_baker_daemon():
    """پاشبنەما: کریت ≥ ١٠ ڕابگرێت (١٠٠ کەیک/ڕۆژ بۆ هەر IP)"""
    time.sleep(20)
    while True:
        try:
            st = _g4f_status()
            if int(st.get("credit_cents") or 0) < 10 and int(st.get("baked_today") or 0) < int(st.get("limit_per_day") or 100):
                _g4f_ensure_credits(min_credits=12, bake_max=3)
        except Exception:
            pass
        time.sleep(90)


G4F_TRUST = {"groq.com", "nvidia.com", "gemini-v1beta", "ollama.com", "ollama-swarm",
             "ollama.pro", "logfare.ai", "relayrouter.org", "openrouter.ai"}
G4F_EXCLUDE = ("whisper", "tts", "embed", "bge", "guard", "image", "flux",
               "stable-diffusion", "sdxl", "music", "video", "dall")


def _g4f_models():
    """داینامیکی تەواو — باشترین ٨ بە باوبانگ لە پڕۆڤایەری متمانەپێکراو"""
    out, seen = [], set()
    try:
        r = requests.get(G4F_BASE + "/v1/models", headers=_g4f_headers(), timeout=(10, 20))
        items = (r.json() or {}).get("data") or []
    except Exception:
        items = []
    PREFER = ["openai/gpt-oss-120b", "gpt-4o-mini"]
    # ١. دوو دڵنیاکە
    for tail in PREFER:
        for it in items:
            sid = str(it.get("id") or "")
            if sid == tail or sid.endswith(":" + tail):
                slug = re.sub(r"[^a-z0-9.]+", "-", tail.lower()).strip("-")
                if slug not in seen:
                    seen.add(slug)
                    out.append({"id": f"g4f-{slug}", "name": f"{tail.split('/')[-1]} (G4F)",
                                "model_id": sid, "kind": "g4f"})
                break
    # ٢. پڕۆڤایەری متمانەپێکراو — ڕیز بە داواکاری
    pool = []
    for it in items:
        sid = str(it.get("id") or "")
        owner = str(it.get("owned_by") or "")
        if owner not in G4F_TRUST:
            continue
        if owner == "openrouter.ai" and ":free" not in sid:
            continue
        base = sid.split(":", 1)[1] if ":" in sid else sid
        low = base.lower()
        if any(x in low for x in G4F_EXCLUDE):
            continue
        try:
            reqs = int(it.get("requests") or 0)
        except Exception:
            reqs = 0
        pool.append((reqs, base, sid))
    pool.sort(reverse=True)
    for reqs, base, sid in pool:
        if len(out) >= 8:
            break
        slug = re.sub(r"[^a-z0-9.]+", "-", base.lower()).strip("-")
        if slug in seen:
            continue
        seen.add(slug)
        out.append({"id": f"g4f-{slug}", "name": f"{base} (G4F)", "model_id": sid, "kind": "g4f"})
    return out


def g4f_chat(messages, model_id, timeout=110):
    """چاتی g4f.space — کریتی PoW؛ ٤٠٢/٤٢٩ → ١٥ خولەک cooldown"""
    import time as _t
    if _t.time() < G4F_LIMIT["until"]:
        raise EMError("g4f: cooldown")
    if _G4F_CREDIT["v"] < 4:
        _g4f_ensure_credits(min_credits=4, bake_max=1)
    try:
        r = requests.post(G4F_BASE + "/v1/chat/completions",
                          json={"model": model_id, "messages": messages},
                          headers=_g4f_headers(), timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"g4f: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code in (402, 429):
            G4F_LIMIT["until"] = _t.time() + 900
        raise EMError(f"g4f: {r.status_code}")
    try:
        return (r.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception:
        raise EMError("g4f: parse")


def ng_servers():
    return [{"id": "ng-gemini-flash-lite", "name": "Gemini 3.1 Flash Lite (NoteGPT)",
             "model_id": "gemini-3.1-flash-lite", "kind": "ng"}]


def ng_chat(messages, timeout=110):
    """چاتی notegpt — مێژوو بۆ یەک نامە؛ template ی homework یش لابردن"""
    import time as _t
    if _t.time() < NG_LIMIT["until"]:
        raise EMError("ng: cooldown")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    user_txt = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_txt = m["content"]
            break
    if not user_txt:
        user_txt = " ".join(m.get("content", "") for m in messages)[-2000:]
    if sys_txt:
        user_txt = f"[ئاراستەی سیستەم: {sys_txt}]\n\n{user_txt}"
    try:
        r = requests.post("https://notegpt.io/api/v2/homework/stream",
                          json={"message": user_txt, "language": "auto", "model": "gemini-3.1-flash-lite",
                                "tone": "default", "length": "moderate",
                                "conversation_id": str(__import__("uuid").uuid4())},
                          headers={"User-Agent": _pick_ua(ACT_UAS),
                                   "Origin": "https://notegpt.io",
                                   "Referer": "https://notegpt.io/ai-answer-generator"},
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"ng: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            NG_LIMIT["until"] = _t.time() + 1800
        raise EMError(f"ng: {r.status_code}")
    text = []
    limit_hit = False
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        try:
            d = json.loads(line[6:])
        except Exception:
            continue
        if isinstance(d.get("text"), str):
            text.append(d["text"])
        if d.get("code") == 164016:
            limit_hit = True
    ans = "".join(text).strip()
    if limit_hit and not ans:
        NG_LIMIT["until"] = _t.time() + 1800
        raise EMError("ng: لیمیت ڕۆژانە")
    # template ی homework پاک بکەوە
    ans = re.sub(r"^###\s*Question\s*\d*\s*", "", ans)
    ans = re.sub(r"\n?###\s*(Answer|Solution Steps|[^\n]*)\s*", "\n", ans)
    ans = ans.strip()
    if ans:
        return ans
    raise EMError("ng: وەڵام نەگەڕایەوە")



# ════════════════════════════════════════════════════════════
# ٢.١٦) ئۆتۆ-سینکی مۆدێڵ — ئەگەر سەرچاوەیەک مۆدێڵی نوێ زیاد بکات یان بگۆڕێت
#      خۆکارانە دەخوێنرێتەوە؛ تەنها مۆدێڵی ڕاییگەی سەلمێنراو زیاد دەکرێت
#      duck: لیست لە bundle ی فەرمییەوە | ak: پڕۆب ی بچووک بۆ مۆدێڵی نوێ
# ════════════════════════════════════════════════════════════

MODEL_SYNC_FILE = os.path.join(DATA_DIR, "model_sync.json")
MS = {"duck": {}, "ak_ok": {}, "ak_block": {}, "l7_ok": {}, "l7_bad": {}, "ct_ok": {}, "ct_bad": {}, "yl_ok": {}, "yl_bad": {}, "hk_ok": {}, "hk_bad": {}, "hf_ok": {}, "hf_bad": {}, "aka_ok": {}, "aka_bad": {}, "hb_ok": {}, "hb_bad": {}, "gk_ok": {}, "gk_bad": {}, "gz_ok": {}, "gz_bad": {}, "pi_ok": {}, "pi_bad": {}, "cb_ok": {}, "cb_bad": {}, "nv_ok": {}, "nv_bad": {}, "al_ok": {}, "al_bad": {}, "aiml_ok": {}}
MS_T = {"duck": 0.0, "ak": 0.0, "l7": 0.0, "ct": 0.0, "yl": 0.0, "hk": 0.0, "hf": 0.0, "aka": 0.0, "hb": 0.0, "gk": 0.0, "gz": 0.0, "pi": 0.0, "cb": 0.0, "ac": 0.0, "nv": 0.0, "al": 0.0}
MS_LOCK = threading.Lock()


def _ms_load():
    try:
        with open(MODEL_SYNC_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k in ("duck", "ak_ok", "ak_block", "l7_ok", "l7_bad", "ct_ok", "ct_bad", "yl_ok", "yl_bad", "hk_ok", "hk_bad", "hf_ok", "hf_bad", "aka_ok", "aka_bad", "hb_ok", "hb_bad", "gk_ok", "gk_bad", "gz_ok", "gz_bad", "pi_ok", "pi_bad", "cb_ok", "cb_bad", "nv_ok", "nv_bad", "al_ok", "al_bad", "aiml_ok"):
            v = d.get(k)
            if isinstance(v, dict):
                MS[k].update(v)
    except Exception:
        pass


def _ms_save():
    try:
        _json_save(MODEL_SYNC_FILE, MS)
    except Exception:
        pass


_ms_load()


# ══════════ ChatTide (chattide.ai) — §2.20 — ٢ چات/ڕۆژ بۆ هەر IP (٠٠:٠٠ UTC نوێ دەبێتەوە) ══════════
CT_LIMIT = {"quota_until": 0.0, "wobble_until": 0.0}
CT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
_CT_N = int(
    "c201d7ff13221b2c1c631aa9a1eea2d4ebf08f0b3aeefbbe7ef363923d9fa77f8045be0f3c76ba59e8a8a0356d09f13360c5ee989acd62ac264d543caef915ec978cbfedcd8a3877383864f31c1e5f50c88c6ac154bdc12cd8fef47bac80fec28765f04b1b55cf8656fce086ecde7843dd6e5ed92b82fb812e5646aaccdd3c2d", 16)
_CT_E = 65537
_CT_SYNC = {"t": 0.0}
_CT_ARR_RE = re.compile(r'\[\{name:"[^"]{1,50}",value:"[^"]{1,50}"\}(?:,\{name:"[^"]{1,50}",value:"[^"]{1,50}"\}){0,30}\]')
_CT_VAL_RE = re.compile(r'\{name:"([^"]{1,50})",value:"([^"]{1,50})"\}')
_CT_FALLBACK = [("gpt-5.6-luna", "GPT 5.6 Luna")]


def _ct_vtoken(vid):
    """vtoken = base64(RSA-PKCS1v15-pub(vid)) — تەنها stdlib (پادینی تایپ-٢ ڕاندۆم)"""
    import base64 as _b64
    import secrets as _sc
    ps_len = 128 - 3 - len(vid)
    ps = bytearray()
    while len(ps) < ps_len:
        b = _sc.token_bytes(1)
        if b != b"\x00":
            ps += b
    em = b"\x00\x02" + bytes(ps) + b"\x00" + vid.encode()
    return _b64.b64encode(pow(int.from_bytes(em, "big"), _CT_E, _CT_N).to_bytes(128, "big")).decode()


def _ct_identity():
    """ناسنامەی میوانی نوێ: visitorId = md5-ڕاندۆم → vtoken + mo_uuid"""
    import hashlib as _hl
    from urllib.parse import quote as _q
    vid = _hl.md5(("ct" + str(time.time_ns()) + str(random.random())).encode()).hexdigest()
    vt = _ct_vtoken(vid)
    mo = _hl.md5(("mo" + vid).encode()).hexdigest()
    hd = {"accept": "text/event-stream,application/json, text/event-stream",
          "content-type": "application/json", "lang": "en", "source": "web",
          "referer": "https://www.chattide.ai/", "origin": "https://www.chattide.ai",
          "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="153", "HeadlessChrome";v="153"',
          "sec-ch-ua-mobile": "?0", "sec-ch-ua-platform": '"Windows"',
          "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-site",
          "user-agent": CT_UA, "vtoken": vt}
    ck = {"NEXT_LOCALE": "en", "mo_uuid": mo, "chatTide.visitor.id": _q(vt, safe="")}
    return hd, ck


def _ct_quota_ts():
    """نیوەشەوی UTC ی داهاتوو + ٥ خولەک — کاتی نوێبوونەوەی کوانتای ڕۆژانە"""
    return (int(time.time()) // 86400 + 1) * 86400 + 300


def ct_chat(messages, model_id="gpt-5.6-luna", timeout=150):
    """چاتی chattide.ai — میوان: ٢ چات/ڕۆژ بۆ هەر IP؛ کۆدی 229 → دیلی تا نیوەشەوی UTC"""
    import time as _t
    if _t.time() < CT_LIMIT["quota_until"]:
        raise EMError("ct: daily quota (2/IP/day)")
    if _t.time() < CT_LIMIT["wobble_until"]:
        raise EMError("ct: wobble cooldown")
    hd, ck = _ct_identity()
    body = {"spaceHandle": True, "roleId": 0, "conversationId": None, "model": model_id,
            "messages": [{"role": m.get("role", "user"),
                          "content": [{"type": "text", "text": m.get("content") or ""}]} for m in messages]}
    try:
        r = requests.post("https://api.chattide.ai/aigc/chat/v2/professional/stream",
                          json=body, headers=hd, cookies=ck, timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"ct: {str(e)[:60]}")
    if r.status_code != 200:
        raise EMError(f"ct: {r.status_code}")
    txt = r.text
    if '"code":229' in txt or "quota has been exhausted" in txt:
        CT_LIMIT["quota_until"] = _ct_quota_ts()
        raise EMError("ct: 229 quota → دیلی بۆ نیوەشەوی UTC")
    out = []
    for line in txt.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        tok = line[5:].strip()
        if not tok or tok == "--@DONE@--":
            continue
        if tok.startswith("Please refresh"):
            CT_LIMIT["wobble_until"] = _t.time() + 600
            raise EMError("ct: refresh-wobble → دیلی ١٠ خولەک")
        if tok.startswith("{"):
            try:
                j = json.loads(tok)
            except Exception:
                continue
            if str(j.get("code")) == "229" or "quota" in str(j.get("message") or "").lower():
                CT_LIMIT["quota_until"] = _ct_quota_ts()
                raise EMError("ct: 229 quota → دیلی بۆ نیوەشەوی UTC")
            continue
        out.append(tok)
    ans = "".join(out).replace("-=- --", " ").replace("-=-n--", "\n").strip()
    ans = re.sub(r" {3,}", "  ", ans)
    if not ans:
        CT_LIMIT["wobble_until"] = _t.time() + 300
        raise EMError("ct: وەڵام بەتاڵ")
    CT_LIMIT["quota_until"] = 0.0
    CT_LIMIT["wobble_until"] = 0.0
    return ans


def _ct_label(mid):
    out = []
    for p in str(mid).split("-"):
        out.append(p if p and p[0].isdigit() else p.capitalize())
    return " ".join(out)


def ct_servers():
    ids = list(MS.get("ct_ok", {}).keys()) or [f for f, _ in _CT_FALLBACK]
    labels = dict(_CT_FALLBACK)
    out = []
    for mid in ids[:6]:
        label = labels.get(mid, _ct_label(mid))
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-')
        out.append({"id": f"ct-{slug}", "name": f"{label} (ChatTide)",
                    "model_id": mid, "kind": "ct"})
    return out


def _ct_is_model(val):
    v = str(val)
    if not re.match(r'^(gpt|claude|gemini|grok|llama|qwen|deepseek|mistral|glm|kimi|minimax|o[1-9])[\w.\-]*$', v):
        return False
    return not any(w in v for w in ("whisper", "tts", "embed", "image", "flux", "video", "music", "guard"))


def sync_ct_models(force=False):
    """ئۆتۆ-ئەپدێتی chattide: لیستی مۆدێڵە زیندووەکان لە چەرەکەکانی Next.js (TTL ٦ کاتژمێر).
       هیچ شتێک ناسڕدرێتەوە — تەنها زیادکردن (یاسای ڕاگرتنی هەموو مۆدێڵەکان)"""
    import time as _t
    if not force and _t.time() - _CT_SYNC["t"] < 21600:
        return
    _CT_SYNC["t"] = _t.time()
    found = {}

    def _scan(js):
        if 'value:"' not in js:
            return
        for arr in _CT_ARR_RE.findall(js):
            for _nm, val in _CT_VAL_RE.findall(arr):
                if _ct_is_model(val):
                    found[val] = True

    try:
        h = {"User-Agent": CT_UA}
        html = requests.get("https://www.chattide.ai/chat/", headers=h, timeout=(10, 20)).text
        chunks = set(re.findall(r'/_next/static/chunks/[a-zA-Z0-9/_.\-]+\.js', html))
        for cu in list(chunks)[:6]:
            try:
                js = requests.get("https://www.chattide.ai" + cu, headers=h, timeout=(10, 15)).text
                _scan(js)
                chunks |= set(re.findall(r'/_next/static/chunks/[a-zA-Z0-9/_.\-]+\.js', js))
            except Exception:
                continue
        for cu in list(chunks)[:30]:
            try:
                js = requests.get("https://www.chattide.ai" + cu, headers=h, timeout=(10, 15)).text
            except Exception:
                continue
            _scan(js)
    except Exception as e:
        print(f"[CT-SYNC] هەڵە: {str(e)[:80]}", flush=True)
        return
    added = 0
    for mid in found:
        if mid not in MS.get("ct_ok", {}) and mid not in MS.get("ct_bad", {}):
            MS.setdefault("ct_ok", {})[mid] = {"t": time.time()}
            added += 1
            print(f"[CT-SYNC] مۆدێڵی نوێ: {mid}", flush=True)
    if added:
        _ms_save()
    print(f"[CT-SYNC] chattide: {len(found)} دۆزرا، {added} زیادکرا، ct_ok={len(MS.get('ct_ok', {}))}", flush=True)


# ══════════ Yollo AI (yollo.ai) — §2.21 — بێ لیمیت بۆ دەق (پارە لە وێنە/ڤیدیۆ) ══════════
YL_BASE = "https://www.yollo.ai"
YL_BOT = 147747
YL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
_YL = {"tok": "", "sid": "", "finger": "", "t": 0.0}


def _yl_headers(finger, tok=None, ct=True):
    hd = {"User-Agent": YL_UA, "x-platform": "web", "x-version": "999.0.0",
          "x-finger": finger, "x-language": "en", "Origin": YL_BASE,
          "Referer": YL_BASE + "/ar/chat"}
    if ct:
        hd["Content-Type"] = "application/json"
    if tok:
        hd["x-auth-token"] = tok
    return hd


def _yl_identity(force=False):
    """میوانی نوێ: createGuest → loginByGuest (JWT ٣٠ ڕۆژ) → createSession — بێ captcha"""
    import time as _t
    import hashlib as _hl
    if not force and _YL["tok"] and _YL["sid"] and _t.time() - _YL["t"] < 4 * 86400:
        return
    finger = _hl.md5(("yl" + str(_t.time_ns()) + str(random.random())).encode()).hexdigest()
    g = requests.post(YL_BASE + "/api/auth/createGuest", headers=_yl_headers(finger, ct=False), timeout=(10, 20)).json()
    d = g.get("data") or {}
    if not d.get("guestUid"):
        raise EMError(f"yl: createGuest {str(g)[:60]}")
    r2 = requests.post(YL_BASE + "/api/auth/loginByGuest", headers=_yl_headers(finger), json=d, timeout=(10, 20)).json()
    tok = (r2.get("data") or {}).get("idToken")
    if not tok:
        raise EMError(f"yl: login {str(r2)[:60]}")
    r3 = requests.post(YL_BASE + "/api/msg/createSession", params={"botId": YL_BOT},
                       headers=_yl_headers(finger, tok=tok, ct=False), timeout=(10, 20)).json()
    sid = (r3.get("data") or {}).get("id")
    if not sid:
        raise EMError(f"yl: session {str(r3)[:60]}")
    _YL.update(tok=tok, sid=str(sid), finger=finger, t=_t.time())


def yl_chat(messages, model_id="yollo-chat", timeout=120):
    """چاتی yollo.ai — مێژوو لە کلایەنتەوە (سیستەم-پرۆمپتی خۆمان) — دەق بێ لیمیت"""
    import time as _t
    if not messages:
        raise EMError("yl: هیچ نامە")
    last = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last = m["content"]
            break
    if not last:
        last = messages[-1].get("content") or ""
    hist = [{"role": m.get("role", "user"), "content": m.get("content") or ""}
            for m in messages if m.get("content")]
    if hist and hist[-1]["role"] == "user" and hist[-1]["content"] == last:
        hist = hist[:-1]
    lasterr = None
    for attempt in range(2):
        try:
            _yl_identity(force=(attempt == 1))
        except Exception as e:
            lasterr = e
            continue
        _sys = _sys_txt(messages)  # #94U25b
        _q = f"[Instructions: {_sys}]\n\n{last}" if _sys else last
        body = {"message": _q, "sessionId": _YL["sid"], "conversationHistory": _sys_keep(hist, 20),
                "userToken": _YL["tok"], "userLocale": "en", "isRegenerate": False,
                "isSafeMode": False, "generateType": 0}
        try:
            r = requests.post(YL_BASE + "/chat-stream", json=body,
                              headers=_yl_headers(_YL["finger"]), timeout=(15, timeout), stream=True)
        except Exception as e:
            lasterr = EMError(f"yl: {str(e)[:60]}")
            continue
        if r.status_code != 200:
            lasterr = EMError(f"yl: {r.status_code}")
            _YL["tok"] = ""
            continue
        out = []
        bad = None
        for line in r.text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if not p:
                continue
            try:
                j = json.loads(p)
            except Exception:
                continue
            ty = j.get("type")
            if ty == "content":
                out.append(j.get("content") or "")
            elif ty == "end":
                break
            elif ty in ("error", "errorMsg") or j.get("error") or "error" in str(ty or "").lower():
                bad = str(j.get("message") or j)[:80]
                break
        ans = "".join(out).strip()
        if ans:
            return ans
        lasterr = EMError(f"yl: {bad or 'وەڵام بەتاڵ'}")
        _YL["sid"] = ""
    raise lasterr or EMError("yl: شکست")


def yl_servers():
    out = []
    for mid in list(MS.get("yl_ok", {}).keys())[:3] or ["yollo-chat"]:
        out.append({"id": "yl-yollo-chat", "name": "Yollo Chat",
                    "model_id": mid, "kind": "yl"})
    return out


def sync_yl_models(force=False):
    """ئۆتۆ-ئەپدێتی yollo: پشکنینی زیندووی فلۆوی میوان (٦ کاتژمێر) — مۆدێڵی چات لە سێرڤەرەوە شاراوەیە"""
    import time as _t
    if not force and _t.time() - MS_T.get("yl", 0.0) < 21600:
        return
    MS_T["yl"] = _t.time()
    try:
        r = requests.get(YL_BASE + f"/api/bot?botId={YL_BOT}",
                         headers={"User-Agent": YL_UA}, timeout=(10, 20))
        if r.status_code != 200:
            print(f"[YL-SYNC] بۆت ڕێک نەگەیشت: {r.status_code}", flush=True)
            return
        MS.setdefault("yl_ok", {})["yollo-chat"] = {"t": _t.time()}
        _ms_save()
        print("[YL-SYNC] yollo زیندووە — yollo-chat ئامادە", flush=True)
    except Exception as e:
        print(f"[YL-SYNC] هەڵە: {str(e)[:80]}", flush=True)


# ══════════ Heck AI (heck.ai) — §2.22 — بێ لۆگین؛ FREE = ٥٠ چات/ڕۆژ؛ probe-gated ══════════
HK_BASE = "https://api.heckai.weight-wave.com/api/ha/v1"
HK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
HK_LIMIT = {"until": 0.0}
_HK = {"sid": "", "t": 0.0}
# کاتالۆگی تایر-فری (لە چەرەکی layout هەڵدرا) — premium ەکان 401 ن — دانەمەزرێن
HK_CATALOG = [
    ("deepseek/deepseek-v4-flash", "DeepSeek v4 Flash"),
    ("deepseek/deepseek-v4-pro", "DeepSeek v4 Pro"),
    ("tencent/hy3-preview", "Tencent Hy3 Preview"),
    ("qwen/qwen3.7-plus", "Qwen 3.7 Plus"),
    ("stepfun/step-3.7-flash", "Step 3.7 Flash"),
    ("google/gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite"),
    ("google/gemini-3-flash-preview", "Gemini 3.0 Flash"),
    ("openai/gpt-5.4-mini", "GPT 5.4 mini"),
    ("minimax/minimax-m3", "Minimax M3"),
    ("anthropic/claude-opus-4.8", "Claude Opus 4.8"),
]


def _hk_headers():
    return {"User-Agent": HK_UA, "Content-Type": "application/json",
            "Origin": "https://heck.ai", "Referer": "https://heck.ai/", "authorization": ""}


def _hk_session(force=False):
    import time as _t
    if not force and _HK["sid"] and _t.time() - _HK["t"] < 3600:
        return _HK["sid"]
    r = requests.post(HK_BASE + "/session/create", json={"title": "chat"},
                      headers=_hk_headers(), timeout=(10, 20))
    sid = (r.json() or {}).get("id")
    if not sid:
        raise EMError(f"hk: session {str(r.text)[:60]}")
    _HK.update(sid=sid, t=_t.time())
    return sid


def _hk_quota_ts():
    import time as _t
    return (int(_t.time()) // 86400 + 1) * 86400 + 300


def hk_chat(messages, model_id="deepseek/deepseek-v4-flash", timeout=120):
    """چاتی heck.ai — تک-شۆت (پرسیار + وەڵامی پێشوو)؛ 402 = کرێکی OpenRouter ەکەیان"""
    import time as _t
    if _t.time() < HK_LIMIT["until"]:
        raise EMError("hk: upstream credit cooldown")
    last, pq, pa = "", None, None
    for m in reversed(messages):
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if m.get("role") == "user":
            last = c
            break
        if pa is None:
            pa = c
        elif pq is None:
            pq = c
    if not last:
        raise EMError("hk: هیچ پرسیار")
    _sys = _sys_txt(messages)  # #94U25: system مەفەوتێنە — بیخە سەر پرسیار
    _q = (f"[Instructions: {_sys}]\n\n{last[-4000:]}" if _sys else last[-4000:])  # #94U26: system تەواو (14k) + کۆتایی پرسیار
    sid = _hk_session()
    body = {"model": model_id, "question": _q, "language": "English",
            "sessionId": sid, "previousQuestion": pq, "previousAnswer": pa,
            "imgUrls": [], "superSmartMode": False}
    try:
        r = requests.post(HK_BASE + "/chat", json=body, headers=_hk_headers(),
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"hk: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            HK_LIMIT["until"] = _t.time() + 600
        elif r.status_code in (400, 500) and model_id in MS.get("hk_ok", {}):
            MS["hk_ok"].pop(model_id, None)
            MS.setdefault("hk_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
        raise EMError(f"hk: {r.status_code}")
    out = []
    err = None
    paywall = False
    for line in r.text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        tok = line[5:].strip()
        if not tok or tok == "[ERROR]":
            continue
        if tok.startswith("{"):
            try:
                j = json.loads(tok)
            except Exception:
                continue
            msg = str(j.get("message") or "")
            if j.get("error") or "error" in str(j.get("error", "")).lower():
                err = msg[:90]
                if "Payment Required" in msg or "402" in msg or "credits" in msg.lower():
                    paywall = True
                break
            for key in ("content", "text", "answer", "token", "delta"):
                v = j.get(key)
                if isinstance(v, str) and v:
                    out.append(v)
                    break
            continue
        out.append(tok)
    ans = "".join(out).strip()
    if paywall:
        HK_LIMIT["until"] = _hk_quota_ts()
        if MS.get("hk_ok"):
            MS["hk_ok"].clear()
            _ms_save()
            print("[HK] کرێکی سەرەوە بەتاڵ — hk_ok پاککرایەوە تا چاک بوو", flush=True)
        raise EMError("hk: 402 upstream → دیلی تا نیوەشەوی UTC")
    if not ans:
        raise EMError(f"hk: {err or 'وەڵام بەتاڵ'}")
    return ans


def hk_servers():
    labels = dict(HK_CATALOG)
    out = []
    for mid in list(MS.get("hk_ok", {}).keys())[:12]:
        label = labels.get(mid, mid.split("/")[-1])
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-').replace('/', '-')
        out.append({"id": f"hk-{slug}", "name": f"{label} (Heck)",
                    "model_id": mid, "kind": "hk"})
    return out


def sync_hk_models(force=False):
    """ئۆتۆ-ئەپدێتی heck: پشکنینی زیندوو — ٤٠٢ (کرێکی بەتاڵ) → هیچ؛ سەرکەوتن → هەموو کاتالۆگەکە ✅
       نیو کاتژمێر لە کاتی مردوودا (زیندووبوونەوەی خێرا)، ٦ کاتژمێر لە کاتی زیندوودا"""
    import time as _t
    ok_now = bool(MS.get("hk_ok"))
    ttl = 21600 if ok_now else 1800
    if not force and _t.time() - MS_T.get("hk", 0.0) < ttl:
        return
    MS_T["hk"] = _t.time()
    probe = "deepseek/deepseek-v4-flash"
    try:
        a = hk_chat([{"role": "user", "content": "Reply with exactly: OK"}], probe, timeout=45)
        alive = bool(a)
    except Exception as e:
        alive = False
        msg = str(e)[:70]
        if "402" in msg or "credit" in msg.lower():
            print(f"[HK-SYNC] کرێکی سەرەوە بەتاڵە ({msg}) — چاوەڕوانی پڕکردنەوە", flush=True)
        else:
            print(f"[HK-SYNC] پشکنین شکات: {msg}", flush=True)
    if alive:
        added = 0
        for mid, _lbl in HK_CATALOG:
            if mid not in MS.get("hk_ok", {}):
                MS.setdefault("hk_ok", {})[mid] = {"t": _t.time()}
                added += 1
        for mid in list(MS.get("hk_bad", {}).keys()):
            MS["hk_bad"].pop(mid, None)
        if added or not ok_now:
            _ms_save()
        print(f"[HK-SYNC] heck زیندووە ✅ {added} مۆدێڵ چالاک بوون (hk_ok={len(MS['hk_ok'])})", flush=True)
    elif ok_now and not MS.get("hk_ok"):
        _ms_save()


# ══════════ HuggingFace Inference (router.huggingface.co) — §2.23 — تۆکنی yusfkarim1028 ══════════
HF_TOKEN = "hf_" + "ZNGBNvoPbHFpqMVMscrJpUHhfHJoKnvBeQ"  # yusfkarim1028
HF_BASE = "https://router.huggingface.co/v1"
HF_LIMIT = {"until": 0.0}
_HF_SYNC = {"t": 0.0}


def _hf_headers(ct=True):
    hd = {"Authorization": f"Bearer {HF_TOKEN}", "User-Agent": "Mozilla/5.0"}
    if ct:
        hd["Content-Type"] = "application/json"
    return hd


def hf_chat(messages, model_id="deepseek-ai/DeepSeek-V4.1-Flash", timeout=110):
    """چاتی HF Inference — OpenAI-ستایل؛ 402 = کرێتی مانگانە (دیلی تا یەکی مانگ)؛ 429 = ١٠ خولەک"""
    import time as _t
    if _t.time() < HF_LIMIT["until"]:
        raise EMError("hf: credit cooldown")
    body = {"model": model_id, "messages": _sys_keep(messages, 23), "max_tokens": 4000}  # #94U25 #94U29 LONG-OUT
    try:
        r = requests.post(HF_BASE + "/chat/completions", json=body,
                          headers=_hf_headers(), timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"hf: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 402:
            # کرێتی مانگانە تەواو — دیلی تا یەکی مانگی داهاتوو + پاککردنەوەی مینیو
            now = _t.time()
            nxt = (_t.gmtime(now).tm_year + (1 if _t.gmtime(now).tm_mon == 12 else 0),
                   1 if _t.gmtime(now).tm_mon == 12 else _t.gmtime(now).tm_mon + 1, 1)
            import calendar as _cal
            HF_LIMIT["until"] = _cal.timegm(nxt + (0, 0, 0)) + 300
            if MS.get("hf_ok"):
                MS["hf_ok"].clear()
                _ms_save()
                print("[HF] کرێتی تەواو — hf_ok پاککرایەوە تا ڕێککەوتنی مانگ", flush=True)
            raise EMError("hf: 402 → دیلی تا مانگی داهاتوو")
        if r.status_code == 429:
            HF_LIMIT["until"] = _t.time() + 600
            raise EMError("hf: 429 → دیلی ١٠ خولەک")
        # مردوو لە ترافیکی ڕاستەقینە (400/404/503) → لە hf_ok بۆ hf_bad (دووبارە ٢٤ کاتژمێر)
        if r.status_code in (400, 404, 503) and model_id in MS.get("hf_ok", {}):
            MS["hf_ok"].pop(model_id, None)
            MS.setdefault("hf_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
            _ms_save()
            print(f"[HF] مردوو لە چات: {model_id} ({r.status_code}) — لابرا", flush=True)
        raise EMError(f"hf: {r.status_code}")
    try:
        m = r.json()["choices"][0]["message"]
    except Exception:
        raise EMError("hf: parse")
    return (m.get("content") or "").strip()


def hf_servers():
    labels = {}
    out = []
    for mid in list(MS.get("hf_ok", {}).keys())[:40]:
        tail = str(mid).split("/")[-1]
        label = re.sub(r'[-_]', ' ', tail).strip()
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-').replace('/', '-')
        out.append({"id": f"hf-{slug}", "name": f"{label} (HF)",
                    "model_id": mid, "kind": "hf"})
    return out


def sync_hf_models(force=False):
    """ڕاکێشانی ئۆتۆماتیکی مۆدێڵەکانی HF:
       - کاتالۆگی زیندوو لە /v1/models (لابردنی ئەوانەی HF لابراون — یاسای بەکارهێنەر)
       - پشکنینی نوێیەکان (١٠/خول) → هەر کامێک وەڵام دا بگاتە hf_ok
       - مردووەکان (پشکنین/چات شکات) → hf_bad (دووبارە ٢٤ کاتژمێر)
       خول: ٦ کاتژمێر"""
    import time as _t
    if not force and _t.time() - _HF_SYNC["t"] < 21600:
        return
    _HF_SYNC["t"] = _t.time()
    try:
        r = requests.get(HF_BASE + "/models", headers={"User-Agent": "Mozilla/5.0"}, timeout=(10, 30))
        items = r.json().get("data") or []
    except Exception as e:
        print(f"[HF-SYNC] کاتالۆگ هەڵە: {str(e)[:70]}", flush=True)
        return
    catalog = {m.get("id") for m in items if m.get("id")}
    # ١) لابردنی ئەوانەی لە کاتالۆگ نەماون (مردوو/لابراو لەلایەن HF)
    removed = [mid for mid in list(MS.get("hf_ok", {}).keys()) if mid not in catalog]
    for mid in removed:
        MS["hf_ok"].pop(mid, None)
        print(f"[HF-SYNC] لابرا لە کاتالۆگ: {mid}", flush=True)
    # ٢) زیندووکردنەوەی bad ە کۆن (٢٤ کاتژمێر)
    for mid in list(MS.get("hf_bad", {}).keys()):
        if _t.time() - float(MS["hf_bad"][mid].get("t") or 0) > 86400:
            MS["hf_bad"].pop(mid, None)
    # ٣) پشکنینی نوێیەکان (١٠/خول)
    probed = 0
    added = 0
    for mid in catalog:
        if mid in MS.get("hf_ok", {}) or mid in MS.get("hf_bad", {}) or probed >= 10:
            continue
        probed += 1
        try:
            rr = requests.post(HF_BASE + "/chat/completions",
                               json={"model": mid, "messages": [{"role": "user", "content": "Reply: OK"}], "max_tokens": 8},
                               headers=_hf_headers(), timeout=(10, 40))
            if rr.status_code == 200 and (rr.json().get("choices") or [{}])[0].get("message", {}).get("content"):
                MS.setdefault("hf_ok", {})[mid] = {"t": _t.time()}
                added += 1
                print(f"[HF-SYNC] نوێ ✅ {mid}", flush=True)
            elif rr.status_code == 402:
                import calendar as _cal
                g = _t.gmtime(_t.time())
                nxt = (g.tm_year + (1 if g.tm_mon == 12 else 0), 1 if g.tm_mon == 12 else g.tm_mon + 1, 1)
                HF_LIMIT["until"] = _cal.timegm(nxt + (0, 0, 0)) + 300
                if MS.get("hf_ok"):
                    MS["hf_ok"].clear()
                    print("[HF-SYNC] کرێتی مانگانە تەواو — hf_ok پاککرایەوە", flush=True)
                _ms_save()
                break
            else:
                MS.setdefault("hf_bad", {})[mid] = {"code": rr.status_code, "t": _t.time()}
        except Exception as e:
            MS.setdefault("hf_bad", {})[mid] = {"err": str(e)[:60], "t": _t.time()}
        _t.sleep(0.6)
    if added or removed:
        _ms_save()
    print(f"[HF-SYNC] کاتالۆگ={len(catalog)} | نوێ={added} | لابرا={len(removed)} | hf_ok={len(MS.get('hf_ok', {}))}", flush=True)


# ══════════ Akash Chat (chat.akash.network) — §2.24 — میوان: session_token + AI-SDK v5 ══════════
AKA_BASE = "https://chat.akash.network"
AKA_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AKA_LIMIT = {"until": 0.0}
_AKA = {"ses": None, "t": 0.0}
_AKA_NEUTRAL = "You are a helpful assistant. Follow the user's instructions precisely."
_AKA_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _aka_headers():
    return {"User-Agent": AKA_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
            "Origin": AKA_BASE, "Referer": AKA_BASE + "/",
            "sec-fetch-dest": "empty", "sec-fetch-mode": "cors", "sec-fetch-site": "same-origin"}


def _aka_session(force=False):
    """session_token: GET / → GET /api/auth/session → POST refresh (فلۆوی براوزەر)"""
    import time as _t
    if not force and _AKA["ses"] and _t.time() - _AKA["t"] < 43200:
        return _AKA["ses"]
    s = requests.Session()
    s.headers.update(_aka_headers())
    try:
        s.get(AKA_BASE + "/", timeout=(10, 20))
        r = s.get(AKA_BASE + "/api/auth/session", timeout=(10, 20))
        if r.status_code != 200:
            raise EMError(f"aka: session {r.status_code}")
        s.post(AKA_BASE + "/api/auth/session/refresh/", json={}, timeout=(10, 20))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"aka: {str(e)[:60]}")
    _AKA["ses"] = s
    _AKA["t"] = _t.time()
    return s


def aka_chat(messages, model_id="openai-gpt-oss-120b", timeout=110):
    """چاتی akash — سیستەم-پرۆمپت لە مێژوو دەهێنرێت (بەتاڵ = نیوتراڵ)؛ 403 سێشن → ڕۆتەیشن"""
    import time as _t
    if _t.time() < AKA_LIMIT["until"]:
        raise EMError("aka: cooldown")
    sys_content = ""
    rest = []
    for m in messages:
        if m.get("role") == "system" and not sys_content:
            sys_content = m.get("content") or ""
        elif m.get("content"):
            rest.append(m)
    if not sys_content:
        sys_content = _AKA_NEUTRAL
    last_err = None
    for attempt in range(2):
        try:
            s = _AKA["ses"] if (_AKA["ses"] and attempt == 0) else _aka_session(force=(attempt == 1))
        except Exception as e:
            last_err = e
            continue
        cid = "".join(random.choices(_AKA_CHARS, k=12))
        hist = rest[-10:]
        body = {"id": cid,
                "messages": [{"role": m.get("role", "user"), "content": m.get("content") or "",
                              "parts": [{"type": "text", "text": m.get("content") or ""}]} for m in hist],
                "model": model_id, "system": sys_content, "temperature": 0.6, "topP": 0.95, "context": []}
        try:
            r = s.post(AKA_BASE + "/api/chat/", json=body, timeout=(15, timeout), stream=True)
        except Exception as e:
            last_err = EMError(f"aka: {str(e)[:60]}")
            continue
        if r.status_code == 403 or r.status_code == 401:
            _AKA["ses"] = None
            last_err = EMError(f"aka: {r.status_code} سێشن")
            continue
        if r.status_code == 429:
            AKA_LIMIT["until"] = _t.time() + 900
            raise EMError("aka: 429 → دیلی ١٥ خولەک")
        if r.status_code != 200:
            if r.status_code in (400, 500) and model_id in MS.get("aka_ok", {}):
                MS["aka_ok"].pop(model_id, None)
                MS.setdefault("aka_bad", {})[model_id] = {"code": r.status_code, "t": _t.time()}
                _ms_save()
            raise EMError(f"aka: {r.status_code}")
        raw = b""
        try:
            for ch in r.iter_content(512):
                raw += ch
                if len(raw) > 120_000:
                    break
        except Exception:
            pass
        t = raw.decode("utf-8", "replace")
        texts = re.findall(r'^0:"(.*)"', t, re.M)
        try:
            ans = "".join(json.loads(f'"{x}"') for x in texts)
        except Exception:
            ans = "".join(texts)
        ans = ans.strip()
        if ans:
            return ans
        last_err = EMError("aka: وەڵام بەتاڵ")
    raise last_err or EMError("aka: شکست")


def aka_servers():
    out = []
    for mid in list(MS.get("aka_ok", {}).keys())[:6]:
        label = "GPT-OSS 120B" if "gpt-oss" in str(mid) else str(mid).replace("-", " ").title()
        slug = re.sub(r'[^a-z0-9.]+', '-', str(mid).lower()).strip('-')
        out.append({"id": f"aka-{slug}", "name": f"{label} (Akash)",
                    "model_id": mid, "kind": "aka"})
    return out


def sync_akash_models(force=False):
    """ئۆتۆ-ئەپدێتی akash: /api/models گشتی — تەنها دەقی (AkashGen/وێنە دەرباز)؛
       لابراوەکان لە کاتالۆگ خۆکارانە لابرددرێن (یاسای بەکارهێنەر)"""
    import time as _t
    if not force and _t.time() - MS_T.get("aka", 0.0) < 21600:
        return
    MS_T["aka"] = _t.time()
    try:
        r = requests.get(AKA_BASE + "/api/models", headers=_aka_headers(), timeout=(10, 20))
        items = r.json() or []
    except Exception as e:
        print(f"[AKA-SYNC] هەڵە: {str(e)[:70]}", flush=True)
        return
    text_models = {m.get("id") for m in items
                   if m.get("id") and m.get("api_id") and "gen" not in str(m.get("id", "")).lower()
                   and "image" not in str(m.get("description", "")).lower()}
    removed = [mid for mid in list(MS.get("aka_ok", {}).keys()) if mid not in text_models]
    for mid in removed:
        MS["aka_ok"].pop(mid, None)
        print(f"[AKA-SYNC] لابرا: {mid}", flush=True)
    added = 0
    for mid in text_models:
        if mid not in MS.get("aka_ok", {}) and mid not in MS.get("aka_bad", {}):
            try:
                code, ans = (None, None)
                s = _aka_session()
                cid = "".join(random.choices(_AKA_CHARS, k=12))
                body = {"id": cid, "messages": [{"role": "user", "content": "Reply: OK", "parts": [{"type": "text", "text": "Reply: OK"}]}],
                        "model": mid, "system": _AKA_NEUTRAL, "temperature": 0.6, "topP": 0.95, "context": []}
                rr = s.post(AKA_BASE + "/api/chat/", json=body, timeout=(10, 40), stream=True)
                if rr.status_code == 200:
                    MS.setdefault("aka_ok", {})[mid] = {"t": time.time()}
                    added += 1
                    print(f"[AKA-SYNC] نوێ ✅ {mid}", flush=True)
                elif rr.status_code == 429:
                    AKA_LIMIT["until"] = time.time() + 900
                    break
                else:
                    MS.setdefault("aka_bad", {})[mid] = {"code": rr.status_code, "t": time.time()}
            except Exception as e:
                MS.setdefault("aka_bad", {})[mid] = {"err": str(e)[:50], "t": time.time()}
    if added or removed:
        _ms_save()
    print(f"[AKA-SYNC] کاتالۆگ={len(text_models)} | نوێ={added} | لابرا={len(removed)} | aka_ok={len(MS.get('aka_ok', {}))}", flush=True)


# ══════════ Hotbot (www.hotbot.com) — §2.25 — ٤ چات/٥خولەک بە IP (کۆنترۆڵکراو) ══════════
HB_BASE = "https://www.hotbot.com"
HB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
HB_LIMIT = {"until": 0.0}
_HB_SYNC = {"t": 0.0}


def hb_chat(messages, model_id="hotbot-chat", timeout=110):
    """چاتی hotbot — یەک مۆدێڵ؛ ٤ چات بە IP، پاش بەتاڵی 200 → دیلی ٥ خولەک"""
    import time as _t
    if _t.time() < HB_LIMIT["until"]:
        raise EMError("hb: cooldown")
    last = ""
    for m in reversed(messages):
        if m.get("role") == "user" and m.get("content"):
            last = m["content"]
            break
    if not last:
        raise EMError("hb: هیچ پرسیار")
    import uuid as _uuid
    cid = str(_uuid.uuid4())
    try:
        requests.get(HB_BASE + "/", headers={"User-Agent": HB_UA}, timeout=(10, 20))
    except Exception:
        pass
    try:
        rm = requests.post(HB_BASE + "/api/moderate",
                           json={"text": last[-800:], "imageUrls": [], "chatId": cid, "requestType": "text"},
                           headers={"User-Agent": HB_UA, "Content-Type": "application/json",
                                    "Origin": HB_BASE, "Referer": HB_BASE + "/"}, timeout=(10, 20))
        if rm.status_code == 200 and (rm.json() or {}).get("flagged"):
            raise EMError("hb: moderate بلۆک")
    except EMError:
        raise
    except Exception:
        pass
    hist = _sys_keep([{"role": m.get("role", "user"), "content": m.get("content") or ""}
                        for m in messages if m.get("content")], 11)
    try:
        r = requests.post(HB_BASE + "/api/chat",
                          json={"messages": hist, "model": "hotbot-chat", "chatId": cid,
                                "effort": "light", "camp": False},
                          headers={"User-Agent": HB_UA, "Content-Type": "application/json",
                                   "Origin": HB_BASE, "Referer": HB_BASE + "/"},
                          timeout=(15, timeout), stream=True)
    except Exception as e:
        raise EMError(f"hb: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            HB_LIMIT["until"] = _t.time() + 300
        raise EMError(f"hb: {r.status_code}")
    try:
        raw = r.content
    except Exception:
        raw = b""
    t = raw.decode("utf-8", "replace")
    ans_parts = []
    for m2 in re.finditer(r'data: (\{"content":".*?"\})', t):
        try:
            ans_parts.append(json.loads(m2.group(1)).get("content", ""))
        except Exception:
            pass
    ans = "".join(ans_parts).strip()
    if not ans:
        HB_LIMIT["until"] = _t.time() + 300
        raise EMError("hb: بەتاڵ → دیلی ٥ خولەک (کوانتا)")
    return ans


def hb_servers():
    out = []
    if "hotbot-chat" in MS.get("hb_ok", {}) or not MS.get("hb_ok"):
        out.append({"id": "hb-hotbot-chat", "name": "HotBot Chat", "model_id": "hotbot-chat", "kind": "hb"})
    return out


def sync_hb_models(force=False):
    """ئۆتۆ-ئەپدێتی hotbot: پشکنینی زیندوو (٦ کاتژمێر) — مۆدێڵی تاک"""
    import time as _t
    if not force and _t.time() - _HB_SYNC["t"] < 21600:
        return
    _HB_SYNC["t"] = _t.time()
    try:
        a = hb_chat([{"role": "user", "content": "Reply with: OK"}], timeout=45)
        if a:
            if "hotbot-chat" not in MS.get("hb_ok", {}):
                MS.setdefault("hb_ok", {})["hotbot-chat"] = {"t": _t.time()}
                _ms_save()
            print("[HB-SYNC] hotbot زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[HB-SYNC] {str(e)[:70]}", flush=True)


# ══════════ GadegetKit (gadegetkit.com) — §2.26 — glm-4-flash، signature-flow، بێ لیمیت دیارکراو ══════════
GK_BASE = "https://www.gadegetkit.com"
GK_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
GK_LIMIT = {"until": 0.0}
_GK_SYNC = {"t": 0.0}


def gk_chat(messages, model_id="glm-4-flash", timeout=150):
    """چاتی gadegetkit — generate-signature ← ai-text/chat (سیستەم-پرۆمپت لە messages)"""
    import time as _t
    if _t.time() < GK_LIMIT["until"]:
        raise EMError("gk: cooldown")
    hist = _sys_keep([{"role": m.get("role", "user"), "content": m.get("content") or ""}
                        for m in messages if m.get("content")], 15)
    if not hist:
        raise EMError("gk: هیچ نامە")
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": GK_UA, "Content-Type": "application/json",
                          "Origin": GK_BASE, "Referer": GK_BASE + "/ai-tools/chatbot"})
        s.get(GK_BASE + "/ai-tools/chatbot", timeout=(10, 25))
        ts = str(int(_t.time() * 1000))
        rs = s.post(GK_BASE + "/api/internal/generate-signature",
                    json={"timestamp": int(ts), "path": "/api/ai-text/chat"}, timeout=(10, 25))
        sig = (rs.json() or {}).get("signature")
        if not sig:
            raise EMError("gk: signature نییە")
        r = s.post(GK_BASE + "/api/ai-text/chat", json={"messages": hist, "locale": "en"},
                   headers={"x-timestamp": ts, "x-signature": sig}, timeout=(15, timeout))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"gk: {str(e)[:60]}")
    if r.status_code != 200:
        if r.status_code == 429:
            GK_LIMIT["until"] = _t.time() + 600
        raise EMError(f"gk: {r.status_code}")
    try:
        j = r.json()
    except Exception:
        raise EMError("gk: parse")
    ans = (j.get("text") or "").strip()
    if not ans or not j.get("success"):
        raise EMError("gk: وەڵام بەتاڵ")
    return ans


def gk_servers():
    out = []
    if "glm-4-flash" in MS.get("gk_ok", {}) or not MS.get("gk_ok"):
        out.append({"id": "gk-glm-4-flash", "name": "GLM 4 Flash (GK)", "model_id": "glm-4-flash", "kind": "gk"})
    return out


def sync_gk_models(force=False):
    """ئۆتۆ-ئەپدێتی gadegetkit: پشکنینی زیندوو (٦ کاتژمێر)"""
    import time as _t
    if not force and _t.time() - _GK_SYNC["t"] < 21600:
        return
    _GK_SYNC["t"] = _t.time()
    try:
        a = gk_chat([{"role": "user", "content": "Reply with: OK"}], timeout=60)
        if a:
            if "glm-4-flash" not in MS.get("gk_ok", {}):
                MS.setdefault("gk_ok", {})["glm-4-flash"] = {"t": _t.time()}
                _ms_save()
            print("[GK-SYNC] gadegetkit زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[GK-SYNC] {str(e)[:70]}", flush=True)


# ══════════ GizAI (giz.ai) — §2.27 — کوانتا بۆ هەر مۆدێڵ ~١ کاتژمێر (بەکارهێنەر: لیمیت مەیەڵە) ══════════
GZ_BASE = "https://www.giz.ai"
GZ_CDN = "https://cdnwww.giz.ai/api/model/choices/textGeneration"
GZ_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
# ناسنامەی نەناسراو (کوکی pfb9) — سەرڤەر بەند بە IP نییە
GZ_PFB9 = "c7380813ca955a386914044983fbcf6a082dbf2bea2eb91917b37ba33d6ff05b"
GZ_SKIP = {"dynamic"}  # dynamic لە ڕێپلەی 400 دەدات (resolve ی session ی وێب دەوێت)
GZ_COOLDOWN = {"quota": 3700.0, "login": 3700.0}  # 401 = دوای کوانتاش دێتەوە → کاتژمێر
_GZ_BADC = {}  # model → cooldown تا
_GZ_SYNC = {"t": 0.0, "thread": None, "labels": {}}


def _gz_rid(n):
    import secrets as _sc, string as _st
    return "".join(_sc.choice(_st.ascii_letters + _st.digits + "-_") for _ in range(n))


def gz_chat(messages, model_id, timeout=110):
    """چاتی GizAI — session ی نەناسراو ← infer → {"status":"completed","output":…}"""
    import time as _t
    if _t.time() < _GZ_BADC.get(model_id, 0):
        raise EMError("gz: cooldown")
    hist = _sys_keep([{"type": (m.get("role") or "user"), "content": m.get("content") or ""}
                        for m in messages if m.get("content")], 11)
    if not hist:
        raise EMError("gz: هیچ نامە")
    try:
        s = requests.Session()
        s.headers.update({"User-Agent": GZ_UA, "Content-Type": "application/json",
                          "Origin": GZ_BASE, "Referer": GZ_BASE + "/assistant?mode=chat&baseModel=dynamic"})
        s.cookies.set("pfb9", GZ_PFB9, domain="www.giz.ai")
        r0 = s.post(GZ_BASE + "/api/data/spaces/spaceServer.createAnonymousSession",
                    json={"visitorId": _gz_rid(32), "session": {"mode": "chat", "shared": False,
                          "modeInput": {"baseModel": "dynamic", "settings": {"character": "AI", "responseMode": "text"},
                          "reasoning": {"level": "low", "mode": "default"}, "context": "general",
                          "reference": "auto", "showChoices": False}}}, timeout=(10, 25))
        sid = (r0.json() or {}).get("sessionId") if r0.status_code in (200, 201) else None
        if not sid:
            raise EMError(f"gz: session {r0.status_code}")
        inst = _gz_rid(21)
        inf = {"model": model_id,
               "input": {"messages": hist, "sessionId": sid, "mode": "chat",
                         "settings": {"character": "AI", "responseMode": "text"}, "context": "general"},
               "subscribeId": _gz_rid(22), "instanceId": inst}
        r = s.post(GZ_BASE + "/api/data/users/inferenceServer.infer", json=inf,
                   headers={"x-giz-instance-id": inst}, timeout=(15, timeout))
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"gz: {str(e)[:60]}")
    if r.status_code == 429:
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["quota"]
        raise EMError("gz: کوانتای مۆدێڵ (~١ کاتژمێر)")
    if r.status_code == 401:
        _GZ_BADC[model_id] = _t.time() + GZ_COOLDOWN["login"]
        raise EMError("gz: لۆگین-واڵ")
    if r.status_code != 201 and r.status_code != 200:
        raise EMError(f"gz: {r.status_code}")
    try:
        j = r.json()
    except Exception:
        raise EMError("gz: parse")
    if (j.get("status") or "completed") != "completed":
        raise EMError(f"gz: status={j.get('status')}")
    ans = (j.get("output") or "").strip()
    if not ans:
        raise EMError("gz: وەڵام بەتاڵ")
    return ans


def _gz_slug(v):
    import re as _re
    sl = _re.sub(r"[^a-zA-Z0-9]+", "-", v).strip("-").lower()
    return sl[:60] or "model"


def gz_servers():
    out = []
    for v, lbl in sorted(_GZ_SYNC.get("catalog", {}).items()):
        out.append({"id": f"gz-{_gz_slug(v)}", "name": f"{lbl} (Giz)", "model_id": v, "kind": "gz"})
    return out


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


def _gz_parse_catalog(t):
    """#91A6: safe-wrapper — parser هەرگیز sync ەک ناکوژێنێت"""
    try:
        return _gz_parse_catalog__raw(t)
    except Exception:
        return None

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


# ══════════ Pi (pi.ai) — §2.28 — curl_cffi (CF-impersonate) + SSE partial ══════════
PI_BASE = "https://pi.ai"
PI_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
PI_STATE = {"s": None, "did": None}
PI_LIMIT = {"until": 0.0}
_PI_SYNC = {"t": 0.0}


def _pi_headers():
    return {"Origin": PI_BASE, "Referer": PI_BASE + "/talk", "x-api-version": "5",
            "x-client-timezone": "UTC", "User-Agent": PI_UA}


def _pi_session():
    """نشستی curl_cffi — بەکارهێنەری نەناسراو (chat/start + legal-accept)"""
    from curl_cffi import requests as _cr
    import uuid as _u
    s = _cr.Session(impersonate="chrome")
    did = str(_u.uuid4())
    r = s.post(PI_BASE + "/api/chat/start",
               json={"distinctId": did, "deviceFingerprint": "pnjfnj"},
               headers=_pi_headers(), timeout=(15, 30))
    if r.status_code != 200:
        raise EMError(f"pi: start {r.status_code}")
    r2 = s.post(PI_BASE + "/api/user/legal-accept",
                json={"name": "Yusf", "ageVerified": True,
                      "useDataToImproveModelsConsent": True,
                      "useEmotionRecognitionOnVoiceConsent": True},
                headers=_pi_headers(), timeout=(15, 30))
    PI_STATE["s"] = s
    PI_STATE["did"] = did
    return s, did


def pi_chat(messages, model_id="pi-chat", timeout=50):  # #94U19: 110→50 (stream-hang)
    """چاتی Pi — مێژوو فلێت دەکرێت بۆ یەک دەق؛ SSE partial → یەک وەڵام"""
    import time as _t, uuid as _u, json as _j
    if _t.time() < PI_LIMIT["until"]:
        raise EMError("pi: cooldown")
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("pi: هیچ نامە")
    lines.append("[Assistant]")
    text = _flat_cut(lines)
    import re as _re
    text = _re.sub(r"\[User\]\s*\[Assistant\]", "", text)
    last = ""
    for attempt in (1, 2):
        try:
            s = PI_STATE.get("s")
            did = PI_STATE.get("did")
            if s is None:
                s, did = _pi_session()
            r = s.post(PI_BASE + "/api/v2/chat",
                       json={"text": text, "conversation": "",
                             "eqDistinctId": did, "eqSessionId": str(_u.uuid4()),
                             "clientId": str(_u.uuid4())},
                       headers=_pi_headers(), timeout=(15, timeout), stream=True)
            if r.status_code in (401, 403, 429) and attempt == 1:
                PI_STATE["s"] = None
                if r.status_code == 429:
                    PI_LIMIT["until"] = _t.time() + 300
                continue
            if r.status_code != 200:
                raise EMError(f"pi: {r.status_code}")
            parts = []
            buf = ""
            _dl = _t.time() + min(timeout, 60)
            for ch in r.iter_content(chunk_size=None):
                if _t.time() > _dl:
                    break  # #94U19: دێدلاینی stream — نەهێشتنی گیربوون
                buf += ch.decode("utf-8", "replace")
                while "\n" in buf:
                    ln, buf = buf.split("\n", 1)
                    ln = ln.strip()
                    if ln.startswith("data:"):
                        try:
                            d = _j.loads(ln[5:].strip())
                            t2 = d.get("text")
                            if isinstance(t2, str):
                                parts.append(t2)
                        except Exception:
                            pass
            last = "".join(parts).strip()
            if last:
                return last
            # بەتاڵ — ئەگەر trial تەواو بووە، نشستی نوێ
            PI_STATE["s"] = None
            continue
        except EMError:
            raise
        except Exception as e:
            PI_STATE["s"] = None
            if attempt == 2:
                raise EMError(f"pi: {str(e)[:60]}")
    if last:
        return last
    raise EMError("pi: وەڵام بەتاڵ")


def pi_servers():
    out = []
    if "pi-chat" in MS.get("pi_ok", {}) or not MS.get("pi_ok"):
        out.append({"id": "pi-pi-chat", "name": "Pi (pi.ai)", "model_id": "pi-chat", "kind": "pi"})
    return out


def sync_pi_models(force=False):
    """ئۆتۆ-ئەپدێتی Pi: چاتی تاقیکردنەوە (٦ کاتژمێر) — بەکارهێنەری نوێ = کوانتای نوێ"""
    import time as _t
    if not force and _t.time() - _PI_SYNC["t"] < 21600:
        return
    _PI_SYNC["t"] = _t.time()
    try:
        PI_STATE["s"] = None  # نشستی نوێ = بەکارهێنەری نوێ
        a = pi_chat([{"role": "user", "content": "Reply with: OK"}], timeout=60)
        if a:
            if "pi-chat" not in MS.get("pi_ok", {}):
                MS.setdefault("pi_ok", {})["pi-chat"] = {"t": _t.time()}
                _ms_save()
            print("[PI-SYNC] pi زیندووە ✅", flush=True)
    except Exception as e:
        print(f"[PI-SYNC] {str(e)[:70]}", flush=True)


# ══════════ ChatbotApp (chat.chatbotapp.ai) — §2.29 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
CB_KEY = "AIzaSyBQLxwsoGGyo0DOI-P8IdRWDAE401me8E8"
CB_BASE = "https://api.chatbotapp.ai"
CB_CMS = "https://webcms.chatbotapp.ai/api/ai-models?populate[]=tags&populate[]=examples&populate[]=suggestions&pagination[pageSize]=100"
CB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
CB_ACC_FILE = os.path.join(DATA_DIR, "cb_accounts.json")
CB_FREE_BOTS = {104: "4o-mini", 107: "gpt-4.1-mini", 113: "gpt-5.1", 117: "gpt-5.4-mini",
                200: "gemini-2.5-flash", 202: "gemini-3-flash", 204: "gemini-3.1-flash-lite",
                301: "deepSeek", 302: "deepseek-v4-flash", 502: "claude-4.5-haiku"}
CB_HTTP400_BOTS = {115, 501, 123, 14}  # پێویستیان بە پارامەتری جیاواز
CB_ST = {"tok": None, "uid": None, "tok_t": 0.0, "idx": 0, "next_num": 82412,
         "exhausted": {}, "ensured": {}, "signups": {"date": "", "n": 0}}
_CB_SYNC = {"t": 0.0}
# ئامرازەکان کە چاتی دەقی نین — دەرکراو
CB_SKIP_KEYS = {"link-and-ask", "music-generation", "document", "editor", "ai-search", "superbot", "aiapp", "chatbotapp", "youtube-summarizer", "image-generator", "logo-generator", "tattoo-generator"}


def _cb_load_acc():
    import json as _j
    try:
        d = _json_load_safe(CB_ACC_FILE) or {}
        CB_ST["accounts"] = d.get("accounts") or []
        CB_ST["idx"] = int(d.get("idx") or 0)
        CB_ST["next_num"] = int(d.get("next_num") or 82400)
        CB_ST["exhausted"] = d.get("exhausted") or {}
        CB_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        CB_ST["accounts"] = []


def _cb_save_acc():
    with _SAVE_LOCK:
        return _cb_save_acc__impl()


def _cb_save_acc__impl():
    import json as _j
    try:
        _json_save(CB_ACC_FILE, {"accounts": CB_ST.get("accounts") or [], "idx": CB_ST["idx"],
                                 "next_num": CB_ST["next_num"], "exhausted": CB_ST.get("exhausted") or {},
                                 "signups": CB_ST.get("signups") or {"date": "", "n": 0}})
    except Exception:
        pass


_cb_load_acc()


def _cb_firebase(ep, email, pw):
    import time as _t
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={CB_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": CB_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json()
    tok = j.get("idToken")
    if not tok:
        return None
    import base64 as _b
    p = tok.split(".")[1]
    p += "=" * (-len(p) % 4)
    try:
        uid = _b.urlsafe_b64decode(p).decode("utf-8", "replace")
        uid = json.loads(uid).get("user_id") or ""
    except Exception:
        uid = ""
    return tok, uid


def _cb_cur_acc():
    acc = getattr(_TLS, "cb_acc", None)  # #94U21: لیسی ئەم تڕێدە پێشینەی هەیە
    if acc:
        return acc
    accs = CB_ST.get("accounts") or []
    if not accs:
        return None
    return accs[CB_ST["idx"] % len(accs)]


def _cb_signup_new(force=False):  # #94U24: force = جێگۆڕکێ — healthy-gate بازدەدات (بودجە+سەقف هەر ماوە)
    """#94U35: ئەکاونتی نوێ — سایزی CA (مۆڵەتی بەکارهێنەر؛ #94U34 breaker دژە-سووتان چالاکە)"""
    import time as _t, datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = CB_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    _cb_n = len(CB_ST.get("accounts") or [])
    _ex = CB_ST.get("exhausted", {}) or {}
    _now = time.time()
    _healthy = 0
    for _a in (CB_ST.get("accounts") or []):  # #94U32b: cooldown-aware (وەک NV + /health)
        try:
            _ok = float(_ex.get(_a.get("email"), 0) or 0) <= _now
        except Exception:
            _ok = str(_ex.get(_a.get("email"), 0))[:10] != today
        if _ok:
            _healthy += 1
    if _cb_n >= 10000 or (not force and _healthy >= 1000):  # #94U35: وەک CA (مۆڵەتی بەکارهێنەر + breaker)
        return None
    if not _sg_breaker_allow(CB_KEY):  # #94U34
        return None
    if not _sg_reserve(CB_ST, 10000, today, _CB_LK):  # #94U23 بودجە لەژێر لۆک؛ #94U35: →10000 (مۆڵەتی بەکارهێنەر؛ breaker دەیپارێزێت)
        return None
    n = CB_ST["next_num"] + random.randint(0, 3000)  # #94U32 jitter دژە-دەستنیشان
    for pref in ("komex", "bexud"):  # #94U32: 2 پریفیکس
        for off in (0, 3, 13, 40, 100, 250):
            email = f"{pref}{n + off}@duidir.com"
            pw = f"{email}#{random.randint(10000, 99999)}"
            res = _fb_signup(CB_KEY, email, pw, _rand_ua())
            if res:
                CB_ST["accounts"] = (CB_ST.get("accounts") or []) + [{"email": email, "password": pw, "ua": _rand_ua()}]
                CB_ST["idx"] = len(CB_ST["accounts"]) - 1
                CB_ST["next_num"] = n + off + 1
                _cb_save_acc()
                CB_ST["tok"] = None
                print(f"[CB] ئەکاونتی نوێ ✅ {email}", flush=True)
                return res
            _t.sleep(random.uniform(0.5, 1.5))  # #94U32 jitter
    CB_ST["next_num"] = n + 300
    _cb_save_acc()
    print(f"[CB] هیچ شوێن — بازدا بۆ {CB_ST['next_num']}", flush=True)
    return None


def _cb_token():
    import time as _t
    acc = getattr(_TLS, "cb_acc", None)
    if acc is None:
        try:
            _cb_rotate()  # #94U21: یەکەم داوا → لیسی خۆی لەژێر لۆک
        except Exception:
            pass
        acc = getattr(_TLS, "cb_acc", None) or _cb_cur_acc()
    if not acc:
        res = _cb_signup_new()
        if not res:
            raise EMError("cb: هیچ ئەکاونت")
        try:
            _na = (CB_ST.get("accounts") or [])[-1]
            _TLS.cb_acc = _na
            with _CB_LK:
                CB_ST.setdefault("toks", {})[_na.get("email")] = (res[0], res[1], _t.time())
        except Exception:
            pass
        return res
    em = acc.get("email")
    with _CB_LK:
        c = (CB_ST.get("toks") or {}).get(em)
    if c and _t.time() - c[2] < 2700:
        return c[0], c[1]
    res = _cb_firebase("signInWithPassword", acc["email"], acc["password"])
    if not res:
        # ئەکاونتەکە نییە — دواتری
        raise EMError("cb: sign-in شکات")
    with _CB_LK:
        CB_ST.setdefault("toks", {})[em] = (res[0], res[1], _t.time())
    return res


def _cb_rotate():
    """ئەکاونتی دواتر — ئەگەر هەمووی تەواو بوو → ئەکاونتی نوێ"""
    accs = CB_ST.get("accounts") or []
    if not accs:
        res = _cb_signup_new()
        return bool(res)
    chosen = None
    with _CB_LK:
        for _ in range(len(accs)):
            CB_ST["idx"] = (CB_ST["idx"] + 1) % len(accs)
            acc = accs[CB_ST["idx"]]
            _exv = CB_ST.get("exhausted", {}).get(acc["email"], 0)
            try:
                _dead = float(_exv) > time.time()  # #94U24: cooldown-until (وەک NV)
            except Exception:
                _dead = str(_exv)[:10] == __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d")
            if _dead:
                continue
            chosen = acc
            break
    if chosen is not None:
        _TLS.cb_acc = chosen
        CB_ST["tok"] = None
        _cb_save_acc()
        return True
    # هەموو ئەم ڕۆژە تەواون → ئەکاونتی نوێ
    res = _cb_signup_new()
    if res:
        try:
            _TLS.cb_acc = (CB_ST.get("accounts") or [])[-1]
        except Exception:
            pass
        return True
    _cb_save_acc()
    return False


def _cb_slug(v):
    import re as _re
    sl = _re.sub(r"[^a-zA-Z0-9]+", "-", v).strip("-").lower()
    return sl[:60] or "model"


def cb_chat(messages, model_id, timeout=110):
    """چاتی ChatbotApp — مێژوو فلێت + حەوزی ئەکاونت + SSE parts"""
    import time as _t, uuid as _u
    meta = (MS.get("cb_ok") or {}).get(model_id)
    if not meta:
        raise EMError("cb: مۆدێڵ نییە")
    bot_id = meta.get("botId") or 120
    tier = meta.get("tier") or "f"
    if tier == "x":
        max_att = 1
    else:
        max_att = min(len(CB_ST.get("accounts") or [1]) + 1, 8)
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("cb: هیچ نامە")
    lines.append("[Assistant]")
    prompt = _flat_cut(lines)
    last_err = ""
    for attempt in range(max_att):
        try:
            tok, uid = _cb_token()
        except EMError:
            if not _cb_rotate():
                raise
            continue
        H = {"User-Agent": CB_UA, "Content-Type": "application/json", "accept": "text/event-stream",
             "x_token": tok, "x_user_id": uid, "x_platform": "web", "x_model": str(bot_id),
             "Origin": "https://chat.chatbotapp.ai", "Referer": "https://chat.chatbotapp.ai/"}
        body = {"botId": bot_id, "sessionId": _u.uuid4().hex[:20],
                "userPseudoId": f"{_u.uuid4().int % 10 ** 9}.{int(_t.time())}",
                "hubxId": str(_u.uuid4()),
                "message": {"prompt": prompt, "messageId": str(_u.uuid4())},
                "actions": {"webSearch": False, "createImage": False, "deepSearch": False, "privateSearch": False}}
        try:
            r = requests.post(CB_BASE + "/api/v2/chat", json=body, headers=H,
                              timeout=(15, timeout), stream=True)
        except Exception as e:
            raise EMError(f"cb: {str(e)[:60]}")
        if r.status_code != 200:
            raw = b""
            try:
                for ch in r.iter_content(chunk_size=None):
                    raw += ch
                    if len(raw) > 300:
                        break
            except Exception:
                pass
            msg = ""
            try:
                msg = (json.loads(raw.decode("utf-8", "replace")).get("data") or {}).get("message", "")
            except Exception:
                msg = raw[:60].decode("utf-8", "replace")
            last_err = msg or str(r.status_code)
            if "Insufficient chat credit" in msg:
                if tier == "x":
                    raise EMError("cb: پرێمیۆمی-قورس — بە پارە بەردەستە")
                import datetime as _dt
                acc = _cb_cur_acc()
                if acc:
                    CB_ST.setdefault("exhausted", {})[acc["email"]] = _t.time() + 86000  # #94U24: وەک NV — cooldown-until (24h)
                    _replace_dead_soon("cb")  # #94U24: لە جێی ئەمە → نوێ یەکسەر
                if not _cb_rotate():
                    raise EMError("cb: کرێدیت هەموو ئەکاونتەکان")
                continue
            if "No agent mapping" in msg:
                MS.setdefault("cb_bad", {})[model_id] = {"t": _t.time(), "why": "no-mapping"}
                MS.get("cb_ok", {}).pop(model_id, None)
                _ms_save()
                raise EMError("cb: مۆدێڵ نەماوە")
            raise EMError(f"cb: {last_err[:60]}")
        parts = []
        agent = ""
        for line in r.iter_lines(decode_unicode=True):
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            dd = d.get("data") or {}
            if isinstance(dd, dict):
                if dd.get("agent_id"):
                    agent = dd["agent_id"]
                c = dd.get("content")
                if isinstance(c, dict) and c.get("parts"):
                    for p in c["parts"]:
                        if isinstance(p, dict) and p.get("thought"):
                            continue  # پارچەی بیرکردنەوە
                        parts.append((p or {}).get("text", "") if isinstance(p, dict) else str(p))
        # پترن: دێڵتا زیادەکان + ڕووداوی کۆتایی-کۆکراو (وەک Nova §2.32)
        if len(parts) > 1 and parts[-1].startswith("".join(parts[:-1])):
            ans = parts[-1].strip()
        else:
            ans = "".join(parts).strip()
        if ans:
            return ans
        last_err = "بەتاڵ"
        _tok_drop("cb")
        CB_ST["tok"] = None
    raise EMError(f"cb: {last_err[:60] or 'شکست'}")


def cb_servers():
    out = []
    for k, meta in sorted((MS.get("cb_ok") or {}).items()):
        out.append({"id": f"cb-{_cb_slug(k)}", "name": f"{(meta or {}).get('label') or k} (CB)",
                    "model_id": k, "kind": "cb"})
    return out


def sync_cb_models(force=False):
    """ئۆتۆ-ئەپدێتی ChatbotApp: کاتالۆگی webcms (٦ کاتژمێر) — تەنها دەقی بە botId"""
    import time as _t
    if not force and _t.time() - _CB_SYNC["t"] < 21600:
        return
    _CB_SYNC["t"] = _t.time()
    try:
        r = requests.get(CB_CMS, headers={"User-Agent": CB_UA, "Origin": "https://chat.chatbotapp.ai",
                                          "Referer": "https://chat.chatbotapp.ai/"}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[CB-SYNC] catalog {r.status_code}", flush=True)
            return
        items = (r.json() or {}).get("data") or []
        ok = {}
        for m in items:
            k = (m or {}).get("modelKey") or ""
            if not k or k in CB_SKIP_KEYS:
                continue
            if (m.get("type") or "") != "text":
                continue
            b = m.get("botId")
            if not isinstance(b, int) or b <= 0 or b in CB_HTTP400_BOTS:
                continue
            # #76: تەنها بۆتە بەخۆڕاییەکان (CB_FREE_BOTS) — heavy/پارەدار لە مێنیو لابردن
            if b not in CB_FREE_BOTS:
                continue
            tier = "f"
            lbl = CB_FREE_BOTS.get(b) or m.get("title") or k
            if lbl.startswith("models."):
                lbl = k
            ok[k] = {"botId": b, "label": lbl, "tier": tier}
        MS["cb_ok"] = ok
        _ms_save()
        print(f"[CB-SYNC] کاتالۆگ {len(items)} → تۆمارکراو {len(ok)}", flush=True)
    except Exception as e:
        print(f"[CB-SYNC] {str(e)[:80]}", flush=True)


# ══════════ ChatbotAI (chatbotai.co) — §2.30 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
CA_KEY = "AIzaSyDHatafp1HL1DKD0Id1UVHPGQY8m_eseAk"
CA_BASE = "https://chatbotai.co"
CA_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
CA_ACC_FILE = os.path.join(DATA_DIR, "ca_accounts.json")
CA_ST = {"tok": None, "tok_t": 0.0, "idx": 0, "next_num": 82401,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82400@duidir.com", "password": "komex82400@duidir.com"}],
         "limits": {}, "signups": {"date": "", "n": 0}}
_CA_SYNC = {"t": 0.0}
# کاتالۆگی بنەڕەتی — sync ی خۆکار لە HTML ی ماڵپەر نوێی دەکاتەوە (key → version, label)
CA_FALLBACK = {
    "gpt-5.4-nano": ("gpt-5.4-nano", "GPT-5.4 Nano"),
    "gpt-5.4-instant": ("gpt-5.4-instant-2026-03-05", "GPT-5.4 Instant"),
    "gemini-3.1-pro": ("gemini-3.1-pro-preview", "Gemini 3.1 Pro"),
    "claude": ("claude-sonnet-5", "Claude Sonnet 5"),
    "perplexity": ("sonar", "Perplexity"),
    "deepseek": ("deepseek-4-pro-0813", "DeepSeek-V4-Pro"),
    "grok": ("grok-4.6", "Grok 4.6"),
    "claude-fable": ("claude-fable-5-1", "Claude Fable 5.1"),
    "claude-opus": ("claude-opus-5", "Claude Opus 5"),
    "gemini": ("gemini-3.8-flash", "Gemini 3.8 Flash"),
    "gpt-5.6-sol": ("gpt-5.6-sol", "GPT-5.6 Sol"),
    "gpt-5.6-terra": ("gpt-5.6-terra", "GPT-5.6 Terra"),
    "gpt-5.6-luna": ("gpt-5.6-luna", "GPT-5.6 Luna"),
    "gpt-6-astra": ("gpt-6-astra", "GPT-6 Astra"),
    "gpt-5.5": ("gpt-5.5-2026-04-23", "GPT-5.5"),
    "kimi": ("kimi-k3", "Kimi K3"),
    "kimi-k2.6": ("kimi-k2.6", "Kimi K2.6"),
    "kimi-k3-thinking": ("kimi-k3-thinking", "Kimi K3 Thinking"),
    "deepseek-v4-pro-thinking": ("deepseek-4-pro-0813-thinking", "DeepSeek-V4-Pro Thinking"),
    "o3": ("o3-2025-04-16", "OpenAI o3"),
    "llama": ("llama-4-maverick", "Llama 4"),
    "gpt-4": ("gpt-4o-2024-08-06", "GPT-4o"),
    "gpt-4o-mini": ("gpt-4o-mini-2024-07-18", "GPT-4o-mini"),
    "gpt-4.1": ("gpt-4.1-2025-04-14", "GPT-4.1"),
}


def _ca_load_acc():
    import json as _j
    try:
        d = _json_load_safe(CA_ACC_FILE) or {}
        CA_ST["accounts"] = d.get("accounts") or CA_ST["accounts"]
        CA_ST["idx"] = int(d.get("idx") or 0)
        CA_ST["next_num"] = int(d.get("next_num") or 82401)
        CA_ST["limits"] = d.get("limits") or {}
        CA_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _ca_save_acc():
    with _SAVE_LOCK:
        return _ca_save_acc__impl()


def _ca_save_acc__impl():
    import json as _j
    try:
        _json_save(CA_ACC_FILE, {"accounts": CA_ST.get("accounts") or [], "idx": CA_ST["idx"],
                                 "next_num": CA_ST["next_num"], "limits": CA_ST.get("limits") or {},
                                 "signups": CA_ST.get("signups") or {"date": "", "n": 0}})
    except Exception:
        pass


_ca_load_acc()


def _ca_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={CA_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": CA_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    tok = (r.json() or {}).get("idToken")
    return (tok, "") if tok else None


def _ca_signup_new(mkey=None, force=False):  # #94U24: force = جێگۆڕکێ
    # #94U16: mkey → ژمارەکردنی زیندوو تەنها بۆ ئەو مۆدێڵە (چارەی deadlock ی «هەموو ئەکاونتەکان limit»)
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = CA_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    # #94U31 CA-FORTRESS: 10000/ڕۆژ + حەوز 10k + 1000 زیندووی بەردەوام (مۆڵەتی بەکارهێنەر 2026-09-21)
    _accs_n = len(CA_ST.get("accounts") or [])
    _today_s = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    _lim = CA_ST.get("limits") or {}
    if mkey:
        _alive = sum(1 for _a in (CA_ST.get("accounts") or [])
                     if not _lim_hit((_lim.get(_a.get("email") or "?") or {}), mkey))
    else:
        _alive = sum(1 for _a in (CA_ST.get("accounts") or [])
                     if _today_s not in (_lim.get(_a.get("email") or "?") or {}).values())
    if _accs_n >= 10000 or (not force and _alive >= 1000):  # #94U31: هەتا 1000 زیندوو نەبێت بەردەوامبە
        return None
    if not _sg_breaker_allow(CA_KEY):  # #94U34: کلیل لە پشوودایە — بودجە مەسووتێنە
        return None
    if not _sg_reserve(CA_ST, 10000, today, _CA_LK):  # #94U23 بودجە لەژێر لۆک؛ #94U31: →10000/ڕۆژ بە مۆڵەتی بەکارهێنەر
        return None
    n = CA_ST["next_num"] + random.randint(0, 5000)  # #94U31: ژمارەی نا-ڕێزبەند دژە-دەستنیشان
    # سکانی بازدان — شوێنی بەتاڵی زوو بدۆزەوە
    offs = (0, 3, 13, 40, 100, 250)
    for pref in ("komex", "heal", "arez", "hiva"):  # #94U31: 4 پریفیکس بۆ جیاوازی
        for off in offs:
            email = f"{pref}{n + off}@duidir.com"
            pw = f"{email}#{random.randint(10000, 99999)}"  # #94U31: وشەی نهێنی هەڕەمەکی
            res = _fb_signup(CA_KEY, email, pw, _rand_ua())  # #94U31: UA هەڕەمەکی بۆ هەر هەوڵێک
            if res:
                CA_ST["accounts"] = (CA_ST.get("accounts") or []) + [{"email": email, "password": pw, "ua": _rand_ua()}]
                CA_ST["idx"] = len(CA_ST["accounts"]) - 1
                CA_ST["next_num"] = n + off + 1
                CA_ST["tok"] = None
                _ca_save_acc()
                print(f"[CA] ئەکاونتی نوێ ✅ {email}", flush=True)
                return res
            time.sleep(random.uniform(0.3, 1.0))  # #94U31: jitter لەنێوان هەوڵەکاندا
    CA_ST["next_num"] = n + 300
    _ca_save_acc()
    print(f"[CA] هیچ شوێن — بازدا بۆ {CA_ST['next_num']}", flush=True)
    return None


# ════════ #82/#83: حەوزی ئەکاونت — هەرسێکە (CA+CB+NV) — ٥٠ بۆ هەر یەکێک + پرۆکسی ════════
_SAVE_LOCK = threading.Lock()  # نووسینی هاوبەشی فایلەکان — تەردی چات + دیمۆن
PROXY_ST = {"list": [], "src_t": 0.0, "bad": set(), "pool": {}, "raw": [], "cur": 0}
_PROXY_GET_STATE = {"loaded": False}
_PROXY_FETCH_LOCK = threading.Lock()  # #94U17: تەنها ١ شەپۆلی fetch+screen لە هەمان کات


_PROXY_TEST = {"url": "https://identitytoolkit.googleapis.com/", "timeout": 6}
# #91P: ئامانجەکانی تاقیکردنەوە — پرۆکسی دەبێت لانیکەم ٢ لە ٣ ببات
_PROXY_TARGETS = [
    "https://identitytoolkit.googleapis.com/",
    "http://www.google.com/generate_204",
    "https://cloudflare.com/cdn-cgi/trace",
]


def _proxy_fetch_all():
    """#91P: هەموو سەرچاوە بەقوەتەکان — لیستە ئاشکراکان + API ەکان (هەندان+وێبشەیر ئەگەر تۆکەن هەبێت)"""
    raw = []
    urls = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&timeout=8000",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-LIST/master/http.txt",
        "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        "https://raw.githubusercontent.com/vakhov/fresh-proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        "https://www.proxy-list.download/api/v1/get?type=http",
        "https://proxyspace.pro/http.txt",
        "https://openproxylist.xyz/http.txt",
        "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/http_proxies.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/http.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/https/data.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/http.txt",
        "https://raw.githubusercontent.com/zloi-user/hideip.me/main/https.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
        "https://raw.githubusercontent.com/mmpx12/proxy-list/master/https.txt",
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
        "https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/https.txt",
        "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-https.txt",
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        "https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/http/http.txt",
    ]  # #94U39: +3 (17 HTTP)؛ #94U41: +9 (26 HTTP)
    def _pull(u):
        try:
            r = requests.get(u, timeout=(8, 16))
            if r.status_code == 200:
                return [x.strip() for x in r.text.split() if 6 < len(x.strip()) < 60]
        except Exception:
            pass
        return []
    ths = [threading.Thread(target=lambda u=u: raw.extend(_pull(u))) for u in urls]
    for t in ths:
        t.start()
    for t in ths:
        t.join(20)
    # Geonode API — JSON، گەورەترین سەرچاوە (HTTP + HTTPS)
    try:
        r = requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=http%2Chttps&limit=500&sort_by=lastChecked&sort_type=desc", timeout=(8, 16))
        if r.status_code == 200:
            for x in (r.json() or {}).get("data") or []:
                raw.append(f"{x.get('ip')}:{x.get('port')}")
    except Exception:
        pass
    # #91K: سۆکسی — SOCKS5 + SOCKS4 (کەمتر بلۆک دەکرێن — پارێزراو) — بە تاگی scheme
    socks_raw = []
    for u, sch in (("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt", "socks4://"),
                   ("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks4.txt", "socks4://"),
                   ("https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks5.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/saschazesiger/Free-Proxies/master/proxies/socks4.txt", "socks4://"),
                   ("https://raw.githubusercontent.com/mmpx12/proxy-list/master/socks5.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks5/data.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks5_proxies.txt", "socks5://"),
                   ("https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&timeout=8000", "socks5://"),
                   ("https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/socks4/data.txt", "socks4://"),
                   ("https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/generated/socks4_proxies.txt", "socks4://"),
                   ("https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt", "socks5://"),
                   ("https://raw.githubusercontent.com/officialputuid/KangProxy/KangProxy/socks5/socks5.txt", "socks5://")):  # #94U39: +7؛ #94U41: +4 (15 SOCKS)
        try:
            r = requests.get(u, timeout=(8, 14))
            if r.status_code == 200:
                for x in r.text.split():
                    x = x.strip()
                    if 6 < len(x) < 60 and ":" in x:
                        socks_raw.append(sch + x)
        except Exception:
            pass
    try:
        r = requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=socks4%2Csocks5&limit=500&sort_by=lastChecked&sort_type=desc", timeout=(8, 16))
        if r.status_code == 200:
            for x in (r.json() or {}).get("data") or []:
                socks_raw.append("socks5://" + f"{x.get('ip')}:{x.get('port')}")
    except Exception:
        pass
    # #91R: منزلی/elite — گەورەترین ئەگەری منزلی + elite-anonymous
    extra = []
    for u in ("https://raw.githubusercontent.com/zevtyardt/proxy-list/main/all.txt",
              "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&anonymity=elite&timeout=8000",
              "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt"):
        try:
            r = requests.get(u, timeout=(8, 16))
            if r.status_code == 200:
                for x in r.text.split():
                    x = x.strip()
                    if 6 < len(x) < 80 and (":" in x) and ("//" not in x.split(":")[0][-1:] or "://" in x):
                        extra.append(x)
        except Exception:
            pass
    # #91R: تێکەڵکردنی گشتی — HTTP · SOCKS · منزلی/elite
    mixed, si, si2 = [], 0, 0
    for x in raw:
        mixed.append(x)
        if len(mixed) % 6 == 0:
            if si < len(socks_raw):
                mixed.append(socks_raw[si]); si += 1
            elif si2 < len(extra):
                mixed.append(extra[si2]); si2 += 1
    mixed.extend(socks_raw[si:])
    mixed.extend(extra[si2:])
    raw = list(dict.fromkeys(mixed))
    if len(raw) > 40000:
        random.shuffle(raw)
        raw = raw[:15000]  # #91R+#94U15: سنووری ڕاو 15k — کەمکردنەوەی بیرگە/CPU دژە-OOM
    # #91W: وێبشەیر — ئەگەر تۆکەن هەبێت → هەموو جۆرەکانی (پرێمیۆم + داتاسنتر + منزلی) — خۆکارانە
    try:
        ws = json.load(open(os.path.join(DATA_DIR, "webshare.json")))
        tk = (ws or {}).get("token")
        if tk:
            _got = 0
            for _mode in ("residential", "datacenter"):
                try:
                    r = requests.get(f"https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page_size=25&type={_mode}",
                                     headers={"Authorization": "Token " + tk}, timeout=(8, 16))
                    if r.status_code == 200:
                        _res = (r.json() or {}).get("results") or []
                        for x in _res:
                            raw.append(f"{x.get('proxy_address')}:{x.get('port')}")
                        _got += len(_res)
                        if _res:
                            print(f"[PROXY-WS] وێبشەیر {_mode}: {len(_res)}", flush=True)
                except Exception:
                    pass
            if _got:
                print(f"[PROXY-WS] کۆی گشتی وێبشەیر: {_got}", flush=True)
    except Exception:
        pass
    return list(dict.fromkeys([x for x in raw if x]))


def _proxy_screen(batch, tmo=8):
    """#91H: شەپۆلێک تاقیکردنەوەی خێرا — سنوردارکردنی تڕێدەکان بە ThreadPoolExecutor بۆ پاراستنی یادگە لە OOM"""
    res = []
    _lk = threading.Lock()

    def _one(px):
        try:
            t0 = time.time()
            if px.startswith("socks4://") or px.startswith("socks5://"):
                pr = {"http": px.replace("socks5://", "socks5h://"), "https": px.replace("socks5://", "socks5h://")}
            else:
                pr = {"http": px, "https": px}
            r = requests.get("http://www.google.com/generate_204", proxies=pr, timeout=tmo)
            if r.status_code < 500:
                with _lk:
                    res.append((time.time() - t0, px))
        except Exception:
            pass

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # #94U15: 20→10 دژە-OOM
        futs = [executor.submit(_one, px) for px in batch]
        concurrent.futures.wait(futs, timeout=tmo + 4)
    return res


def _proxy_check(pxs, cap=18):
    """#91H کڕاک: شەپۆلی خێرا → ڕیزکردن بەپێی خێرایی — دوو شەپۆل تا پڕ ببێت"""
    res = _proxy_screen(pxs[:min(180, cap * 8)])
    if len(res) < cap and len(pxs) > 180:
        res += _proxy_screen(pxs[180:360])
    res.sort()
    return [p for _, p in res[:cap]]


def _proxy_mark_bad(px):
    """#91H: مردوو لە باد-سێت و حەوز یەکسان لادەبرێت؛ #94U39b: 3 زەبر (هێواش ≠ مردوو)؛ #94U41: منزلی 5 زەبر + کەلەپوور + چاکی کلی socks"""
    b = px.replace("http://", "")
    bk = px.split("://", 1)[-1]  # کلیلی strikes (هاوشێوەی سفرکردنەوە لەسەر سەرکەوتن)
    _pool = PROXY_ST.get("pool") or {}
    _pe = _pool.get(b) or _pool.get(bk) or _pool.get(px)
    _was_res = bool((_pe or {}).get("res"))
    _lim = 5 if _was_res else 3
    _st = PROXY_ST.setdefault("strikes", {})
    if len(_st) > 2000:
        _st.clear()
    _st[bk] = (_st.get(bk) or 0) + 1
    if _st[bk] < _lim:
        return False
    PROXY_ST["bad"].add(b)
    _st.pop(bk, None)
    try:
        _pool.pop(b, None)
        _pool.pop(bk, None)
        _pool.pop(px, None)
    except Exception:
        pass
    if _was_res:
        _dr = PROXY_ST.setdefault("dead_res", set())
        _dr.add(px)
        while len(_dr) > 500:
            _dr.pop()
    return True


def _proxy_revive_res():
    """#94U41: زیندووکردنەوەی منزلییە مردووەکان — IP ی ماڵەوە دەگەڕێتەوە؛ هەر کاتژمێرێک 100"""
    try:
        _dr = PROXY_ST.get("dead_res") or set()
        if not _dr:
            return
        _pool = PROXY_ST.setdefault("pool", {})
        _bad = PROXY_ST["bad"]
        _cands = [x for x in _dr if x not in _pool and x.split("://", 1)[-1] not in _pool][:100]
        if not _cands:
            return
        res = _proxy_screen(_cands)
        for lat, px in res:
            _pool[px] = {"t": time.time(), "lat": round(lat, 2), "res": True}
            _bad.discard(px)
            _bad.discard(px.split("://", 1)[-1])
        for x in _cands:
            _dr.discard(x)
        _proxy_pool_save()
        print(f"[RES-REVIVE] ♻️ {len(_cands)} تاقیکرا → {len(res)} منزلی گەڕانەوە | حەوز: {len(_pool)}", flush=True)
    except Exception as e:
        print(f"[RES-REVIVE] هەڵە: {str(e)[:50]}", flush=True)


def _proxy_pool_save():
    try:
        _json_save(os.path.join(DATA_DIR, "proxy_pool.json"),
                   {"pool": PROXY_ST.get("pool") or {}, "bad": sorted(PROXY_ST["bad"])[:600], "t": time.time()})
    except Exception:
        pass


def _proxy_pool_load():
    """#91H: حەوزی پاشەکەوتکراو لە /data — ڕیستارت = یەکسان پرۆکسی ئامادە"""
    try:
        d = json.load(open(os.path.join(DATA_DIR, "proxy_pool.json")))
        now = time.time()
        PROXY_ST["pool"] = {k: v for k, v in (d.get("pool") or {}).items() if now - (v or {}).get("t", 0) < (7200 if (v or {}).get("res") else 2700)}  # #94U41
        for b in (d.get("bad") or [])[:600]:
            PROXY_ST["bad"].add(b)
        print(f"[HARVESTER] حەوزی پاشەکەوتکراو: {len(PROXY_ST['pool'])} زیندوو | {len(PROXY_ST['bad'])} مردوو", flush=True)
    except Exception:
        try:
            for b in json.load(open(os.path.join(DATA_DIR, "proxy_bad.json"))) or []:
                PROXY_ST["bad"].add(b)
        except Exception:
            pass


def _harvest_wave(wave=120):  # #94U15: 190→120 دژە-OOM
    """#91H: یەک شەپۆل — خولانەوەی لیستی ڕاو بەبێ دووبارە، تا هەموو پرۆکسییەکان پشکنراون"""
    now = time.time()
    raw = PROXY_ST.get("raw") or []
    if now - PROXY_ST["src_t"] > 900 or not raw:
        raw = _proxy_fetch_all()
        PROXY_ST["raw"] = raw
        PROXY_ST["src_t"] = now
        PROXY_ST["cur"] = 0
        print(f"[HARVESTER] 🕸 ڕاوی تازە: {len(raw)} پاڵێوراو لە ٤٠+ سەرچاوە", flush=True)
    if not raw:
        return
    bad, pool = PROXY_ST["bad"], PROXY_ST.setdefault("pool", {})
    cur = int(PROXY_ST.get("cur") or 0) % len(raw)
    batch, i, scanned = [], cur, 0
    while len(batch) < wave and scanned < len(raw):
        px = raw[i % len(raw)]
        i += 1
        scanned += 1
        if px in bad or px in pool:
            continue
        batch.append(px)
    PROXY_ST["cur"] = i % len(raw)
    if not batch:
        PROXY_ST["cur"] = 0  # هەموو لیست پشکنراوە — لە سەرەتاوە بە قۆناغی نوێ
        return
    res = _proxy_screen(batch)
    n_socks = sum(1 for _, px in res if px.startswith("socks"))
    for lat, px in res:
        pool[px] = {"t": now, "lat": round(lat, 2)}
    # #91R: تاگی منزلی لە ip-api (hosting=false = منزلی/ISP)؛ #94U41: socks ـیش + 100/جار (سنووری batch — 200 یەکجار هەمووی دەفەوتاند)
    try:
        _untagged = [k for k, v in pool.items() if "res" not in v][:100]
        if _untagged:
            _ips = [k.split("://", 1)[-1].split(":")[0] for k in _untagged]
            _rj = requests.post("http://ip-api.com/batch?fields=query,hosting", json=_ips, timeout=(8, 20))
            if _rj.status_code == 200:
                _n_res = 0
                for ip, info in zip(_untagged, _rj.json() or []):
                    _is_res = not (info or {}).get("hosting", True)
                    pool[ip]["res"] = _is_res
                    _n_res += 1 if _is_res else 0
                print(f"[RES-TAG] {_n_res} منزلی لە {len(_untagged)}", flush=True)
    except Exception:
        pass
    _pruned_res = [k for k, v in pool.items() if (v or {}).get("res") and now - (v or {}).get("t", 0) >= 7200]
    if _pruned_res:  # #94U41: منزلی بەسەرچوو → کەلەپووری زیندووکردنەوە (نافەوتێت)
        _dr = PROXY_ST.setdefault("dead_res", set())
        for _k in _pruned_res:
            _dr.add(_k)
        while len(_dr) > 500:
            _dr.pop()
    PROXY_ST["pool"] = {k: v for k, v in pool.items() if now - (v or {}).get("t", 0) < (7200 if (v or {}).get("res") else 2700)}  # #94U41: منزلی 2h، ئاسایی 45m
    if len(PROXY_ST["pool"]) > 300:  # #94U39: 100→200؛ #94U41: →300
        # #94U20: پشکی پارێزراو بۆ منزلی — 100 منزلی + خێرا (داتاسەنتەرە خێراکان منزلییەکان ناسڕنەوە)
        _items = list(PROXY_ST["pool"].items())
        _res = sorted([kv for kv in _items if (kv[1] or {}).get("res")], key=lambda kv: kv[1].get("lat", 9))[:100]
        _resk = {k for k, _ in _res}
        _fast = sorted([kv for kv in _items if kv[0] not in _resk], key=lambda kv: kv[1].get("lat", 9))[:300 - len(_res)]
        PROXY_ST["pool"] = dict(_res + _fast)
    _proxy_pool_save()
    print(f"[HARVESTER] شەپۆل: {len(batch)} تاقیکرا → {len(res)} زیندوو (socks: {n_socks}) | حەوز: {len(PROXY_ST['pool'])} خێراترین", flush=True)


def _proxy_harvester_daemon():
    """#91H: بەردەوام — هەر 3 خولەک شەپۆلێکی 200 کراک → گەورەترین و تازەترین حەوز بەبێ وەستان؛ #94U39: ئەگەر حەوز <15 → تا 3 شەپۆل؛ #94U41: revive ی منزلی هەر کاتژمێرێک"""
    time.sleep(45)
    _last_rev = 0
    while True:
        try:
            _harvest_wave(200)
            _extra = 0
            while len(PROXY_ST.get("pool") or {}) < 15 and _extra < 2:
                _extra += 1
                print(f"[HARVESTER] 🆘 حەوز کەمە — شەپۆلی فریاکەوتنی {_extra}", flush=True)
                _harvest_wave(200)
            if time.time() - _last_rev > 3600:
                _last_rev = time.time()
                _proxy_revive_res()
        except Exception as e:
            print(f"[HARVESTER] هەڵە: {str(e)[:60]}", flush=True)
        time.sleep(180)


def _proxy_get(n=4):
    """پرۆکسی: proxies.json (دەستی) → سەرچاوە خۆڕاییەکان → **پشکنینی زیندوو** — تەنها ئەکتیڤ"""
    import time as _t
    now = _t.time()
    if not _PROXY_GET_STATE.get("loaded"):
        _PROXY_GET_STATE["loaded"] = True
        _proxy_pool_load()
    pool = PROXY_ST.get("pool") or {}
    if pool:
        ranked = sorted(pool.items(), key=lambda kv: ((not (kv[1] or {}).get("res", False)), (kv[1] or {}).get("lat", 9)))
        out = []
        http_got, socks_got = 0, 0
        for k, _ in ranked:
            if k in PROXY_ST["bad"]:
                continue
            if k.startswith("socks4://") or k.startswith("socks5://"):
                if socks_got >= max(2, n // 3):
                    continue
                socks_got += 1
            else:
                if http_got >= max(1, n - max(2, n // 3)):
                    continue
                http_got += 1
            out.append(k if "://" in k else "http://" + k)
            if len(out) >= n:
                break
        if out:
            return out
    _do_fetch = (now - PROXY_ST["src_t"] > 1800 or not PROXY_ST["list"])
    if _do_fetch and not _PROXY_FETCH_LOCK.acquire(blocking=False):
        return []  # #94U17: شەپۆلێکی تر خەریکە — fail-fast نەک pile-up
    try:
        if _do_fetch:
            manual = []
            for _pf in (os.path.join(DATA_DIR, "proxies.json"),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxies.json")):
                try:
                    d = json.load(open(_pf))
                    if isinstance(d, list):
                        manual = [str(x) for x in d if str(x).strip()]
                        if manual:
                            break
                except Exception:
                    pass
            raw = list(manual)
            if not raw:
                raw = _proxy_fetch_all()
            raw = [p for p in raw if p not in PROXY_ST["bad"]]
            good = _proxy_check(raw, cap=30)
            if manual and not good:
                good = [p if "://" in p else "http://" + p for p in manual[:6]]  # دەستیلەکان با هەوڵیان لەسەر بکرێت
            _proxy_pool_save()
            PROXY_ST["list"] = good
            PROXY_ST["bad"].clear()
            PROXY_ST["src_t"] = now
            print(f"[PROXY] {len(raw)} کۆکرا → {len(good)} ئەکتیڤ (پشکنین)", flush=True)
    finally:
        if _do_fetch:
            _PROXY_FETCH_LOCK.release()
    out = []
    for p in PROXY_ST["list"]:
        if p in PROXY_ST["bad"]:
            continue
        if "://" in p:
            out.append(p)
        else:
            out.append("http://" + p)
    out2 = []
    for p in out:
        if p not in out2:
            out2.append(p)
    return out2[:n]


_FB_BLOCK = ("TOO_MANY_ATTEMPTS_TRY_LATER", "OPERATION_NOT_ALLOWED", "QUOTA_EXCEEDED", "RESOURCE_EXHAUSTED")
_FB_DIRECT_BAD = {}  # #94U18: key → ڕۆژی بلۆکبوونی IP ی ڕاستەوخۆ (تاگ بۆ proxy-first)
_SG_BREAKER = {}  # #94U34: key → {"fail": n, "until": ts, "trips": t} — پاراستنی کلیلی Firebase لە سووتان
_SG_BREAKER_LK = threading.Lock()
_SG_KEY_NAMES = None  # #94U38: lazy map key→pool بۆ لۆگ


def _proxy_signup_best(n=6):
    """#94U18: باشترین پرۆکسی بۆ ساینئەپ — منزلی یەکەم، کەم-هەڵە، خێرا؛ #94U33: شەفڵ لەناو هەر چینێک (بڵاوکردنەوە لەسەر چەند IP)"""
    pool = PROXY_ST.get("pool") or {}
    bad = PROXY_ST.get("bad") or set()
    cands = []
    for k, v in pool.items():
        if k in bad:
            continue
        v = v or {}
        if (v.get("sg_bad") or 0) >= 3:
            continue
        cands.append((0 if v.get("res") else 1, v.get("sg_bad") or 0, v.get("lat", 9), k))
    cands.sort()
    top = cands[:n]
    _res = [k for r, _, _, k in top if r == 0]
    _oth = [k for r, _, _, k in top if r != 0]
    random.shuffle(_res)
    random.shuffle(_oth)
    out = [(k if "://" in k else "http://" + k) for k in (_res + _oth)]
    if len(out) < n:
        try:
            for p in _proxy_get(n):
                if p not in out:
                    out.append(p)
                if len(out) >= n:
                    break
        except Exception:
            pass
    return out


def _sg_breaker_allow(key):
    """#94U34: ئایا ساینئەپ بۆ ئەم کلیلە ڕێگەپێدراوە؟ (دوای 10 شکستی throttle لەسەریەک → پشووی 2h)"""
    try:
        with _SG_BREAKER_LK:
            b = _SG_BREAKER.get(key) or {}
            return not (b.get("until", 0) > time.time())
    except Exception:
        return True


def _sg_key_name(key):
    """#94U38: ناوی حەوز بۆ لۆگ (کلیلەکە خۆی چاپ مەکە)"""
    global _SG_KEY_NAMES
    try:
        if _SG_KEY_NAMES is None:
            _SG_KEY_NAMES = {CA_KEY: "CA", CB_KEY: "CB", NV_KEY: "NV", AC_KEY: "AC"}
        return _SG_KEY_NAMES.get(key, "?")
    except Exception:
        return "?"


def _sg_breaker_hit(key, ok):
    """#94U34: تۆماری ئەنجام — سەرکەوتن ڕیسیت، شکستی throttle ژمارە + trip لە 10؛ #94U38: backoff 15m→120m"""
    try:
        with _SG_BREAKER_LK:
            b = _SG_BREAKER.setdefault(key, {"fail": 0, "until": 0, "trips": 0})
            if ok:
                b["fail"] = 0
                b["trips"] = 0
                return
            b["fail"] = b.get("fail", 0) + 1
            if b["fail"] >= 10 and b.get("until", 0) <= time.time():
                t = b.get("trips", 0)
                pause = min(900 * (2 ** t), 7200)  # 15m → 30m → 60m → 120m cap
                b["until"] = time.time() + pause
                b["fail"] = 0
                b["trips"] = t + 1
                print(f"[BREAKER-{_sg_key_name(key)}] ⏸ پشووی {int(pause // 60)}m (10 throttle — پاراستنی کلیل)", flush=True)
    except Exception:
        pass


def _fb_signup(key, email, pw, ua):
    """#94U31: signUp بە پرۆکسی-یەکەم (8 باشترین: منزلی→کەم-هەڵە→خێرا)؛ ڕاستەوخۆ تەنها دوایین چارەسەر"""
    def _call(px=None):
        kw = {"json": {"email": email, "password": pw, "returnSecureToken": True},
              "headers": {"User-Agent": ua}, "timeout": (8, 16) if px else (10, 25)}
        if px:
            kw["proxies"] = {"http": px, "https": px}
        r = requests.post("https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + key, **kw)
        if r.status_code == 200:
            j = r.json() or {}
            tok = j.get("idToken")
            if not tok:
                return None
            return tok, j.get("localId") or ""
        try:
            msg = (r.json() or {}).get("error", {}).get("message", "")
        except Exception:
            msg = ""
        return ("BLOCKED", msg) if msg in _FB_BLOCK else None
    _today = time.strftime("%Y-%m-%d", time.gmtime())
    _direct_bad = _FB_DIRECT_BAD.get(key) == _today
    _saw_blocked = False  # #94U34
    for px in _proxy_signup_best(8):  # #94U31: هەمیشە پرۆکسی یەکەم — IP ڕاستەوخۆ مەخەرە مەترسییەوە
        try:
            r2 = _call(px)
        except Exception:
            _proxy_mark_bad(px)  # پرۆکسی مردووە — لاببرێت
            continue
        if r2 and r2[0] == "BLOCKED":
            _saw_blocked = True
        _pool = PROXY_ST.get("pool") or {}
        _pe = _pool.get(px) or _pool.get(px.split("://", 1)[-1])
        if r2 and r2[0] != "BLOCKED":
            try:
                if _pe is not None:
                    _pe["sg_ok"] = time.time()
                    _pe["sg_bad"] = 0
                    (PROXY_ST.get("strikes") or {}).pop(px.split("://", 1)[-1], None)  # #94U39b: سەرکەوتن = سفرکردنەوەی زەبرەکان
            except Exception:
                pass
            print(f"[FB] signUp بە پرۆکسی ✅ {px[:28]}", flush=True)
            _sg_breaker_hit(key, True)
            return r2
        try:
            if _pe is not None:
                _pe["sg_bad"] = (_pe.get("sg_bad") or 0) + 1
        except Exception:
            pass
        # BLOCKED لەڕێی پرۆکسییەوە = IP ـەکە لای Firebase فلەگە — بۆ ساینئەپ بەکارمەهێنە بەڵام مەیسڕە (بۆ کاری تر باشە)
    # #94U31: دوایین هەوڵ: ڕاستەوخۆ (تەنها ئەگەر پرۆکسییەکان نەبوون/شکستخواردن)
    try:
        r = _call()
        if r and r[0] != "BLOCKED":
            _FB_DIRECT_BAD.pop(key, None)
            _sg_breaker_hit(key, True)
            return r
        if r and r[0] == "BLOCKED":
            _FB_DIRECT_BAD[key] = _today
            _saw_blocked = True
    except Exception:
        pass
    if _saw_blocked:  # #94U34: تەنها throttle ژمارە — collision (EMAIL_EXISTS) نەخەرە ئەستۆی کلیل
        _sg_breaker_hit(key, False)
    return None


def _lim_today():
    """#91Z: بەرواری ئەمڕۆ UTC — بۆ تاگی لیمێت"""
    return time.strftime("%Y-%m-%d", time.gmtime())


def _lim_hit(em, model_key=None):
    """#91Z: ئایا ئەم ئەکاونتە ئەمڕۆ limit ە؟ — ستار/مۆدێڵ-لیمێتی دوێنێ خۆکارانە بەسەردەچێت
       (کۆن: True ی هەمیشەیی = ئەمڕۆ دەژمێردرێت — سبەی ئازاد دەبێت؛ تەنها lifetime هەمیشەییە)"""
    if not em:
        return False
    today = _lim_today()
    star = em.get("*")
    if star:
        if star is True or str(star) == today:
            return True
    if model_key:
        mv = em.get(model_key)
        if mv and (mv is True or str(mv) == today):
            return True
    return False


def _pool_reap():
    """#91P2: ئەکاونتی limit — سڕینەوە نییە! پاڵنان بۆ کۆتایی (limit ی ڕۆژانە شەوانە دەگەڕێتەوە
       — سڕینەوە = بەفیڕۆدانی ئەکاونتی تەندرووست + signup ی بێ‌پێویست)"""
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    now = time.time()
    # #91Z-mig2: ستاری True کۆن = لیمێتی ڕۆژی پێشوو → سڕینەوە (ئازاد) — نەک بە ئەمڕۆ تۆمار
    try:
        _freed = 0
        for st_lim, sv in ((CA_ST.get("limits"), _ca_save_acc), (AC_ST.get("limits"), _ac_save_acc)):
            for _e, _v in (st_lim or {}).items():
                if isinstance(_v, dict) and _v.get("*") is True:
                    _v.pop("*", None)
                    _freed += 1
            if _freed:
                try:
                    sv()
                except Exception:
                    pass
        if _freed:
            print(f"[MIGRATE] ✨ {_freed} ستاری کۆن سڕانەوە — ئەکاونتەکان ئازاد بوون", flush=True)
    except Exception:
        pass
    # CA — ئەوانەی '*' یان هەیە → کۆتایی لیست (لە سەرەتاوە کار ناکەن) — ناسێنراوەکان یەکسان کار دەکەن
    lim = CA_ST.get("limits") or {}
    accs = CA_ST.get("accounts") or []
    live = [a for a in accs if not _lim_hit(lim.get(a.get("email")) or {})]
    done = [a for a in accs if _lim_hit(lim.get(a.get("email")) or {})]
    if done and live:
        CA_ST["accounts"] = live + done
        CA_ST["idx"] = CA_ST["idx"] % max(len(live), 1)
        _ca_save_acc()
        print(f"[POOL-CA] {len(done)} limit-کراو پاڵدران کۆتایی → سەرەتا {len(live)} ی تەندرووست", flush=True)
    elif done and not live:
        # هەموویان limit — ئەوانی کۆنترین limit بدۆزە و بسڕەوە (بۆ ئەوانەی ٢ ڕۆژ پێش ئێستا بوون)
        # #94U30b: تریم 1000 (ئامانجی زیندوو) + سڕینەوەی limits/toks ی فڕێدراو؛ #94U31: حەوز 10k
        old_lim = [e for e, v in lim.items() if v.get("*")]
        if len(old_lim) > 1000:
            keep_emails = set(old_lim[-1000:])
            keep = [a for a in accs if a.get("email") in keep_emails]
            CA_ST["accounts"] = keep
            CA_ST["tok"] = None
            for _e in [e for e in lim if e not in keep_emails]:
                lim.pop(_e, None)
            _toks = CA_ST.get("toks") or {}
            for _e in [e for e in _toks if e not in keep_emails]:
                _toks.pop(_e, None)
            _ca_save_acc()
            print(f"[POOL-CA] پاککردنەوەی گەورە: {len(accs)} → {len(keep)}", flush=True)
    # CB — ئەمڕۆ تەواوبوو → پاڵنان بۆ کۆتایی (سبەی دەگەڕێنەوە)
    ex = CB_ST.get("exhausted") or {}
    accs = CB_ST.get("accounts") or []
    def _cb_dead(e):
        v = ex.get(e, 0)
        try:
            return float(v) > now  # #94U24: cooldown-until
        except Exception:
            return str(v)[:10] == today
    live = [a for a in accs if not _cb_dead(a.get("email"))]
    done = [a for a in accs if _cb_dead(a.get("email"))]
    if done and live:
        CB_ST["accounts"] = live + done
        CB_ST["idx"] = CB_ST["idx"] % max(len(live), 1)
        _cb_save_acc()
        print(f"[POOL-CB] {len(done)} تەواوبوو پاڵدران کۆتایی → {len(live)} ی تەندرووست سەرەتا", flush=True)
    # NV — ٣ جار کۆڵ → پاڵنان بۆ کۆتایی (نەک سڕینەوە — ئەوان لەوانەیە بگەڕێنەوە)
    exc = NV_ST.get("exc") or {}
    accs = NV_ST.get("accounts") or []
    live = [a for a in accs if exc.get(a.get("email"), 0) < 3]
    done = [a for a in accs if exc.get(a.get("email"), 0) >= 3]
    if done and live:
        NV_ST["accounts"] = live + done
        NV_ST["uid"] = None
        NV_ST["idx"] = NV_ST["idx"] % max(len(live), 1)
        _nv_save_acc()
        print(f"[POOL-NV] {len(done)} کۆڵبوو پاڵدران کۆتایی → {len(live)} ی تەندرووست سەرەتا", flush=True)
    elif done and not live:
        keep = [a for a in done if exc.get(a.get("email"), 0) < 9]
        NV_ST["accounts"] = keep
        NV_ST["uid"] = None
        NV_ST["idx"] = 0
        _nv_save_acc()
        print(f"[POOL-NV] پاککردنەوە: {len(accs)} → {len(keep)}", flush=True)


def _pool_fill_one(name, st, fn, tgt, alive_tgt, batch, jlo, jhi):
    """#94U40: پڕکردنەوەی یەک حەوز — سەلامەت بۆ تڕێدی جیا (هەر حەوز ST/کلیلی خۆی هەیە)"""
    import random as _r
    import time as _t
    try:
        accs = st.get("accounts") or []
        # #94U2: ژمارەی زیندوو — ئەگەر هەموو ئەکاونتەکان لیمیتن → زیاد بکە با بەردەوام بێت
        today = _lim_today()
        now = _t.time()
        lim = st.get("limits") or {}
        exh = st.get("exhausted") or {}
        alive = [a for a in accs if _pool_acc_alive(a, lim, exh, today, now)]
        if len(accs) >= tgt and len(alive) >= alive_tgt:
            return 0
        made = 0
        miss = 0
        for _ in range(batch):
            accs_now = st.get("accounts") or []
            lim_now = st.get("limits") or {}
            exh_now = st.get("exhausted") or {}
            alive_now = sum(1 for a in accs_now if _pool_acc_alive(a, lim_now, exh_now, today, now))
            if len(accs_now) >= tgt or alive_now >= alive_tgt:
                break
            before = len(accs_now)
            try:
                fn()
            except Exception:
                pass
            if len(st.get("accounts") or []) > before:
                made += 1
                miss = 0
            else:
                miss += 1
                if miss >= 3:  # بودجە/ساینئەپ گیراوە — ئەم خولە بوەستە
                    break
            _t.sleep(_r.uniform(jlo, jhi))  # jitter دژە-بلۆک
        if made:
            print(f"[POOL-{name}] +{made} → {len(st.get('accounts') or [])}/{tgt} (ئامانجی زیندوو {alive_tgt})", flush=True)
        return made
    except Exception as e:
        print(f"[POOL-{name}] {str(e)[:50]}", flush=True)
        return 0


def _pool_daemon():
    """#94U35: CA/CB/NV → 1000 زیندوو + AC 30؛ #94U40: catch-up — ئەگەر <ئامانج: 3 حەوز پێکەوە (threads) بەچ 40؛ ئەگەر گەیشت: مەینتەینەنس (1-بۆ-1)"""
    time.sleep(60)
    # لازەی — دوای load ی هەموو ST ەکان (CB/NV دوای ئەم بلۆکە پێناسە دەکرێن لە فایلدا)
    import sys as _s
    _m = _s.modules[__name__]
    pools = (("CA", _m.CA_ST, _m._ca_signup_new, 10000, 1000),
             ("CB", _m.CB_ST, _m._cb_signup_new, 10000, 1000),
             ("NV", _m.NV_ST, _m._nv_signup_new, 10000, 1000),
             ("AC", _m.AC_ST, _m._ac_signup_new, 300, 30))
    import concurrent.futures as _cf
    _was_catch = None
    while True:
        try:
            _pool_reap()
        except Exception as e:
            print(f"[POOL] reap: {str(e)[:60]}", flush=True)
        # دۆخی گەیشتن: ئایا هەر حەوزێکی گەورە لە ژێر ئامانجدایە؟
        _catch = False
        _today = _lim_today()
        _now = time.time()
        for _nm, _st, _fn, _tgt, _at in pools[:3]:
            try:
                _accs = _st.get("accounts") or []
                _lim = _st.get("limits") or {}
                _exh = _st.get("exhausted") or {}
                _al = sum(1 for _a in _accs if _pool_acc_alive(_a, _lim, _exh, _today, _now))
                if _al < _at and len(_accs) < _tgt:
                    _catch = True
                    break
            except Exception:
                pass
        if _catch != _was_catch:
            print(f"[POOL] {'🚀 catch-up: CA+CB+NV پێکەوە بەچ 40' if _catch else '🛡 maintenance: 1-بۆ-1 پاراستنی 1000'}", flush=True)
            _was_catch = _catch
        try:
            if _catch:
                with _cf.ThreadPoolExecutor(max_workers=3) as _ex:
                    _futs = [_ex.submit(_pool_fill_one, _nm, _st, _fn, _tgt, _at, 40, 2, 4)
                             for _nm, _st, _fn, _tgt, _at in pools[:3]]
                    _cf.wait(_futs)
                _pool_fill_one("AC", _m.AC_ST, _m._ac_signup_new, 300, 30, 2, 3, 6)
                time.sleep(30)
            else:
                for _nm, _st, _fn, _tgt, _at in pools:
                    _pool_fill_one(_nm, _st, _fn, _tgt, _at, 20 if _nm != "AC" else 2, 3, 6)
                time.sleep(90)  # #91: خێراتر — 90 چرکە نەک 120
        except Exception as e:
            print(f"[POOL] daemon: {str(e)[:60]}", flush=True)
            time.sleep(60)


def _ca_token():
    import time as _t
    acc = getattr(_TLS, "ca_acc", None)
    if acc is None:
        try:
            _ca_rotate(None)  # #94U21: یەکەم داوا → لیسی خۆی (تەنها ستار-لیمێت لابەرە)
        except Exception:
            pass
        acc = getattr(_TLS, "ca_acc", None)
        if acc is None:
            accs = CA_ST.get("accounts") or []
            acc = accs[CA_ST["idx"] % len(accs)] if accs else None
    if acc is not None:
        em = acc.get("email")
        with _CA_LK:
            c = (CA_ST.get("toks") or {}).get(em)
        if c and _t.time() - c[1] < 2700:
            return c[0]
        res = _ca_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            with _CA_LK:
                CA_ST.setdefault("toks", {})[em] = (res[0], _t.time())
            return res[0]
    resn = _ca_signup_new()
    if not resn:
        raise EMError("ca: هیچ ئەکاونت")
    try:
        _na = (CA_ST.get("accounts") or [])[-1]
        _TLS.ca_acc = _na
        with _CA_LK:
            CA_ST.setdefault("toks", {})[_na.get("email")] = (resn[0], _t.time())
    except Exception:
        pass
    return resn[0]


def _ca_rotate(model_key):
    """ئەکاونتی دواتر بۆ ئەم مۆدێڵە — ئەوانەی سنووریان تێپەڕاندووە لابەرە؛ ئەگەر نەمابوو → نوێ"""
    accs = CA_ST.get("accounts") or []
    lim = CA_ST.get("limits") or {}
    chosen = None
    with _CA_LK:
        for _ in range(len(accs)):
            CA_ST["idx"] = (CA_ST["idx"] + 1) % len(accs)
            acc = accs[CA_ST["idx"]]
            em = lim.get(acc["email"]) or {}
            if not _lim_hit(em, model_key):  # #91Z: ستاری دوێنێ = ئازاد
                chosen = acc
                break
    if chosen is not None:
        _TLS.ca_acc = chosen
        CA_ST["tok"] = None
        _ca_save_acc()
        return True
    res = _ca_signup_new(model_key)
    if res:
        try:
            _TLS.ca_acc = (CA_ST.get("accounts") or [])[-1]
        except Exception:
            pass
    return bool(res)


def _ca_models_catalog():
    cat = {}
    for k, v in (MS.get("ca_ok") or {}).items():
        cat[k] = (v.get("version") or k, v.get("label") or k)
    for k, v in CA_FALLBACK.items():
        cat.setdefault(k, v)
    return cat


def ca_chat(messages, model_id, timeout=110):
    """چاتی ChatbotAI — send + پۆڵی get-all + حەوزی ئەکاونت + خۆکار-ساینئەپ"""
    import time as _t
    cat = _ca_models_catalog()
    if model_id not in cat:
        raise EMError("ca: مۆدێڵ نییە")
    mkey, mver = model_id, cat[model_id][0]
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("ca: هیچ نامە")
    lines.append("[Assistant]")
    prompt = _flat_cut(lines)
    last_err = ""
    for attempt in range(8):
        try:
            tok = _ca_token()
        except EMError:
            if not _ca_rotate(mkey):
                raise
            continue
        H = {"User-Agent": CA_UA, "Content-Type": "application/json",
             "authorization": tok, "Origin": CA_BASE, "Referer": CA_BASE + "/"}
        try:
            r = requests.post(CA_BASE + "/api/chat/message/send",
                              json={"message": prompt, "model": mkey, "temporaryChat": False,
                                    "modelVersion": mver}, headers=H, timeout=(15, 40))
        except Exception as e:
            raise EMError(f"ca: {str(e)[:60]}")
        ok = False
        sid = ""
        err = ""
        try:
            j = r.json() or {}
            ok = bool(j.get("success"))
            sid = str(j.get("sessionId") or "")
            err = str(j.get("error") or "")
        except Exception:
            err = r.text[:80]
        if not ok:
            last_err = err or str(r.status_code)
            low = last_err.lower()
            if "limit" in low or "free message" in low or "no free" in low:
                acc = getattr(_TLS, "ca_acc", None)
                if acc is None:
                    _accs = CA_ST.get("accounts") or []
                    acc = _accs[CA_ST["idx"] % len(_accs)] if _accs else None
                if acc is not None:
                    lm = CA_ST.setdefault("limits", {}).setdefault(acc["email"], {})
                    lm[mkey] = _lim_today()  # مۆدێڵ-لیمێت — هەمیشە بەروارکراو
                    # #91Z-P: ستار تەنها بۆ limit ی ڕاستەقینەی گشتی (free message / no free / daily limit)
                    # هەڵەکانی "account limit"/"rate" ی تایبەت بە مۆدێڵ → تەنها mkey (نەک *)
                    if ("free message" in low or "no free" in low or "daily" in low):
                        lm["*"] = _lim_today()
                        _replace_dead_soon("ca")  # #94U24: مردنی گشتی → نوێ لە جێی
                    _ca_save_acc()
                if not _ca_rotate(mkey):
                    raise EMError("ca: سنووری هەموو ئەکاونتەکان")
                continue
            if r.status_code in (401, 403):
                CA_ST["tok"] = None
                if not _ca_rotate(mkey):
                    raise EMError("ca: توکن")
                continue
            raise EMError(f"ca: {last_err[:60]}")
        # پۆڵی وەڵام — get-all (POST)
        deadline = _t.time() + min(timeout, 100)
        while _t.time() < deadline:
            _t.sleep(2.5)
            try:
                r2 = requests.post(CA_BASE + "/api/session/get-all", headers=H, json={}, timeout=(15, 30))
                sessions = (r2.json() or {}).get("sessions") or []
            except Exception:
                continue
            for s in sessions:
                if str(s.get("sessionId")) != sid:
                    continue
                ms = s.get("messages") or []
                if ms and ms[-1].get("finish_reason") == "stop":
                    ans = (ms[-1].get("content") or "").strip()
                    if ans:
                        return ans
        last_err = "بەتاڵ/درەنگ"
        _tok_drop("ca")
        CA_ST["tok"] = None
    raise EMError(f"ca: {last_err[:60] or 'شکست'}")


def ca_servers():
    src = MS.get("ca_ok") or {k: {"version": v[0], "label": v[1]} for k, v in CA_FALLBACK.items()}
    out = []
    for k in sorted(src):
        lbl = (src[k] or {}).get("label") or k
        out.append({"id": f"ca-{re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')}",
                    "name": f"{lbl} (CA)", "model_id": k, "kind": "ca"})
    return out


def _ca_extract_models__raw(html):
    """نەخشەی مۆدێڵەکان لە payload ی Nuxt ی HTML — کۆنفیگی multi_language (idMap: نرخ لە شوێنی تر)"""
    i = 0
    while True:
        j = -1
        for pat in ('{\\\\"is_active', '{\\"is_active', '{"is_active'):
            j = html.find(pat, i)
            if j >= 0:
                break
        if j < 0:
            return None
        k = html.rfind('"', max(0, j - 8), j)
        if k < 0:
            i = j + 1
            continue
        out = []
        esc = False
        pos = k + 1
        while pos < len(html):
            ch = html[pos]
            if esc:
                out.append(ch)
                esc = False
            elif ch == "\\":
                out.append(ch)
                esc = True
            elif ch == '"':
                break
            else:
                out.append(ch)
            pos += 1
        i = pos + 1
        try:
            inner = json.loads('"' + "".join(out) + '"')
            cfg = json.loads(inner)
        except Exception:
            continue
        if isinstance(cfg, dict) and isinstance(cfg.get("models"), dict) and len(cfg["models"]) >= 3:
            return cfg["models"]
    return None


def _ca_extract_models(html):
    """#91A6: safe-wrapper — parser هەرگیز sync ەک ناکوژێنێت"""
    try:
        return _ca_extract_models__raw(html)
    except Exception:
        return None

def sync_ca_models(force=False):
    """ئۆتۆ-ئەپدێتی ChatbotAI: نەخشەی مۆدێڵەکان لە HTML ی /chat — ٦ کاتژمێر"""
    import time as _t
    if not force and _t.time() - _CA_SYNC["t"] < 21600:
        return
    _CA_SYNC["t"] = _t.time()
    try:
        r = requests.get(CA_BASE + "/chat", headers={"User-Agent": CA_UA, "Accept": "text/html",
                                                     "Referer": CA_BASE + "/"}, timeout=(15, 40))
        if r.status_code != 200:
            print(f"[CA-SYNC] HTML {r.status_code}", flush=True)
            return
        models = _ca_extract_models(r.text)
        if not models:
            print("[CA-SYNC] نەخشە نەدۆزرایەوە — کاتی کۆن دەمێنێتەوە", flush=True)
            return
        ok = {}
        for k, v in models.items():
            try:
                if not (v or {}).get("is_active"):
                    continue
                ok[k] = {"version": v.get("version") or k, "label": v.get("display_name") or k}
            except Exception:
                continue
        if len(ok) >= 5:
            MS["ca_ok"] = ok
            _ms_save()
            print(f"[CA-SYNC] کاتالۆگ {len(ok)} مۆدێڵ", flush=True)
    except Exception as e:
        print(f"[CA-SYNC] {str(e)[:80]}", flush=True)


# ══════════ AskAI (askaichat.app) — §2.31 — Firebase + cerebroId + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
AC_KEY = "AIzaSyBIjexOfpMhsws3weHS6Hko4d5Arin3Zzs"
AC_BASE = "https://askaichat.app"
AC_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AC_ACC_FILE = os.path.join(DATA_DIR, "ac_accounts.json")  # #94U32b: مانەوە لەسەر /data (پێشتر بە هەر deploy ێک دەسڕایەوە)
AC_ST = {"tok": None, "tok_t": 0.0, "idx": 0, "next_num": 82407,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82406@duidir.com", "password": "komex82406@duidir.com"}],
         "limits": {}, "signups": {"date": "", "n": 0}}
_AC_SYNC = {"t": 0.0}
# کاتالۆگی بنەڕەتی — تەنها ئەوانەی سنووری خۆڕاییان هەیە (چاکەکان limit=0 ئەنجام نادەن)
AC_FALLBACK = {
    "gpt-5.4-nano": ("gpt-5.4-nano", "GPT-5.4 Nano"),
}


def _ac_load_acc():
    import json as _j
    try:
        d = _json_load_safe(AC_ACC_FILE) or {}
        AC_ST["accounts"] = d.get("accounts") or AC_ST["accounts"]
        AC_ST["idx"] = int(d.get("idx") or 0)
        AC_ST["next_num"] = int(d.get("next_num") or 82407)
        AC_ST["limits"] = d.get("limits") or {}
        AC_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _ac_save_acc():
    import json as _j
    try:
        _json_save(AC_ACC_FILE, {"accounts": AC_ST.get("accounts") or [], "idx": AC_ST["idx"],
                                 "next_num": AC_ST["next_num"], "limits": AC_ST.get("limits") or {},
                                 "signups": AC_ST.get("signups") or {"date": "", "n": 0}})
    except Exception:
        pass


_ac_load_acc()


def _ac_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={AC_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": AC_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json() or {}
    tok = j.get("idToken")
    if not tok:
        return None
    return tok, j.get("localId") or ""


def _ac_bootstrap(tok, uid, email):
    """پرۆفایلی cerebro + user/set بە cerebroId — بەبێ ئەمە نەوەکە ناگوزەرێت"""
    import random as _r, string as _s
    cid = "web_" + "".join(_r.choices(_s.ascii_letters + _s.digits, k=9))
    try:
        requests.post("https://gateway.cerebroapi.com/user/web",
                      json={"user_id": cid, "app_id": "com.codeway.chatappweb", "version": "1.0.0",
                            "operating_system": "Windows", "properties": {"userAgent": AC_UA}},
                      headers={"User-Agent": AC_UA}, timeout=(10, 20))
    except Exception:
        pass
    import time as _t
    try:
        requests.post(AC_BASE + "/api/user/set",
                      json={"userId": uid, "firebaseUserId": uid, "email": email,
                            "createdAt": int(_t.time() * 1000), "cerebroId": cid,
                            "providerData": [{"providerId": "password", "uid": email, "displayName": None,
                                              "email": email, "phoneNumber": None, "photoURL": None}],
                            "originOnboarding": "Home", "emailConsent": True,
                            "temporaryChatOnboarding": True},
                      headers={"authorization": tok, "User-Agent": AC_UA, "Origin": AC_BASE,
                               "Referer": AC_BASE + "/", "Content-Type": "application/json"},
                      timeout=(10, 25))
    except Exception:
        pass


def _ac_signup_new():
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = AC_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    if len(AC_ST.get("accounts") or []) >= 300:  # #94U32: 40→300
        return None
    if not _sg_breaker_allow(AC_KEY):  # #94U34
        return None
    if not _sg_reserve(AC_ST, 200, today, _AC_LK):  # #94U23 بودجە لەژێر لۆک؛ #94U32: 20→200
        return None
    n = AC_ST["next_num"] + random.randint(0, 2000)  # #94U32 jitter
    for _ in range(6):
        email = f"komex{n}@duidir.com"
        pw = f"{email}#{random.randint(10000, 99999)}"
        res = _fb_signup(AC_KEY, email, pw, _rand_ua())  # #94U32: proxy-first لەبری _ac_firebase ی ڕاستەوخۆ
        if res:
            acc = {"email": email, "password": pw, "boot": True, "ua": _rand_ua()}
            try:
                _ac_bootstrap(res[0], res[1], email)
            except Exception as e:
                print(f"[AC] bootstrap fail {email}: {e}", flush=True)
            AC_ST["accounts"] = (AC_ST.get("accounts") or []) + [acc]
            AC_ST["idx"] = len(AC_ST["accounts"]) - 1
            AC_ST["next_num"] = n + 1
            AC_ST["tok"] = None
            _ac_save_acc()
            print(f"[AC] ئەکاونتی نوێ ✅ {email}", flush=True)
            return res
        time.sleep(random.uniform(1.0, 2.0))  # #94U32 jitter
        n += 1
    AC_ST["next_num"] = n
    _ac_save_acc()
    return None


def _ac_token():
    import time as _t
    acc = getattr(_TLS, "ac_acc", None)
    if acc is None:
        try:
            _ac_rotate(None)  # #94U21: یەکەم داوا → لیسی خۆی
        except Exception:
            pass
        acc = getattr(_TLS, "ac_acc", None)
        if acc is None:
            accs = AC_ST.get("accounts") or []
            acc = accs[AC_ST["idx"] % len(accs)] if accs else None
    if acc is not None:
        em = acc.get("email")
        with _AC_LK:
            c = (AC_ST.get("toks") or {}).get(em)
        if c and _t.time() - c[1] < 2700:
            return c[0]
        res = _ac_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            with _AC_LK:
                AC_ST.setdefault("toks", {})[em] = (res[0], _t.time())
            if not acc.get("boot"):
                try:
                    _ac_bootstrap(res[0], res[1], acc["email"])
                except Exception:
                    pass
                acc["boot"] = True
                _ac_save_acc()
            return res[0]
    resn = _ac_signup_new()
    if not resn:
        raise EMError("ac: هیچ ئەکاونت")
    try:
        _na = (AC_ST.get("accounts") or [])[-1]
        _TLS.ac_acc = _na
        with _AC_LK:
            AC_ST.setdefault("toks", {})[_na.get("email")] = (resn[0], _t.time())
    except Exception:
        pass
    return resn[0]


def _ac_rotate(model_key):
    accs = AC_ST.get("accounts") or []
    lim = AC_ST.get("limits") or {}
    chosen = None
    with _AC_LK:
        for _ in range(len(accs)):
            AC_ST["idx"] = (AC_ST["idx"] + 1) % len(accs)
            acc = accs[AC_ST["idx"]]
            em = lim.get(acc["email"]) or {}
            if not _lim_hit(em, model_key):  # #91Z
                chosen = acc
                break
    if chosen is not None:
        _TLS.ac_acc = chosen
        AC_ST["tok"] = None
        _ac_save_acc()
        return True
    res = _ac_signup_new()
    if res:
        try:
            _TLS.ac_acc = (AC_ST.get("accounts") or [])[-1]
        except Exception:
            pass
    return bool(res)


def _ac_catalog():
    cat = {}
    for k, v in (MS.get("ac_ok") or {}).items():
        cat[k] = (v.get("version") or k, v.get("label") or k)
    for k, v in AC_FALLBACK.items():
        cat.setdefault(k, v)
    return cat


def ac_chat(messages, model_id, timeout=110):
    """چاتی AskAI — send + SSE stream ی session + حەوزی ئەکاونت + خۆکار-ساینئەپ"""
    import time as _t
    cat = _ac_catalog()
    if model_id not in cat:
        raise EMError("ac: مۆدێڵ نییە")
    mkey, mver = model_id, cat[model_id][0]
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("ac: هیچ نامە")
    lines.append("[Assistant]")
    prompt = _flat_cut(lines)
    last_err = ""
    for attempt in range(8):
        try:
            tok = _ac_token()
        except EMError:
            if not _ac_rotate(mkey):
                raise
            continue
        H = {"User-Agent": AC_UA, "Content-Type": "application/json", "authorization": tok,
             "Origin": AC_BASE, "Referer": AC_BASE + "/", "accept": "text/event-stream"}
        try:
            r = requests.post(AC_BASE + "/api/chat/message/send",
                              json={"message": prompt, "model": mkey, "temporaryChat": False,
                                    "modelVersion": mver}, headers=H, timeout=(15, 40))
        except Exception as e:
            raise EMError(f"ac: {str(e)[:60]}")
        ok = False
        sid = ""
        err = ""
        try:
            j = r.json() or {}
            ok = bool(j.get("success"))
            sid = str(j.get("sessionId") or "")
            err = str(j.get("error") or "")
        except Exception:
            err = r.text[:80]
        if not ok:
            last_err = err or str(r.status_code)
            low = last_err.lower()
            if "limit" in low or "free message" in low or "no free" in low:
                acc = getattr(_TLS, "ac_acc", None)
                if acc is None:
                    _accs = AC_ST.get("accounts") or []
                    acc = _accs[AC_ST["idx"] % len(_accs)] if _accs else None
                if acc is not None:
                    lm = AC_ST.setdefault("limits", {}).setdefault(acc["email"], {})
                    lm[mkey] = _lim_today()  # مۆدێڵ-لیمێت
                    if ("free message" in low or "no free" in low or "daily" in low):
                        lm["*"] = _lim_today()  # تەنها limit ی ڕاستەقینەی گشتی
                        _replace_dead_soon("ac")  # #94U24: مردنی گشتی → نوێ لە جێی
                    _ac_save_acc()
                if not _ac_rotate(mkey):
                    raise EMError("ac: سنووری هەموو ئەکاونتەکان")
                continue
            if r.status_code in (401, 403):
                AC_ST["tok"] = None
                if not _ac_rotate(mkey):
                    raise EMError("ac: توکن")
                continue
            raise EMError(f"ac: {last_err[:60]}")
        # SSE stream — snapshot ی نشست
        ans = ""
        deadline = _t.time() + min(timeout, 100)
        try:
            r2 = requests.get(AC_BASE + "/api/session/stream",
                              params={"sessionId": sid, "isTool": "false", "isAssistant": "false"},
                              headers=H, timeout=(15, 100), stream=True)
            for line in r2.iter_lines(decode_unicode=True):
                if _t.time() > deadline:
                    break
                if not line or not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except Exception:
                    continue
                if d.get("type") != "snapshot":
                    continue
                data = d.get("data") or {}
                ms = data.get("messages") or []
                am = [x for x in ms if x.get("role") == "assistant"]
                if am and data.get("status") == "completed":
                    ans = (am[-1].get("message") or "").strip()
                    break
            try:
                r2.close()
            except Exception:
                pass
        except Exception as e:
            last_err = str(e)[:60]
            AC_ST["tok"] = None
            continue
        if ans:
            return ans
        last_err = "بەتاڵ/درەنگ"
        AC_ST["tok"] = None
    raise EMError(f"ac: {last_err[:60] or 'شکست'}")


def ac_servers():
    src = MS.get("ac_ok") or {k: {"version": v[0], "label": v[1]} for k, v in AC_FALLBACK.items()}
    out = []
    for k in sorted(src):
        lbl = (src[k] or {}).get("label") or k
        out.append({"id": f"ac-{re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-')}",
                    "name": f"{lbl} (AC)", "model_id": k, "kind": "ac"})
    return out


def sync_ac_models(force=False):
    """ئۆتۆ-ئەپدێتی AskAI: نەخشەی مۆدێڵەکان لە HTML — ٦ کاتژمێر (هەمان پارسەری Nuxt)"""
    import time as _t
    if not force and _t.time() - _AC_SYNC["t"] < 21600:
        return
    _AC_SYNC["t"] = _t.time()
    try:
        r = requests.get(AC_BASE + "/chat", headers={"User-Agent": AC_UA, "Accept": "text/html",
                                                     "Referer": AC_BASE + "/"}, timeout=(15, 40))
        if r.status_code != 200:
            print(f"[AC-SYNC] HTML {r.status_code}", flush=True)
            return
        models = _ca_extract_models(r.text)
        if not models:
            print("[AC-SYNC] نەخشە نەدۆزرایەوە — کاتی کۆن دەمێنێتەوە", flush=True)
            return
        ok = {}
        for k, v in models.items():
            try:
                if not (v or {}).get("is_active"):
                    continue
                # تەنها ئەوانەی سنووری خۆڕاییان هەیە — ئەوانی تر پرۆن و هەمیشە شکست دەخۆن
                if not (v.get("free_lifetime_message_limit") or 0) > 0:
                    continue
                ok[k] = {"version": v.get("version") or k, "label": v.get("display_name") or k}
            except Exception:
                continue
        if len(ok) >= 1:
            MS["ac_ok"] = ok
            _ms_save()
            print(f"[AC-SYNC] کاتالۆگ {len(ok)} مۆدێڵی خۆڕایی", flush=True)
    except Exception as e:
        print(f"[AC-SYNC] {str(e)[:80]}", flush=True)


# ══════════ Nova (chat.novaapp.ai) — §2.32 — Firebase + حەوزی ئەکاونت + خۆکار-ساینئەپ ══════════
NV_KEY = "AIzaSyAOuqWxL44t4n0_uF00qj7jh8kmb8Ly9s0"
NV_BASE = "https://api.novaapp.ai"
NV_CMS = "https://webcms.novaapp.ai/api/ai-models?populate[]=tags&populate[]=examples&populate[]=suggestions&pagination[pageSize]=100"
NV_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
NV_ACC_FILE = os.path.join(DATA_DIR, "nv_accounts.json")
NV_ST = {"tok": None, "uid": None, "tok_t": 0.0, "idx": 0, "next_num": 82416,
         "accounts": [{"email": "komex82398@duidir.com", "password": "komex82398@duidir.com"},
                      {"email": "komex82414@duidir.com", "password": "komex82414@duidir.com"},
                      {"email": "komex82415@duidir.com", "password": "komex82415@duidir.com"}],
         "exhausted": {}, "ensured": {}, "signups": {"date": "", "n": 0}}
_NV_SYNC = {"t": 0.0}
# مۆدێڵی هەرزان — بە botId دەناسرێتەوە (کاتالۆگ بە modelKey دەگۆڕدرێت بەڵام botId جێگیرە)
NV_FREE_BOTS = {0: "4o-mini", 9: "auto", 10: "gemini-2.5-flash", 15: "claude", 21: "deepSeek",
                26: "gpt-4.1", 44: "claude-4.5-haiku", 49: "gpt-5.1", 100: "gemini-3-flash",
                108: "gpt-5.6-luna", 111: "deepseek-v4-flash"}
# پرێمیۆم — ensure-credits کرێدیتی دەستپێک دەدات؛ تەنها هەرزانەکان (28/29) بە ڕۆتەیشن دەکرێنەوە
NV_PREM_CHEAP = {28, 29}
NV_PREMIUM_BOTS = {14: "deepSeekV4", 28: "gpt-5", 29: "gpt-5-mini", 40: "o3", 46: "claude-4.5-sonnet",
                   50: "gemini-3.1-pro", 106: "gpt-5.5", 107: "gpt-5.4", 110: "claude-4.6-sonnet",
                   112: "deepseek-v4-pro", 113: "grok-4.3", 114: "gemini-3.1-flash-lite", 115: "gpt-5.3",
                   116: "gpt-5.6", 117: "claude-5-sonnet", 119: "claude-5-opus", 120: "grok-4.5",
                   121: "gemini-3.6-flash", 122: "gpt-5.6-terra", 123: "gemini-3-pro", 125: "claude-4.6-opus",
                   126: "claude-4.8-opus", 127: "grok-4.20", 128: "claude-5-fable", 136: "gpt-6-astra"}
NV_HTTP400_BOTS = {5, 23, 45, 201, 403}  # پێویستیان بە پارامەتری جیاواز — هێشتا ناتۆمارکرێن
NV_PREF = {0: "4o-mini", 108: "gpt-5.6-luna", 14: "deepSeekV4", 107: "gpt-5.4", 110: "claude-4.6-sonnet",
           115: "gpt-5.3", 123: "gemini-3-pro", 128: "claude-5-fable"}
NV_SKIP_KEYS = {"link-and-ask", "music-generation", "document", "editor", "ai-search", "superbot", "aiapp", "chatbotapp", "youtube-summarizer", "image-generator", "logo-generator", "tattoo-generator", "nova"}


def _nv_load_acc():
    import json as _j
    try:
        d = _json_load_safe(NV_ACC_FILE) or {}
        NV_ST["accounts"] = d.get("accounts") or NV_ST["accounts"]
        NV_ST["idx"] = int(d.get("idx") or 0)
        NV_ST["next_num"] = int(d.get("next_num") or 82416)
        NV_ST["exhausted"] = d.get("exhausted") or {}
        NV_ST["ensured"] = d.get("ensured") or {}
        NV_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    except Exception:
        pass


def _nv_save_acc():
    with _SAVE_LOCK:
        return _nv_save_acc__impl()


def _nv_save_acc__impl():
    import json as _j
    try:
        _json_save(NV_ACC_FILE, {"accounts": NV_ST.get("accounts") or [], "idx": NV_ST["idx"],
                                 "next_num": NV_ST["next_num"], "exhausted": NV_ST.get("exhausted") or {},
                                 "ensured": NV_ST.get("ensured") or {},
                                 "signups": NV_ST.get("signups") or {"date": "", "n": 0}})
    except Exception:
        pass


_nv_load_acc()


def _nv_firebase(ep, email, pw):
    r = requests.post(f"https://identitytoolkit.googleapis.com/v1/accounts:{ep}?key={NV_KEY}",
                      json={"email": email, "password": pw, "returnSecureToken": True},
                      headers={"User-Agent": NV_UA}, timeout=(10, 25))
    if r.status_code != 200:
        return None
    j = r.json() or {}
    tok = j.get("idToken")
    if not tok:
        return None
    return tok, j.get("localId") or ""


def _nv_signup_new(force=False):  # #94U24: force = جێگۆڕکێ
    import datetime as _dt
    today = _dt.datetime.utcnow().strftime("%Y-%m-%d")
    sg = NV_ST.get("signups") or {"date": "", "n": 0}
    if sg.get("date") != today:
        sg = {"date": today, "n": 0}
    _nv_n = len(NV_ST.get("accounts") or [])
    _ex = NV_ST.get("exhausted") or {}
    _now = time.time()
    _healthy = 0
    for _a in (NV_ST.get("accounts") or []):
        try:
            _ok = float(_ex.get(_a.get("email"), 0) or 0) <= _now
        except Exception:
            _ok = True
        if _ok:
            _healthy += 1
    if _nv_n >= 10000 or (not force and _healthy >= 1000):  # #94U35: وەک CA
        return None
    if not _sg_breaker_allow(NV_KEY):  # #94U34
        return None
    if not _sg_reserve(NV_ST, 10000, today, _NV_LK):  # #94U23 بودجە لەژێر لۆک؛ #94U35: →10000
        return None
    import time as _ts
    n = NV_ST["next_num"] + random.randint(0, 3000)  # #94U32 jitter دژە-دەستنیشان
    for pref in ("komex", "naska"):  # #94U32: 2 پریفیکس
        for off in (0, 3, 13, 40, 100, 250):
            email = f"{pref}{n + off}@duidir.com"
            pw = f"{email}#{random.randint(10000, 99999)}"
            res = _fb_signup(NV_KEY, email, pw, _rand_ua())
            if res:
                NV_ST["accounts"] = (NV_ST.get("accounts") or []) + [{"email": email, "password": pw}]
                NV_ST["idx"] = len(NV_ST["accounts"]) - 1
                NV_ST["next_num"] = n + off + 1
                NV_ST["tok"] = None
                _nv_save_acc()
                print(f"[NV] ئەکاونتی نوێ ✅ {email}", flush=True)
                return res
            _ts.sleep(random.uniform(1.0, 2.5))  # #94U32 jitter
    NV_ST["next_num"] = n + 300
    _nv_save_acc()
    print(f"[NV] هیچ شوێن — بازدا بۆ {NV_ST['next_num']}", flush=True)
    return None


def _nv_token():
    import time as _t
    acc = getattr(_TLS, "nv_acc", None)
    if acc is None:
        try:
            _nv_rotate()  # #94U21: یەکەم داوا → لیسی خۆی لەژێر لۆک (بڵاوبوونەوە لە سەرەتاوە)
        except Exception:
            pass
        acc = getattr(_TLS, "nv_acc", None)
        if acc is None:
            accs = NV_ST.get("accounts") or []
            acc = accs[NV_ST["idx"] % len(accs)] if accs else None
    if acc is not None:
        em = acc.get("email")
        with _NV_LK:
            c = (NV_ST.get("toks") or {}).get(em)
        if c and _t.time() - c[2] < 2700:
            return c[0], c[1]
        res = _nv_firebase("signInWithPassword", acc["email"], acc["password"])
        if res:
            with _NV_LK:
                NV_ST.setdefault("toks", {})[em] = (res[0], res[1], _t.time())
            return res
    resn = _nv_signup_new()
    if not resn:
        raise EMError("nv: هیچ ئەکاونت")
    try:
        _na = (NV_ST.get("accounts") or [])[-1]
        _TLS.nv_acc = _na
        with _NV_LK:
            NV_ST.setdefault("toks", {})[_na.get("email")] = (resn[0], resn[1], _t.time())
    except Exception:
        pass
    return resn


def _nv_rotate():
    import time as _ts
    accs = NV_ST.get("accounts") or []
    if not accs:
        return bool(_nv_signup_new())
    ex = NV_ST.get("exhausted") or {}
    xc = NV_ST.get("exc") or {}
    now = _ts.time()
    chosen = None
    with _NV_LK:
        _n = len(accs)
        for _pass in (0, 1):  # #94U37: لە کۆتاییەوە (نوێترین یەکەم — کرێدیتی تازە)؛ pass 0: exc<3
            for _i in range(_n):
                _j = _n - 1 - _i
                acc = accs[_j]
                if float(ex.get(acc["email"], 0)) > now:
                    continue  # هێشتا سارد نەبووەتەوە (کۆڵ ٦٠٠ چرکە)
                if _pass == 0 and (xc.get(acc["email"], 0) or 0) >= 3:
                    continue  # #94U36: ٣+ insufficient ئەمڕۆ — مەیدەرەوە ئەگەر ئاڵتەرناتیڤ هەیە
                NV_ST["idx"] = _j
                chosen = acc
                break
            if chosen is not None:
                break
    if chosen is not None:
        _TLS.nv_acc = chosen
        NV_ST["tok"] = None
        _nv_save_acc()
        return True
    res = _nv_signup_new()
    if res:
        try:
            _TLS.nv_acc = (NV_ST.get("accounts") or [])[-1]
        except Exception:
            pass
        return True
    # فەرموودەی کۆتایی — ئەگەر ساینئەپ شکست خوارد، هەر ئەکاونتێک (تەنانەت ساردبوو)
    with _NV_LK:
        NV_ST["idx"] = (NV_ST["idx"] + 1) % len(accs)
        _TLS.nv_acc = accs[NV_ST["idx"]]
    NV_ST["tok"] = None
    _nv_save_acc()
    return True


def nv_chat(messages, model_id, timeout=110):
    """چاتی Nova — هەمان فلۆوی §2.29 + حەوزی ئەکاونت (٥ نامەی خۆڕایی/ئەکاونت)"""
    import time as _t, uuid as _u
    meta = (MS.get("nv_ok") or {}).get(model_id)
    if not meta:
        raise EMError("nv: مۆدێڵ نییە")
    bot_id = meta.get("botId") or 0
    tier = meta.get("tier") or "f"
    max_att = 3 if tier == "p" else (1 if tier == "x" else 12)  # #94U37: 8→12 بۆ punch-through لەناو مردووەکان
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("nv: هیچ نامە")
    lines.append("[Assistant]")
    prompt = _flat_cut(lines)
    last_err = ""
    import datetime as _dtm
    _today = _dtm.datetime.utcnow().strftime("%Y-%m-%d")
    _ens_retried = set()  # #94U37: ensure+retry یەک جار بۆ هەر ئەکاونتێک لەم بانگەوازە
    for attempt in range(max_att):
        try:
            tok, uid = _nv_token()
        except EMError:
            if not _nv_rotate():
                raise
            continue
        H = {"User-Agent": NV_UA, "Content-Type": "application/json", "accept": "text/event-stream",
             "X_Token": tok, "X_User_Id": uid, "X_Platform": "web", "X_Model": str(bot_id),
             "Origin": "https://chat.novaapp.ai", "Referer": "https://chat.novaapp.ai/"}
        if True:  # #94U36: ensure-credits بۆ هەموو tier (پێشتر تەنها p/x) — grant ئەگەر مابێت
            accs0 = NV_ST.get("accounts") or []
            em0 = accs0[NV_ST["idx"] % len(accs0)]["email"] if accs0 else ""
            en = NV_ST.setdefault("ensured", {})
            if en.get(em0) != _today:
                try:
                    requests.get(NV_BASE + "/api/v2/ensure-credits",
                                 headers={"User-Agent": NV_UA, "X_Token": tok, "X_User_Id": uid,
                                          "X_Platform": "web", "Origin": "https://chat.novaapp.ai",
                                          "Referer": "https://chat.novaapp.ai/"}, timeout=(10, 20))
                except Exception:
                    pass
                en[em0] = _today
                _nv_save_acc()
        body = {"botId": bot_id, "sessionId": _u.uuid4().hex[:20],
                "userPseudoId": f"{_u.uuid4().int % 10 ** 9}.{int(_t.time())}",
                "hubxId": str(_u.uuid4()),
                "message": {"prompt": prompt, "messageId": str(_u.uuid4())},
                "actions": {"webSearch": False, "createImage": False, "deepSearch": False, "privateSearch": False}}
        try:
            r = requests.post(NV_BASE + "/api/v2/chat", json=body, headers=H,
                              timeout=(15, timeout), stream=True)
        except Exception as e:
            raise EMError(f"nv: {str(e)[:60]}")
        if r.status_code != 200:
            raw = b""
            try:
                for ch in r.iter_content(chunk_size=None):
                    raw += ch
                    if len(raw) > 300:
                        break
            except Exception:
                pass
            msg = ""
            try:
                msg = (json.loads(raw.decode("utf-8", "replace")).get("data") or {}).get("message", "")
            except Exception:
                msg = raw[:60].decode("utf-8", "replace")
            last_err = msg or str(r.status_code)
            if "Insufficient chat credit" in msg:
                if tier == "x":
                    raise EMError("nv: پرێمیۆمی-قورس — بە پارە بەردەستە")
                acc = getattr(_TLS, "nv_acc", None)
                if acc is None:
                    _accs = NV_ST.get("accounts") or []
                    acc = _accs[NV_ST["idx"] % len(_accs)] if _accs else None
                _em = (acc or {}).get("email") or ""
                if acc is not None and _em not in _ens_retried:  # #94U37: grant ماوە؟ — ensure + 1 retry پێش ناسناخەکە
                    _ens_retried.add(_em)
                    try:
                        requests.get(NV_BASE + "/api/v2/ensure-credits",
                                     headers={"User-Agent": NV_UA, "X_Token": tok, "X_User_Id": uid,
                                              "X_Platform": "web", "Origin": "https://chat.novaapp.ai",
                                              "Referer": "https://chat.novaapp.ai/"}, timeout=(10, 20))
                    except Exception:
                        pass
                    try:
                        NV_ST.setdefault("ensured", {})[_em] = _today
                        _nv_save_acc()
                    except Exception:
                        pass
                    _t.sleep(2)
                    continue  # هەمان ئەکاونت دووبارە (بێ rotate، بێ exc+)
                if acc is not None:
                    NV_ST.setdefault("exhausted", {})[acc["email"]] = _t.time() + 600  # کۆڵ ١٠ خولەک
                    _replace_dead_soon("nv")  # #94U24: لە جێی ئەمە → نوێ یەکسەر
                    NV_ST.setdefault("exc", {})[acc["email"]] = (NV_ST.get("exc") or {}).get(acc["email"], 0) + 3  # #94U37: پشتڕاستکراوە-مردوو (دوای ensure+retry) → skip یەکسەر
                if not _nv_rotate():
                    raise EMError("nv: حەوزی ئەکاونتەکان تەواوە")
                _t.sleep(1.5)
                continue
            if "No agent mapping" in msg:
                MS.setdefault("nv_bad", {})[model_id] = {"t": _t.time(), "why": "no-mapping"}
                MS.get("nv_ok", {}).pop(model_id, None)
                _ms_save()
                raise EMError("nv: مۆدێڵ نەماوە")
            raise EMError(f"nv: {last_err[:60]}")
        parts = []
        for line in r.iter_lines(decode_unicode=True):
            if not line.startswith("data:"):
                continue
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            dd = d.get("data") or {}
            if isinstance(dd, dict):
                c = dd.get("content")
                if isinstance(c, dict) and c.get("parts"):
                    for p in c["parts"]:
                        if isinstance(p, dict) and p.get("thought"):
                            continue  # پارچەی بیرکردنەوە — فڕێدان
                        parts.append((p or {}).get("text", "") if isinstance(p, dict) else str(p))
        if not parts:
            _tok_drop("nv")
            NV_ST["tok"] = None
            last_err = "بەتاڵ"
            continue
        # پترن: دێڵتا زیادەکان + لە کۆتایی ڕووداوی کۆتایی-کۆکراو
        if len(parts) > 1 and parts[-1].startswith("".join(parts[:-1])):
            ans = parts[-1].strip()
        else:
            ans = "".join(parts).strip()
        if ans:
            return ans
        last_err = "بەتاڵ"
        _tok_drop("nv")
        NV_ST["tok"] = None
    raise EMError(f"nv: {last_err[:60] or 'شکست'}")


def nv_servers():
    out = []
    for k, meta in sorted((MS.get("nv_ok") or {}).items()):
        out.append({"id": f"nv-{re.sub(r'[^a-z0-9]+', '-', str(k).lower()).strip('-') or 'model'}",
                    "name": f"{(meta or {}).get('label') or k} (NV)", "model_id": k, "kind": "nv"})
    return out


def sync_nv_models(force=False):
    """ئۆتۆ-ئەپدێتی Nova: کاتالۆگی webcms — تەنها مۆدێڵی هەرزان (botId ∈ NV_FREE_BOTS)"""
    import time as _t
    if not force and _t.time() - _NV_SYNC["t"] < 21600:
        return
    _NV_SYNC["t"] = _t.time()
    try:
        r = requests.get(NV_CMS, headers={"User-Agent": NV_UA, "Origin": "https://chat.novaapp.ai",
                                          "Referer": "https://chat.novaapp.ai/"}, timeout=(10, 40))
        if r.status_code != 200:
            print(f"[NV-SYNC] catalog {r.status_code}", flush=True)
            return
        items = (r.json() or {}).get("data") or []
        ok = {}
        for m in items:
            k = (m or {}).get("modelKey") or ""
            b = m.get("botId")
            if not k or k in NV_SKIP_KEYS or b is None:
                continue
            if (m.get("type") or "") != "text":
                continue
            # تەنها خۆڕاییەکان لە مینیو — پرێمیۆم/نەناسراو لادەبرێن (پارەدار)
            if b not in NV_FREE_BOTS:
                continue
            lbl = m.get("title") or k
            if lbl.startswith("models."):
                lbl = (NV_FREE_BOTS.get(b) or k)
            ok[k] = {"botId": b, "label": lbl, "tier": "f"}
        if ok:
            MS["nv_ok"] = ok
            _ms_save()
            print(f"[NV-SYNC] کاتالۆگ {len(items)} → تۆمارکراو {len(ok)}", flush=True)
    except Exception as e:
        print(f"[NV-SYNC] {str(e)[:80]}", flush=True)


# ══════════ AllChatBots (allchatbots.ai) — §2.33 — Supabase + کوکی سێشن ══════════
# تێبینی: سایتەکە پارەدارە — بێ سەبسکریپشن 402 دەدات → tier=x (فەیلئۆڤەری خۆکار بۆ هەمان مۆدێڵ لە سەرچاوەکانی تر)
# ئەگەر ئەکاونتەکە سەبسکریپشی هەبوو → tier بگۆڕە بۆ f و هەموو ٤٨ مۆدێڵ ڕاستەوخۆ کار دەکەن
AL_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlbHpxd2R4Zml0YXprcmt0eWtlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNTQ0OTMsImV4cCI6MjA5MjczMDQ5M30.3xKzSovrFhxu-ptma0-u_5QweO0QHjeBqWoLTbRasY0"
AL_SB = "https://felzqwdxfitazkrktyke.supabase.co"
AL_BASE = "https://allchatbots.ai"
AL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
AL_COOKIE = "sb-felzqwdxfitazkrktyke-auth-token"
AL_ACC_FILE = os.path.join(DATA_DIR, "al_accounts.json")
AL_ST = {"sess": None, "sess_t": 0.0, "idx": 0,
         "accounts": [{"email": "pimeyax560@dreameg.com", "password": "pimeyax560@dreameg.com"}]}
_AL_SYNC = {"t": 0.0}
AL_MODELS = {
    "gpt-6-astra": "GPT-6 Astra", "gpt-5.6-sol": "GPT-5.6 Sol", "gpt-5.6-terra": "GPT-5.6 Terra",
    "gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.5": "GPT-5.5", "gpt-5.4": "GPT-5.4",
    "gpt-5.4-mini": "GPT-5.4 mini", "gpt-5.4-nano": "GPT-5.4 nano", "gpt-5": "GPT-5",
    "gpt-5-mini": "GPT-5 mini", "gpt-5-nano": "GPT-5 nano", "gpt-4.1": "GPT-4.1",
    "claude-opus-5": "Claude Opus 5", "claude-opus-4-8": "Claude Opus 4.8", "claude-opus-4-7": "Claude Opus 4.7",
    "claude-opus-4-6": "Claude Opus 4.6", "claude-opus-4-5": "Claude Opus 4.5", "claude-sonnet-5": "Claude Sonnet 5",
    "claude-sonnet-4-6": "Claude Sonnet 4.6", "claude-sonnet-4-5": "Claude Sonnet 4.5",
    "claude-haiku-4-5": "Claude Haiku 4.5", "claude-fable-5-1": "Claude Fable 5.1", "claude-fable-5": "Claude Fable",
    "gemini-3.1-pro": "Gemini 3.1 Pro", "gemini-2.5-pro": "Gemini 2.5 Pro", "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-3.7-flash": "Gemini 3.7 Flash", "gemini-3.6-flash": "Gemini 3.6 Flash", "gemini-3.5-flash": "Gemini 3.5 Flash",
    "gemini-2.5-flash": "Gemini 2.5 Flash", "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "grok-4.6": "Grok 4.6", "grok-4.5": "Grok 4.5", "grok-4": "Grok 4", "grok-3": "Grok 3", "grok-3-mini": "Grok 3 mini",
    "deepseek-v4-pro": "DeepSeek V4 Pro", "deepseek-v4-flash": "DeepSeek V4 Flash",
    "deepseek-chat": "DeepSeek V3", "deepseek-reasoner": "DeepSeek R1",
    "openrouter-auto": "OpenRouter Auto", "kimi-k3": "Kimi K3", "moonshot-32k": "Moonshot v1 32k",
    "moonshot-128k": "Moonshot v1 128k", "mistral-large": "Mistral Large", "mistral-medium": "Mistral Medium",
    "mistral-small": "Mistral Small", "auto": "Auto"}


def _al_load_acc():
    import json as _j
    try:
        d = _json_load_safe(AL_ACC_FILE) or {}
        if d.get("accounts"):
            AL_ST["accounts"] = d["accounts"]
        AL_ST["idx"] = int(d.get("idx") or 0)
    except Exception:
        pass


def _al_save_acc():
    import json as _j
    try:
        _json_save(AL_ACC_FILE, {"accounts": AL_ST.get("accounts") or [], "idx": AL_ST["idx"]})
    except Exception:
        pass


_al_load_acc()




def _al_signup_new():
    """#91AA: سایناپی نوێی allchatbots (Supabase) — پۆڵی ئەکاونت دروست دەکات"""
    try:
        import random as _r, string as _s2
        user = "al" + "".join(_r.choices(_s2.ascii_lowercase + _s2.digits, k=8))
        em, pw = f"{user}@dreameg.com", "Al" + "".join(_r.choices(_s2.ascii_letters + _s2.digits, k=10)) + "!7"
        r = requests.post(AL_SB + "/auth/v1/signup",
                          headers={"apikey": AL_KEY, "Content-Type": "application/json"},
                          json={"email": em, "password": pw}, timeout=(10, 25))
        if r.status_code != 200:
            return False
        AL_ST.setdefault("accounts", []).append({"email": em, "password": pw})
        AL_ST["idx"] = len(AL_ST["accounts"]) - 1
        AL_ST["sess"] = None
        _al_save_acc()
        print(f"[AL] ئەکاونتی نوێ ✅ {em}", flush=True)
        return True
    except Exception as e:
        print(f"[AL] سایناپ: {str(e)[:50]}", flush=True)
        return False


def _al_rotate():
    """#91AA: ئەکاونتی دواتر — ئەگەر هیچ نەما سایناپی نوێ"""
    accs = AL_ST.get("accounts") or []
    AL_ST["idx"] = (AL_ST.get("idx", 0) + 1) % max(len(accs), 1)
    AL_ST["sess"] = None
    _al_save_acc()
    return bool(_al_signup_new())

def _al_login(force=False):
    """چوونەژوورەوەی Supabase — سێشن (~٥٠ خولەک کاش)"""
    import time as _t
    if not force and AL_ST.get("sess") and _t.time() - AL_ST.get("sess_t", 0) < 2700:
        return AL_ST["sess"]
    accs = AL_ST.get("accounts") or []
    if not accs:
        raise EMError("al: هیچ ئەکاونت")
    acc = accs[AL_ST["idx"] % len(accs)]
    try:
        r = requests.post(AL_SB + "/auth/v1/token?grant_type=password",
                          headers={"apikey": AL_KEY, "Content-Type": "application/json"},
                          json={"email": acc["email"], "password": acc["password"]}, timeout=(10, 25))
    except Exception as e:
        raise EMError(f"al: {str(e)[:60]}")
    if r.status_code != 200 or not (r.json() or {}).get("access_token"):
        # #91AA: ئەکاونتی مردوو → ئەکاونتی دواتر/سایناپی نوێ
        AL_ST["idx"] += 1
        try:
            _al_rotate()
            return _al_login(force=True)
        except Exception:
            raise EMError("al: چوونەژوورەوە شکست")
    AL_ST["sess"] = r.json()
    AL_ST["sess_t"] = _t.time()
    _al_save_acc()
    return AL_ST["sess"]


def al_chat(messages, model_id, timeout=110):
    """چاتی AllChatBots — کوکی سێشن + /api/chat — 402 → فەیلئۆڤەر"""
    sess = _al_login()
    lines = []
    for m in _sys_keep(messages, 11):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        if role == "system":
            lines.append("[Instructions] " + c)
        elif role == "user":
            lines.append("[User] " + c)
        else:
            lines.append("[Assistant] " + c)
    if not lines:
        raise EMError("al: هیچ نامە")
    lines.append("[Assistant]")
    prompt = _flat_cut(lines)
    H = {"User-Agent": AL_UA, "Content-Type": "application/json",
         "Origin": "https://allchatbots.ai", "Referer": "https://allchatbots.ai/"}
    ck = {AL_COOKIE: json.dumps(sess)}
    body = {"messages": [{"role": "user", "content": prompt}], "modelId": model_id, "stream": False}
    for attempt in range(2):
        try:
            r = requests.post(AL_BASE + "/api/chat", json=body, headers=H, cookies=ck, timeout=(15, timeout))
        except Exception as e:
            raise EMError(f"al: {str(e)[:60]}")
        if r.status_code in (401, 403) and attempt == 0:
            sess = _al_login(force=True)
            ck = {AL_COOKIE: json.dumps(sess)}
            continue
        if r.status_code == 402:
            raise EMError("al: سەبسکریپشن پێویستە — دەگوازرێتەوە")
        if r.status_code == 429:
            raise EMError("al: لیمیت")
        if r.status_code != 200:
            raise EMError(f"al: HTTP{r.status_code}")
        ct = (r.headers.get("content-type") or "")
        if "text/event" in ct:
            parts = []
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except Exception:
                    continue
                for k in ("content", "text", "delta"):
                    v = d.get(k)
                    if isinstance(v, str):
                        parts.append(v)
                        break
            ans = "".join(parts).strip()
        else:
            try:
                j = r.json()
            except Exception:
                raise EMError("al: وەڵامی نەناسراو")
            ans = ""
            for cand in (j.get("content"), j.get("message"), j.get("text"),
                         (j.get("choices") or [{}])[0].get("message", {}).get("content") if isinstance(j.get("choices"), list) else None):
                if isinstance(cand, str) and cand.strip():
                    ans = cand.strip()
                    break
        if ans:
            return ans
        raise EMError("al: بەتاڵ")
    raise EMError("al: شکست")


def al_servers():
    return []  # پارەدار — لابراو لە مینیو (ڕیسێپی پارێزراوە لە کۆد)


def sync_al_models(force=False):
    """تۆمارکردنی کاتالۆگی AL — ٦ کاتژمێر (لیستی ناو-کۆد — لە چانکەکانی فرۆنتئێند دەرهێنراوە)"""
    import time as _t
    if not force and _t.time() - _AL_SYNC["t"] < 21600:
        return
    _AL_SYNC["t"] = _t.time()
    MS["al_ok"] = {}
    _ms_save()
    print("[AL-SYNC] پاشکراوە — تەنها بە سەبسکریپشن چالاک دەبێت", flush=True)


# ══════════ AI/ML API (aimlapi.com) — §2.34 — دەروازەی 938 مۆدێڵ (پارەدار — tier-x) ══════════
# لۆگین: PUT auth.aimlapi.com/v1/auth/account {email,password} + aim-device-id → token (~11کاتژمێر)
# کلیل: POST app.aimlapi.com/v1/keys → چات: POST api.aimlapi.com/v1/chat/completions (OpenAI-جۆر)
# ئەکاونت بێ-فەندز → 403 → هەڵەی جوان → فەیلئۆڤەری هەمان مۆدێڵ لە سەرچاوەکانی تر
AIML_ACC_FILE = os.path.join(DATA_DIR, "aiml_key.json")
AIML_ST = {"tok": None, "tok_t": 0.0, "key": None,
           "email": "pimeyax560@dreameg.com", "password": "12345678Rkjk@&"}
_AIML_SYNC = {"t": 0.0}
AIML_MODELS = {
    "openai/gpt-6-astra": "GPT-6 Astra", "openai/gpt-5.6-sol-pro": "GPT-5.6 Sol Pro",
    "openai/gpt-5.6-sol": "GPT-5.6 Sol", "openai/gpt-5.6-terra-pro": "GPT-5.6 Terra Pro",
    "openai/gpt-5.6-terra": "GPT-5.6 Terra", "openai/gpt-5.6-luna-pro": "GPT-5.6 Luna Pro",
    "openai/gpt-5.6-luna": "GPT-5.6 Luna", "openai/gpt-5-5-pro": "GPT-5.5 Pro",
    "openai/gpt-5-5": "GPT-5.5", "openai/gpt-5-4-pro": "GPT-5.4 Pro", "openai/gpt-5-4": "GPT-5.4",
    "openai/gpt-5.4-mini": "GPT-5.4 Mini", "openai/gpt-5.4-nano": "GPT-5.4 Nano",
    "openai/gpt-5-3-codex": "GPT-5.3 Codex", "openai/gpt-5-2-pro": "GPT-5.2 Pro",
    "openai/gpt-5-2": "GPT-5.2", "openai/gpt-5-1": "GPT-5.1", "openai/gpt-5": "GPT-5",
    "openai/gpt-5-mini": "GPT-5 Mini", "openai/gpt-5-nano": "GPT-5 Nano",
    "openai/gpt-4.1": "GPT-4.1", "openai/gpt-4o": "GPT-4o", "openai/gpt-4o-mini": "GPT-4o Mini",
    "openai/o3-pro": "o3 Pro", "openai/o3-mini": "o3 Mini", "openai/gpt-oss-120b": "GPT OSS 120B",
    "anthropic/claude-opus-5": "Claude Opus 5", "anthropic/claude-opus-4.8": "Claude Opus 4.8",
    "anthropic/claude-opus-4.7": "Claude Opus 4.7", "anthropic/claude-opus-4.5": "Claude Opus 4.5",
    "anthropic/claude-sonnet-5": "Claude Sonnet 5", "anthropic/claude-sonnet-4.6": "Claude Sonnet 4.6",
    "anthropic/claude-haiku-4.5": "Claude 4.5 Haiku", "anthropic/claude-fable-5.1": "Claude Fable 5.1",
    "anthropic/claude-fable-5": "Claude Fable 5", "anthropic/claude-3-haiku": "Claude 3 Haiku",
    "google/gemini-3.8-flash": "Gemini 3.8 Flash", "google/gemini-3.7-flash": "Gemini 3.7 Flash",
    "google/gemini-3.6-flash": "Gemini 3.6 Flash", "google/gemini-3.5-flash": "Gemini 3.5 Flash",
    "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro", "google/gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "google/gemini-2.5-pro": "Gemini 2.5 Pro", "google/gemini-2.5-flash": "Gemini 2.5 Flash",
    "google/gemma-4-31b-it": "Gemma 4 31B",
    "x-ai/grok-4-6": "Grok 4.6", "x-ai/grok-4-5": "Grok 4.5", "x-ai/grok-4-3": "Grok 4.3",
    "x-ai/grok-4-20-0309-reasoning": "Grok 4.20", "x-ai/grok-4-1-fast-reasoning": "Grok 4.1 Fast",
    "x-ai/grok-code-fast-1": "Grok Code Fast",
    "moonshot/kimi-k3": "Kimi K3", "moonshot/kimi-k2-7-code": "Kimi K2.7 Code",
    "moonshot/kimi-k2-5": "Kimi K2.5", "moonshotai/kimi-latest": "Kimi Latest",
    "deepseek/deepseek-v4.1-flash": "DeepSeek V4.1 Flash", "deepseek/deepseek-v4-pro": "DeepSeek V4 Pro",
    "deepseek/deepseek-v4-flash": "DeepSeek V4 Flash", "deepseek/deepseek-chat": "DeepSeek Chat",
    "deepseek/deepseek-reasoner": "DeepSeek R1", "deepseek/deepseek-thinking-v3.2-exp": "DeepSeek V3.2 Think",
    "minimax/minimax-m3": "MiniMax M3", "minimax/m2-7-highspeed": "MiniMax M2.7",
    "minimax/m2-5-20260218": "MiniMax M2.5", "minimax/m1": "MiniMax M1",
    "zhipu/glm-5.3": "GLM 5.3", "zhipu/glm-5.2": "GLM 5.2", "zhipu/glm-5-1": "GLM 5.1",
    "zhipu/glm-5": "GLM 5", "zhipu/glm-4.7": "GLM 4.7", "z-ai/glm-5v-turbo": "GLM 5V Turbo",
    "alibaba/qwen3.8-max": "Qwen 3.8 Max", "alibaba/qwen3.8-flash": "Qwen 3.8 Flash",
    "alibaba/qwen3.7-max": "Qwen 3.7 Max", "alibaba/qwen3.6-plus": "Qwen 3.6 Plus",
    "alibaba/qwen3-max": "Qwen 3 Max",
    "bytedance/seed-2-0-pro": "Seed 2.0 Pro", "bytedance/seed-2-0-lite": "Seed 2.0 Lite",
    "bytedance/seed-2-0-mini": "Seed 2.0 Mini", "bytedance/seed-1-8": "Seed 1.8",
    "meta/muse-spark-1.3": "Muse Spark 1.3", "meta/muse-glimmer-30b": "Muse Glimmer 30B",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra", "nvidia/nemotron-3-super-120b-a12b": "Nemotron 3 Super",
    "nvidia/nemotron-3-nano-30b-a3b": "Nemotron 3 Nano",
    "tencent/hy4-preview": "Hy4 Preview", "tencent/hy3": "Hy3",
    "baidu/ernie-5.0": "ERNIE 5.0", "amazon/nova-pro-v1": "Nova Pro 1.0",
    "amazon/nova-lite-v1": "Nova Lite 1.0", "amazon/nova-micro-v1": "Nova Micro 1.0",
    "stepfun/step-3.7-flash": "Step 3.7 Flash", "xiaomi/mimo-v2.5-pro": "MiMo V2.5 Pro",
    "upstage/solar-pro4": "Solar Pro 4", "writer/palmyra-x5": "Palmyra X5",
    "thinkingmachines/inkling": "Inkling", "inception/mercury-2.5": "Mercury 2.5",
    "mistralai/mistral-medium-3.5": "Mistral Medium 3.5", "mistralai/mistral-large": "Mistral Large",
    "mistralai/codestral-2508": "Codestral", "cohere/command-a": "Command A",
    "perplexity/sonar-pro": "Sonar Pro", "perplexity/sonar": "Sonar",
    "nousresearch/hermes-4-405b": "Hermes 4 405B", "ibm-granite/granite-4.2-8b": "Granite 4.2 8B",
    "sakana/fugu-ultra-v2": "Fugu Ultra v2", "stealth/union-alpha": "Union Alpha",
    "typesafe/jev": "Jev 1.13", "meituan/longcat-2.0": "LongCat 2.0", "poolside/laguna-s-2.1": "Laguna S 2.1"}


def _aiml_load():
    import json as _j
    try:
        d = _j.load(open(AIML_ACC_FILE, encoding="utf-8"))
        AIML_ST["key"] = d.get("key")
    except Exception:
        pass


def _aiml_save():
    import json as _j
    try:
        _j.dump({"key": AIML_ST.get("key")}, open(AIML_ACC_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    except Exception:
        pass


_aiml_load()


def _aiml_login():
    import time as _t, uuid as _u
    if AIML_ST.get("tok") and _t.time() - AIML_ST.get("tok_t", 0) < 30000:
        return AIML_ST["tok"]
    try:
        r = requests.put("https://auth.aimlapi.com/v1/auth/account",
                         json={"email": AIML_ST["email"], "password": AIML_ST["password"]},
                         headers={"aim-device-id": str(_u.uuid4()), "User-Agent": "Mozilla/5.0",
                                  "Origin": "https://aimlapi.com", "Referer": "https://aimlapi.com/"},
                         timeout=(15, 30))
        if r.status_code != 200:
            raise EMError(f"aiml-login {r.status_code}")
        AIML_ST["tok"] = r.json().get("token")
        AIML_ST["tok_t"] = _t.time()
        return AIML_ST["tok"]
    except EMError:
        raise
    except Exception as e:
        raise EMError(f"aiml: {str(e)[:60]}")


def _aiml_ensure_key():
    tok = _aiml_login()
    H = {"Authorization": f"Bearer {tok}", "User-Agent": "Mozilla/5.0"}
    if AIML_ST.get("key"):
        return AIML_ST["key"]
    # کیلی هەیە؟
    r = requests.get("https://app.aimlapi.com/v1/keys", headers=H, timeout=(15, 30))
    items = (r.json() or {}).get("items") or []
    if not items:
        r2 = requests.post("https://app.aimlapi.com/v1/keys", headers=H, json={"name": "ta3afi"}, timeout=(15, 30))
        if r2.status_code not in (200, 201):
            raise EMError(f"aiml-key {r2.status_code}")
        items = [r2.json()]
    # تەنها لە کاتی دروستکردندا key تەواو دەدرێت — ئەگەر کۆنەکە نەمانەوە، دووبارە دروست بکە
    full = (items[0] or {}).get("key")
    if not full:
        r3 = requests.post("https://app.aimlapi.com/v1/keys", headers=H, json={"name": "ta3afi"}, timeout=(15, 30))
        if r3.status_code not in (200, 201):
            raise EMError(f"aiml-key {r3.status_code}")
        full = (r3.json() or {}).get("key")
    if not full:
        raise EMError("aiml: هیچ کلیل")
    AIML_ST["key"] = full
    _aiml_save()
    return full


def aiml_chat(messages, model_id, timeout=110):
    """چاتی AI/ML API — OpenAI-جۆر — 403 (فەندز) → فەیلئۆڤەر"""
    lines = []
    for m in _sys_keep(messages, 19):
        role = m.get("role")
        c = (m.get("content") or "").strip()
        if not c:
            continue
        lines.append({"role": role, "content": c})
    if not lines:
        raise EMError("aiml: هیچ نامە")
    key = _aiml_ensure_key()
    try:
        r = requests.post("https://api.aimlapi.com/v1/chat/completions",
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                   "User-Agent": "Mozilla/5.0"},
                          json={"model": model_id, "messages": lines}, timeout=(15, timeout))
    except Exception as e:
        raise EMError(f"aiml: {str(e)[:60]}")
    if r.status_code in (401, 403):
        try:
            j = r.json()
        except Exception:
            j = {}
        msg = str((j.get("message") or j.get("error") or ""))[:60]
        if "funds" in msg.lower():
            MS.get("aiml_ok", {}).pop(model_id, None)
            _ms_save()
            raise EMError("aiml: فەندز — دەگوازرێتەوە بۆ سەرچاوەی هەمان مۆدێڵ")
        if r.status_code == 401:
            # #91AA: token+key یەکسان نوێ بکرێنەوە — بێ دەستێوەردان
            def _aiml_renew():
                try:
                    AIML_ST["tok"] = None
                    AIML_ST["key"] = None
                    AIML_ST["tok_t"] = 0.0
                    _aiml_login()
                    _aiml_ensure_key()
                    print("[AIML] 🔁 token+key نوێ کرایەوە", flush=True)
                except Exception:
                    pass
            threading.Thread(target=_aiml_renew, daemon=True).start()
            raise EMError("aiml: توکن")
        raise EMError(f"aiml: {msg or r.status_code}")
    if r.status_code == 429:
        raise EMError("aiml: لیمیت")
    if r.status_code != 200:
        raise EMError(f"aiml: HTTP{r.status_code}")
    try:
        j = r.json()
        ans = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
        if isinstance(ans, list):
            ans = "".join(x.get("text", "") for x in ans if isinstance(x, dict))
        ans = (ans or "").strip()
        if ans:
            return ans
    except Exception:
        pass
    raise EMError("aiml: بەتاڵ")


def aiml_servers():
    return []  # پارەدار — لابراو لە مینیو (ڕیسێپی پارێزراوە لە کۆد)


def sync_aiml_models(force=False):
    """تۆمارکردنی کاتالۆگی AI/ML — ٦ کاتژمێر — tier=x"""
    import time as _t
    if not force and _t.time() - _AIML_SYNC["t"] < 21600:
        return
    _AIML_SYNC["t"] = _t.time()
    MS["aiml_ok"] = {}
    _ms_save()
    print("[AIML-SYNC] پاشکراوە — تەنها بە فەندز چالاک دەبێت", flush=True)


def _ms_dup(servers, model_id):
    """ئایا ئەم مۆدێڵە پێشتر لە سەرچاوەیەکی تر هەیە؟ — دژە-دووبارە"""
    n = norm_model(model_id)
    if not n:
        return True
    for x in servers:
        if n in norm_model(x["id"]) or n in norm_model(str(x.get("model_id", ""))):
            return True
    return False


def sync_duck_models(servers):
    """لیستی مۆدێڵە ڕاییگەکانی duck.ai ڕاستەوخۆ لە bundle ی فەرمی — هەر ٣٠ خولەک"""
    if time.time() - MS_T["duck"] < 1800:
        return
    with MS_LOCK:
        if time.time() - MS_T["duck"] < 1800:
            return
        MS_T["duck"] = time.time()
    try:
        s = _duck_session()
        r = s.get("https://duck.ai/", headers={"Accept": "text/html", "Upgrade-Insecure-Requests": "1"},
                  timeout=(15, 25))
        m = re.search(r'(/dist/duckai-dist/entry\.duckai\.[A-Za-z0-9]+\.js)', r.text)
        if not m:
            print("[SYNC] duck: bundle نەدۆزرایەوە", flush=True)
            return
        r2 = s.get("https://duck.ai" + m.group(1), timeout=(15, 40))
        js = r2.text
        found = {}
        for mo in re.finditer(r'\{model:"([a-z0-9./\-]+)",modelName:"[^"]*",modelVariant:"([^"]*)",'
                              r'modelShortName:"([^"]*)".{0,600}?availableTo:\[([^\]]*)\]', js):
            mid, variant, short, avail = mo.group(1), mo.group(2), mo.group(3), mo.group(4)
            if "Free" not in avail:
                continue
            found[mid] = short or variant or mid
        for mo in re.finditer(r'\{model:"([a-z0-9./\-]+)",upgradeModel:"[^"]+"\}', js):
            found.pop(mo.group(1), None)  # مردووەکان لاببە
        newd = {}
        for mid, short in found.items():
            slug = re.sub(r'[^a-z0-9.]+', '-', mid.lower()).strip('-')
            newd[mid] = {"id": f"duck-{slug}", "name": f"{short} (Duck)",
                         "model_id": mid, "kind": "duck"}
        old_ids = set(MS.get("duck", {}).keys())
        MS["duck"] = newd
        _ms_save()
        extras = [k for k in newd if not _ms_dup(servers, k)]
        print(f"[SYNC] duck: {len(newd)} مۆدێڵی ڕاییگە ({','.join(newd)}) | نوێ: {extras}", flush=True)
    except Exception as e:
        print(f"[SYNC] duck هەڵە: {str(e)[:80]}", flush=True)


def sync_ak_models(servers):
    """anakin — مۆدێڵی نوێی لیستی گشتی → پڕۆب ی بچووک؛ تەنها ئەوەی میوان کاری دەکات زیاد دەکرێت"""
    if time.time() - MS_T["ak"] < 3600:
        return
    with MS_LOCK:
        if time.time() - MS_T["ak"] < 3600:
            return
        MS_T["ak"] = time.time()
    try:
        r = requests.get("https://api.anakin.ai/api/v1/ai-models?locale=en-US",
                         headers={"User-Agent": DUCK_UA, "Origin": "https://app.anakin.ai",
                                  "Referer": "https://app.anakin.ai/", "x-client-mode": "web"},
                         timeout=(15, 25))
        data = r.json().get("data") or []
        cands = []
        for x in data:
            if not isinstance(x, dict):
                continue
            mid = x.get("modelId")
            types = x.get("types") or []
            label = str(x.get("label") or "")
            if not mid or int(mid) in (308, 309) or "chat" not in types:
                continue
            if x.get("comingSoon") or x.get("legacy"):
                continue
            if re.search(r'flex|thinking|high|low|minimal', label, re.I):
                continue
            if str(mid) in MS["ak_ok"] or str(mid) in MS["ak_block"]:
                continue
            cands.append((int(mid), label))
        cands.sort(reverse=True)  # نوێترین پێشتر
        if not cands:
            return
        # سەرەتا پشکنینی تەندروستی — ٣٠٩ دەبێت کار بکات، ئەگینا IP لە cooldown ە و پڕۆب ڕاست ناکات
        def _probe(mid, content="hi"):
            payload = json.dumps({"app_id": 19510, "model_id": int(mid),
                                  "messages": [{"role": "user", "content": content}]})
            p = subprocess.run([NODE_BIN, AK_CLIENT], input=payload.encode("utf-8"),
                               capture_output=True, timeout=60)
            lines = [l for l in (p.stdout or b"").decode("utf-8", "replace").strip().splitlines() if l.strip()]
            return json.loads(lines[-1]) if lines else {}
        chk = _probe(309)
        if not (chk.get("ok") and chk.get("answer")):
            print("[SYNC] ak: ٣٠٩ وەڵام نەدایەوە — IP لە cooldown ە، پڕۆب دوادەخرێت", flush=True)
            return
        mid, label = cands[0]
        res = _probe(mid, "Say exactly: OK")
        if res.get("ok") and res.get("answer"):
            MS["ak_ok"][str(mid)] = {"label": label, "t": time.time()}
            print(f"[SYNC] ak: مۆدێڵی نوێی میوان ✅ {mid} {label}", flush=True)
        else:
            MS["ak_block"][str(mid)] = {"label": label, "t": time.time()}
            print(f"[SYNC] ak: {mid} {label} بۆ میوان کراوە نییە", flush=True)
        _ms_save()
    except Exception as e:
        print(f"[SYNC] ak هەڵە: {str(e)[:80]}", flush=True)


def _apply_model_sync(servers):
    """هەموو مۆدێڵە دۆزراوەکان زیاد دەکرێن — بێ سڕینەوەی هیچ سەرچاوەیەک؛
       مینیو خۆی دووەکییەکان یەک دەخات (dedupe_servers) و بەک-ئێند هەردووکیان دەیهێڵێتەوە"""
    out = list(servers)
    for mid, e in MS.get("duck", {}).items():
        if not any(x["id"] == e["id"] for x in out):
            out.append(dict(e))
    for mid, info in MS.get("ak_ok", {}).items():
        sid = f"ak-{re.sub(r'[^a-z0-9]+', '-', str(info.get('label', mid)).lower()).strip('-') or mid}-{mid}"
        if not any(x["id"] == sid for x in out):
            out.append({"id": sid, "name": f"{info.get('label', mid)} (Anakin)",
                        "model_id": str(mid), "kind": "ak"})
    return out


# ─── یەکسانکردنی مۆدێڵ بۆ fallback — هەمان خێزان لە سەرچاوەیەکی تر ───
_MODEL_HINTS = [
    ("gemini", "gemini"), ("claude", "claude"), ("grok", "grok"),
    ("kimi", "kimi"), ("moonshot", "kimi"), ("qwen", "qwen"),
    ("glm", "glm"), ("z-ai", "glm"), ("deepseek", "deepseek"),
    ("llama", "llama"), ("meta-llama", "llama"), ("phi", "phi"),
    ("hy3", "hy3"), ("tencent", "hy3"), ("gemma", "gemma"),
    ("oss", "gpt"), ("o4", "gpt"), ("o3", "gpt"), ("gpt", "gpt"),
]


def _model_family(mid):
    s = str(mid).lower()
    for k, fam in _MODEL_HINTS:
        if k in s:
            return fam
    return "gpt"


def pick_in_kind(servers, kind, wanted):
    """باشترین مۆدێڵی هاوشێوە لە سەرچاوەیەکی تر — بۆ fallback ی ورد"""
    fam = _model_family(wanted)
    same = [x for x in servers if x.get("kind") == kind]
    if not same:
        return None
    for x in same:
        if _model_family(x["id"]) == fam:
            return x
    return same[0]


# ════════════════════════════════════════════════════════════
# ٣) کلایەنتی aifreeforever
# ════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════
# ٤) API — ڕووکاری HTTP (OpenAI-compatible + سادە)
# ════════════════════════════════════════════════════════════

API_PORT = int(os.environ.get("API_PORT", 8080))
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    try:
        _ak_f = os.path.join(os.path.dirname(__file__), "API_KEY.txt")
        if os.path.isfile(_ak_f):
            API_KEY = open(_ak_f).read().strip()
    except Exception:
        pass
if not API_KEY:
    API_KEY = "sk-yf-31c00f02aa9221b336d7b4a274bb375c"

# ─── پرۆمپتی بنەڕەتی API — شێوازی پرسیار و وەڵامی شەرعی (کوردی) ───
# ئەگەر ئەپەکەت سیستەم پرۆمپتی خۆی نەنێرێت، ئەمە بەکاردێت
# ⚡ مێشکی سەربەخۆی API — تەواو جیاواز لە بۆتی تێلەگرام
# بێ سیستەم پرۆمپت، بێ کەسایەتی، بێ یاساکانی بۆتەکە
API_BRAIN = {"mode": None, "servers": [], "t": 0.0}
API_REFRESH_SEC = 300


def detect_brain_api():
    """هەمان لیستی بۆت — easemate + aifreeforever + pollinations"""
    return detect_brain(allow_fallback=True)


def api_brain_ensure():
    """لیستی سێرڤەرەکانی API تازە دەکاتەوە — هەر ٥ خولەک، سەربەخۆ"""
    if API_BRAIN["servers"] and time.time() - API_BRAIN["t"] < API_REFRESH_SEC:
        return
    new = detect_brain_api()
    if new["servers"]:
        API_BRAIN["mode"], API_BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        API_BRAIN["t"] = time.time()
        print(f"[API-BRAIN] {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)


def _api_servers():
    # ناوە ڕاستەقینەکانی مۆدەڵەکان — یەک دەنگ بۆ هەر مۆدێڵ (دووەکی سەرچاوەکان لە بەک-ئێند دەمێننەوە)
    return [{"alias": x["id"], "id": x["id"], "name": x.get("name", x["id"])}
            for x in dedupe_servers(API_BRAIN["servers"])]


def _resolve_server(ref):
    ref = str(ref).strip().lower()
    for i, x in enumerate(API_BRAIN["servers"], 1):
        if ref in (f"server-{i}", str(i)) or ref == str(x["id"]).lower() or ref == str(x.get("alias", "")).lower():
            y = dict(x)
            y["alias"] = f"server-{i}"
            return y
    num = ref[3:] if ref.startswith("em-") else ref
    if num.isdigit():
        for x in API_BRAIN["servers"]:
            if x.get("kind") == "em" and str(x["model_id"]) == num:
                y = dict(x)
                y["alias"] = x["id"]
                return y
    return None


class APIHandler(http.server.BaseHTTPRequestHandler):
    def _clean_path(self):
        p = self.path.split("?")[0].rstrip("/")
        return p if p else "/"

    def _send(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "*")
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Expose-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def log_message(self, *a):
        pass

    def _extract_key(self):
        h = self.headers.get("Authorization", "").strip()
        if h:
            parts = h.split(None, 1)
            if len(parts) == 2 and parts[0].lower() == "bearer":
                return parts[1].strip()
            return h
        for hk in ("X-API-Key", "api-key", "x-api-key"):
            val = self.headers.get(hk, "").strip()
            if val:
                return val
        if "?" in self.path:
            try:
                import urllib.parse as _up
                qs = _up.parse_qs(self.path.split("?", 1)[1])
                for qk in ("key", "api_key", "token"):
                    if qk in qs and qs[qk]:
                        return qs[qk][0].strip()
            except Exception:
                pass
        return ""

    def _authed(self):
        if not API_KEY:
            return True
        k = self._extract_key()
        if not k:
            return False
        import hmac as _hmac
        return _hmac.compare_digest(k.encode(), API_KEY.encode()) or k in _API_KEYS

    def _body(self):
        cl = self.headers.get("Content-Length")
        if cl:
            try:
                n = int(cl)
                return json.loads(self.rfile.read(n).decode("utf-8", errors="replace") or "{}")
            except Exception:
                return {}
        te = self.headers.get("Transfer-Encoding", "").lower()
        if "chunked" in te:
            chunks = []
            try:
                while True:
                    line = self.rfile.readline().strip()
                    if not line:
                        break
                    chunk_len = int(line, 16)
                    if chunk_len == 0:
                        self.rfile.readline()
                        break
                    chunks.append(self.rfile.read(chunk_len))
                    self.rfile.readline()
                return json.loads(b"".join(chunks).decode("utf-8", errors="replace") or "{}")
            except Exception:
                return {}
        return {}

    def do_GET(self):
        # #91: health endpoint — چاودێری خێرا
        cp = self._clean_path()
        # #94U11: honeypot — ڕێڕەوی تەڵە بۆ دزەکەران + بڵۆکی ئایپی لەسەر API
        if cp in _HP_PATHS:
            _note_honeypot(_sec_ip(self), cp)
            return self._send(404, {"error": "not found"})
        if cp.startswith("/v1/") and _ip_blocked(_sec_ip(self)):
            return self._send(429, {"error": "blocked — خۆپاراستنی خۆکار"})
        if cp == "/health":
            st = _HEAL_STATE.get("status", {})
            def _n2(f):
                try:
                    d = _json_load_safe(os.path.join(DATA_DIR, f)) or {}
                    return len(d.get("accounts", [])) if isinstance(d, dict) else len(d)
                except Exception:
                    return 0
            def _pstat(f, cap):
                # #94U20: ژمارەی ئەکاونت + زیندووی ئەمڕۆ + بودجەی ساینئەپی ماوە
                try:
                    d = _json_load_safe(os.path.join(DATA_DIR, f)) or {}
                    accs = d.get("accounts", []) or []
                    lim = d.get("limits") or {}
                    exh = d.get("exhausted") or {}
                    today = _lim_today()
                    def _ok(a):
                        e = a.get("email") or "?"
                        if today in (lim.get(e) or {}).values():
                            return False
                        v = exh.get(e)
                        if v in (None, 0, "", False):
                            return True
                        try:
                            return float(v) <= time.time()
                        except Exception:
                            return str(v)[:10] != today
                    alive = sum(1 for a in accs if _ok(a))
                    sg = d.get("signups") or {}
                    used = sg.get("n", 0) if sg.get("date") == today else 0
                    return {"n": len(accs), "alive": alive, "signups": f"{used}/{cap}"}
                except Exception:
                    return {"n": 0, "alive": 0, "signups": f"0/{cap}"}
            try:
                api_brain_ensure()  # #94U2: /health ەش دڵنیابێت لە API-BRAIN
            except Exception:
                pass
            try:
                _self_check()
            except Exception:
                pass
            body = {
                "ok": _STS.get("ok", True),
                "self": _STS.get("last", ""),
                "time": int(time.time()),
                "models": len(dedupe_servers(BRAIN["servers"])) if BRAIN["servers"] else 0,
                "pools": {"ca": _pstat("ca_accounts.json", 10000), "cb": _pstat("cb_accounts.json", 10000), "nv": _pstat("nv_accounts.json", 10000), "ac": _pstat("ac_accounts.json", 200)},  # #94U32b
                "sources": {k: {"ok": v.get("ok"), "age_s": int(time.time() - v.get("t", 0))} for k, v in st.items()},
                "proxies": len(PROXY_ST.get("pool") or PROXY_ST.get("list") or []),
                "proxies_res": sum(1 for v in (PROXY_ST.get("pool") or {}).values() if (v or {}).get("res")),
            }
            return self._send(200, body)
        if cp in ("/", "/health"):
            api_brain_ensure()
            self._send(200, {"ok": True, "service": "smart-chatbot-api",
                             "mode": API_BRAIN["mode"], "servers": len(API_BRAIN["servers"])})
        elif cp in ("/models", "/v1/models"):
            # #94U9: کلیدی نادروست → 401 (کلیدی دروست یان بێ-کلیل → 200)
            _k = self._extract_key()
            if _k and API_KEY:
                import hmac as _hmac8
                if not (_hmac8.compare_digest(_k.encode(), API_KEY.encode()) or _k in _API_KEYS):
                    _note_badkey(_sec_ip(self))  # #94U11
                    return self._send(401, {"error": "invalid API key"})
            api_brain_ensure()
            data = [{"id": s["alias"], "object": "model", "owned_by": "smart-chatbot"}
                    for s in _api_servers()]
            self._send(200, {"object": "list", "data": data})
        else:
            self._send(404, {"error": f"not found: {self.path} — /v1/chat/completions و /v1/models"})

    def do_POST(self):
        cp = self._clean_path()
        valid_paths = ("/chat", "/v1/chat/completions", "/chat/completions", "/v1/chat", "/api/chat")
        if cp not in valid_paths:
            return self._send(404, {"error": f"not found: {self.path} — بەردەستەکان: /v1/chat/completions, /chat"})

        _PERF["req"] += 1  # #91R2: داواکاری API ۀم بژمێرە
        t_api0 = time.time()

        try:
            body = self._body()
        except Exception:
            return self._send(400, {"error": "bad json"})

        # دۆزینەوەی کلیل لە هیدەر، کوێری یان بۆدی
        key = self._extract_key() or (body.get("api_key") if isinstance(body, dict) else "") or (body.get("apiKey") if isinstance(body, dict) else "") or ""
        client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For") or (self.client_address[0] if self.client_address else "")
        # #94U11: بڵۆکی ئایپی + ژماردنی بڕوتفۆرس
        _sip = _sec_ip(self)
        if _ip_blocked(_sip):
            return self._send(429, {"error": "blocked — خۆپاراستنی خۆکار"})
        # #94U9: کلیدی درێژکراو + نادروست → 401 (بێ توندوتیژی لەسەر guest-i بێ-کلیل)
        if key and API_KEY:
            import hmac as _hmac9
            if not (_hmac9.compare_digest(key.encode(), API_KEY.encode()) or key in _API_KEYS):
                _note_badkey(_sip)  # #94U11
                return self._send(401, {"error": "invalid API key"})
        ok_rate, rate_err = _api_rate_ok(key, client_ip=client_ip)
        if not ok_rate:
            return self._send(429, {"error": rate_err})

        openai_style = cp != "/chat"
        want_stream = bool(body.get("stream")) and openai_style

        def _extract_content(c):
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                parts = []
                for p in c:
                    if isinstance(p, dict) and "text" in p:
                        parts.append(str(p["text"]))
                    elif isinstance(p, str):
                        parts.append(p)
                return " ".join(parts)
            return str(c or "")

        if openai_style:
            ref = body.get("model") or "1"
            raw_msgs = body.get("messages") or []
            msgs = []
            for m in raw_msgs:
                role = m.get("role", "user")
                c_text = _extract_content(m.get("content", ""))
                msgs.append({"role": role, "content": c_text})
            q = ""
            for m in reversed(msgs):
                if m.get("role") == "user":
                    q = m.get("content", "")
                    break
            history = _sys_keep([{"role": m.get("role", "user"), "content": m.get("content", "")}
                                   for m in msgs if m.get("role") in ("user", "assistant", "system")], 19)
            full = history  # #94U25: q هەر لەناو history ـە — دووبارە مەکە
        else:
            ref = body.get("server") or body.get("model") or 1
            raw_q = body.get("message") or body.get("prompt") or ""
            q = _extract_content(raw_q).strip()
            history = body.get("history") or []
            msgs = full
            full = _sys_keep(msgs, 19)  # #94U25

        if not q:
            return self._send(400, {"error": "پرسیار بەتاڵە"})


        api_brain_ensure()
        if not _resolve_server(ref):
            # #91F: مۆدێڵەکە ون بووە (سەرچاوەکەی لابرا) → بە خێزان/کلیل جێگۆڕ دەکرێت — وەڵام هەر دەگەڕێتەوە
            _mk = SRV_KEY_BY_ID.get(ref) or norm_model(ref)
            _fam = _model_family(ref)
            _cands = list(API_BRAIN["servers"] or [])
            _alt = next((x for x in _cands if srv_key(x) == _mk), None)
            if not _alt and _fam:
                _alt = pick_in_kind(_cands, _fam, ref)
            if not _alt:
                _alt = next((x for x in _cands if x.get("kind") == "em"), None) or (_cands[0] if _cands else None)
            if not _alt:
                return self._send(400, {"error": f"خادم غير معروف: {ref} — راجع /v1/models"})
            print(f"[API] 🧬 مۆدێڵی ون ({ref}) → جێگۆڕ: {_alt['id']}", flush=True)
            srv = dict(_alt)
            srv["alias"] = srv["id"]
        else:
            srv = _resolve_server(ref)

        print(f"[API] server={srv['id']} q={q[:50]}", flush=True)

        # ⚡ API سەربەخۆیە: تەنها نامەکانی داواکار بەکاردەهێنێت —
        # هیچ سیستەم پرۆمپت یان یاسای بۆتەکە لێرەدا نییە
        # زنجیرەی هەوڵ: سێرڤەری هەڵبژێردراو + یەکێک لە هەر سەرچاوەیەکی تر
        order = [srv]
        # ⚡ فەڵباکی خێرا: هەمان مۆدێڵ لە سەرچاوەی تر
        for alt in MODEL_SOURCES.get(srv_key(srv), []):
            if alt["id"] != srv["id"] and alt not in order:
                order.append(alt)
        # #87: em فەیبل-5 → ca-claude-fable (فەیبل 5.1 — هەمان خێزان) پێش هەر سەرچاوەیەکی تر
        if srv.get("kind") == "em" and "fable" in str(srv.get("id", "")).lower():
            fab = next((x for x in API_BRAIN["servers"] if x.get("id") == "ca-claude-fable"), None)
            if fab and fab not in order:
                order.append(fab)
        for kind in ("em", "aff", "rwd", "l7", "g4f", "pol"):
            if srv.get("kind") != kind:
                cand = pick_in_kind(API_BRAIN["servers"], kind, srv["id"])
                if cand and cand not in order:
                    order.append(cand)

        content, last_err = "", None
        _spare = None  # #94U27: وەڵامی تێکچوو — تەنها ئەگەر هیچی تر نەبوو
        # #94U26b: پرۆمپتی درێژ (>7k) → باسکەندە single-question ەکان پرسیار لە 8k دەبڕن! بیانخە کۆتایی
        try:
            _sys_len = sum(len(str(m.get("content") or "")) for m in full if m.get("role") == "system")
        except Exception:
            _sys_len = 0
        if _sys_len > 7000:
            _sq = {"aff", "yl", "hk", "qb", "ng"}
            _long_ok = [c for c in order if c.get("kind") not in _sq]
            if _long_ok:
                print(f"[API] 📜 system {_sys_len} پیت → single-question دواخرا ({len(order)}→{len(_long_ok)}+sq)", flush=True)
                order = _long_ok + [c for c in order if c.get("kind") in _sq]
        _flt = [c for c in order if time.time() >= _BREAKER.get(c.get("kind"), 0)]
        if _flt:
            order = _flt
        else:
            _seen, _min = set(), []
            for c in order:
                if c.get("kind") not in _seen:
                    _seen.add(c.get("kind"))
                    _min.append(c)
            order = _min[:3]
        for cand in order:
            if time.time() - t_api0 > 100:  # #94U17: دێدلاینی گشتی 100s — slot ئازاد دەبێت
                print(f"[API] ⏱ دێدلاین 100s — وەستان لە {cand.get('id')}", flush=True)
                break
            try:
                kind = cand.get("kind")
                if kind == "em":
                    content = em_chat(full, cand["model_id"])
                elif kind == "aff":
                    content = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint")).chat(q, history=full)
                elif kind == "cbc":
                    content = cbc_chat(full)
                elif kind == "rwd":
                    content = rwd_chat(cand["model_id"], full)
                elif kind == "act":
                    content = act_chat(cand["model_id"], full)
                elif kind == "fla":
                    content = fla_chat(full)
                elif kind == "z02":
                    content = z02_chat(full, cand["model_id"])
                elif kind == "qb":
                    content = qb_chat(full)
                elif kind == "duck":
                    content = duck_chat(cand["model_id"], full)
                elif kind == "ak":
                    content = ak_chat(cand["model_id"], full)
                elif kind == "ng":
                    content = ng_chat(full)
                elif kind == "l7":
                    content = l7_chat(full, cand["model_id"])
                elif kind == "g4f":
                    content = g4f_chat(full, cand["model_id"], timeout=50)  # #94U19
                elif kind == "ct":
                    content = ct_chat(full, cand["model_id"])
                elif kind == "yl":
                    content = yl_chat(full, cand["model_id"])
                elif kind == "hk":
                    content = hk_chat(full, cand["model_id"])
                elif kind == "hf":
                    content = hf_chat(full, cand["model_id"])
                elif kind == "aka":
                    content = aka_chat(full, cand["model_id"])
                elif kind == "hb":
                    content = hb_chat(full, cand["model_id"])
                elif kind == "gk":
                    content = gk_chat(full, cand["model_id"])
                elif kind == "gz":
                    content = gz_chat(full, cand["model_id"])
                elif kind == "pi":
                    content = pi_chat(full, cand["model_id"])
                elif kind == "cb":
                    content = cb_chat(full, cand["model_id"])
                elif kind == "ca":
                    content = ca_chat(full, cand["model_id"])
                elif kind == "ac":
                    content = ac_chat(full, cand["model_id"])
                elif kind == "nv":
                    content = nv_chat(full, cand["model_id"])
                elif kind == "al":
                    content = al_chat(full, cand["model_id"])
                elif kind == "pia":
                    content = pia_chat(full, cand["model_id"])
                elif kind == "cbox":
                    content = cbox_chat(full, cand["model_id"])
                elif kind == "alle":
                    content = alle_chat(full, cand["model_id"])
                elif kind == "aiml":
                    content = aiml_chat(full, cand["model_id"])
                else:
                    content = pol_chat(cand["id"], full)
                if content:
                    _dg = _resp_degenerate(content)
                    if _dg >= 2:
                        print(f"[API] {kind} وەڵامی تێکچوو (degenerate-{_dg}) — fallback", flush=True)
                        threading.Thread(target=_revive_source, args=(kind, "degenerate"), daemon=True).start()
                        if _spare is None:
                            _spare = content
                        content = ""
                        continue
                    if cand is not srv:
                        print(f"[API] fallback → {kind}", flush=True)
                    break
                else:
                    print(f"[API] {kind} بەتاڵ — revive + fallback", flush=True)
                    threading.Thread(target=_revive_source, args=(kind, "empty"), daemon=True).start()
            except Exception as e:
                last_err = e
                _BREAKER[cand.get("kind")] = time.time() + (300 if _is_limit_err(e) else 90)
                _limit_recharge(cand.get("kind"), e)
                print(f"[API] {cand.get('kind')} هەڵە: {str(e)[:90]}", flush=True)
                threading.Thread(target=_revive_source, args=(cand.get("kind"), e), daemon=True).start()
        if not content:
            # ═══ دیلی نەوە (API): مۆدێڵی داواکراو مردووە → نوێترین نەوەی هەمان خێزان ═══
            try:
                up = smart_rebind(API_BRAIN["servers"], srv["id"])
                if up and up != srv["id"]:
                    nsrv = next(x for x in API_BRAIN["servers"] if x["id"] == up)
                    print(f"[API] 🔄 دیلی نەوە: {srv['id']} → {up}", flush=True)
                    k = nsrv.get("kind")
                    nmsgs = full
                    if k == "em":
                        content = em_chat(nmsgs, nsrv["model_id"])
                    elif k == "cbc":
                        content = cbc_chat(nmsgs)
                    elif k == "rwd":
                        content = rwd_chat(nsrv["model_id"], nmsgs)
                    elif k == "act":
                        content = act_chat(nsrv["model_id"], nmsgs)
                    elif k == "fla":
                        content = fla_chat(nmsgs)
                    elif k == "z02":
                        content = z02_chat(nmsgs, nsrv["model_id"])
                    elif k == "qb":
                        content = qb_chat(nmsgs)
                    elif k == "duck":
                        content = duck_chat(nsrv["model_id"], nmsgs)
                    elif k == "ak":
                        content = ak_chat(nsrv["model_id"], nmsgs)
                    elif k == "ng":
                        content = ng_chat(nmsgs)
                    elif k == "l7":
                        content = l7_chat(nmsgs, nsrv["model_id"])
                    elif k == "g4f":
                        content = g4f_chat(nmsgs, nsrv["model_id"])
                    elif k == "ct":
                        content = ct_chat(nmsgs, nsrv["model_id"])
                    elif k == "yl":
                        content = yl_chat(nmsgs, nsrv["model_id"])
                    elif k == "hk":
                        content = hk_chat(nmsgs, nsrv["model_id"])
                    elif k == "hf":
                        content = hf_chat(nmsgs, nsrv["model_id"])
                    elif k == "aka":
                        content = aka_chat(nmsgs, nsrv["model_id"])
                    elif k == "hb":
                        content = hb_chat(nmsgs, nsrv["model_id"])
                    elif k == "gk":
                        content = gk_chat(nmsgs, nsrv["model_id"])
                    elif k == "gz":
                        content = gz_chat(nmsgs, nsrv["model_id"])
                    elif k == "pi":
                        content = pi_chat(nmsgs, nsrv["model_id"])
                    elif k == "cb":
                        content = cb_chat(nmsgs, nsrv["model_id"])
                    elif k == "ca":
                        content = ca_chat(nmsgs, nsrv["model_id"])
                    elif k == "ac":
                        content = ac_chat(nmsgs, nsrv["model_id"])
                    elif k == "nv":
                        content = nv_chat(nmsgs, nsrv["model_id"])
                    elif k == "al":
                        content = al_chat(nmsgs, nsrv["model_id"])
                    elif k == "pia":
                        content = pia_chat(nmsgs, nsrv["model_id"])
                    elif k == "cbox":
                        content = cbox_chat(nmsgs, nsrv["model_id"])
                    elif k == "alle":
                        content = alle_chat(nmsgs, nsrv["model_id"])
                    elif k == "aiml":
                        content = aiml_chat(nmsgs, nsrv["model_id"])
                    else:
                        content = pol_chat(nsrv["id"], nmsgs)
                    if content and not _resp_degenerate(content):
                        print(f"[API] ✅ نەوەی نوێ وەڵامی دا: {up}", flush=True)
                    elif content:
                        print("[API] ⚠️ نەوەی نوێ تێکچوو — فڕێدرا", flush=True)
                        if _spare is None:
                            _spare = content
                        content = ""
            except Exception as e2:
                print(f"[API] دیلی نەوە شکستی هێنا: {str(e2)[:90]}", flush=True)
        if not content and _spare:
            content = _spare  # #94U27: هەموو تێکچوو بوون — لە هەڵە باشترە
            print("[API] ⚠️ هەموو وەڵامەکان تێکچوو بوون — spare گەڕایەوە", flush=True)
        if not content:
            _PERF["fail"] += 1
            return self._send(502, {"error": str(last_err) if last_err else "هیچ سەرچاوەیەک وەڵام نەدایەوە"})
        _PERF["ok"] += 1
        _PERF["lat"].append(time.time() - t_api0)
        if len(_PERF["lat"]) > 200:
            del _PERF["lat"][:100]

        cid = "chatcmpl-" + "".join(random.choices("abcdef0123456789", k=12))
        now = int(time.time())
        if want_stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
            self.send_header("Access-Control-Allow-Headers", "*")
            self.send_header("Access-Control-Expose-Headers", "*")
            self.end_headers()

            def sse(obj):
                self.wfile.write(b"data: " + json.dumps(obj, ensure_ascii=False).encode("utf-8") + b"\n\n")
                self.wfile.flush()

            for i in range(0, len(content), 80):
                sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                     "model": srv["id"],
                     "choices": [{"index": 0, "delta": {"content": content[i:i+80]}, "finish_reason": None}]})
            sse({"id": cid, "object": "chat.completion.chunk", "created": now,
                 "model": srv["id"],
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
            self.wfile.write(b"data: [DONE]\n\n")
        elif openai_style:
            # #94U: usage ە ڕاستەقینە (estimate — tiktoken-ناوی زۆرینە ~4 پیت/توکن)
            _pt = max(1, sum(len(str(m.get("content") or "")) for m in (msgs or [])) // 4)
            _ct = max(1, len(content or "") // 4)  # #94U2: وەڵامی کورت → لانیکەم ١
            self._send(200, {
                "id": cid, "object": "chat.completion", "created": now, "model": srv["id"],
                "choices": [{"index": 0,
                             "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": _pt, "completion_tokens": _ct,
                          "total_tokens": _pt + _ct},
            })
        else:
            self._send(200, {"answer": content, "server": srv["id"]})


_API_CHAT_SEM = threading.Semaphore(24)  # #94U22 LOAD: زۆرترین 24 چاتی API لە هەمان کات + ڕیزبەندی 25s — بەرگەی 20 کەسی هاوکات


def start_api():
    """دەستپێکردنی سێرڤەری API لە تڕێدێکی جیاواز"""
    socketserver.ThreadingTCPServer.allow_reuse_address = True

    class TS(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True

        def process_request(self, request, client_address):
            # #94U15 ANTI-CRASH: تەنها داواکاری چات سنوردارە (health/models هەمیشە دەڕۆن)
            try:
                _peek = request.recv(4096, socket.MSG_PEEK).decode("latin1", "ignore")
                _line = _peek.split("\n", 1)[0]
                _is_chat = _line.startswith("POST") and ("/chat" in _line)
            except Exception:
                _is_chat = True
            if not _is_chat:
                return super().process_request(request, client_address)
            _t = threading.Thread(target=self._chat_thread, args=(request, client_address), daemon=True)
            _t.start()

        def _chat_thread(self, request, client_address):
            if not _API_CHAT_SEM.acquire(timeout=25):  # #94U22: ڕیز دەبن 25s — تەنها لەباردنی ڕاستەقینە 429
                try:
                    _b = b'{"error":"server busy - try again"}'
                    request.sendall(b"HTTP/1.1 429 Too Many Requests\r\nContent-Type: application/json\r\nContent-Length: "
                                    + str(len(_b)).encode() + b"\r\nConnection: close\r\n\r\n" + _b)
                except Exception:
                    pass
                try:
                    self.close_request(request)
                except Exception:
                    pass
                return
            try:
                self.finish_request(request, client_address)
            except Exception:
                try:
                    self.handle_error(request, client_address)
                except Exception:
                    pass
            finally:
                try:
                    self.shutdown_request(request)
                except Exception:
                    pass
                _API_CHAT_SEM.release()

    def _api_serve():
        # #91A2: supervisor — ئەگەر serve_forever بمرێت → 2s → دووبارە
        while True:
            try:
                srv = TS(("0.0.0.0", API_PORT), APIHandler)
                srv.serve_forever(poll_interval=0.5)
            except Exception as e:
                print(f"[API] ⚠️ تڕێدی API وەستا: {e} — دووبارە لە 2s…", flush=True)
                time.sleep(2)

    threading.Thread(target=_api_serve, daemon=True).start()
    print(f"[API] ✅ API کارا کەوت — http://0.0.0.0:{API_PORT} (/v1/chat/completions)", flush=True)


# ════════════════════════════════════════════════════════════
# ٥) تێلەگرام
# ════════════════════════════════════════════════════════════

import os
TOKEN = os.environ.get("BOT_TOKEN") or "8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
API = f"https://api.telegram.org/bot{TOKEN}"

WELCOME = (
    "🤖 <b>أهلا بك! أنا بوت الدكتور التعافي</b>\n\n"
    "أنا معك خطوة بخطوة في رحلة التعافي — اكتب أي شيء وسأسمعك\n\n"
    "🔹 <b>الأوامر:</b>\n"
    "/new — محادثة جديدة\n"
    "/about — معلومات عن البوت"
)

ABOUT = (
    "ℹ️ <b>عن هذا البوت</b>\n\n"
    "بوت الدكتور التعافي — مستشار نفسي وشرعي لمساعدتكم على التعافي من الإدمان\n\n"
    "🛡 <b>الخصوصية</b>\n"
    "كل محادثاتكم محفوظة ومشفرة ولا يمكن لأحد الاطلاع عليها حتى مالك البوت نفسه لا يستطيع رؤيتها\n\n"
    "👤 صُنع بواسطة: <b>يوسف الكردي</b>\n"
    "❤️ لخدمة المدمنين على الإباحة وعادة الاستمناء\n\n"
    "💬 /new — محادثة جديدة"
)

# ژووری گفتوگۆی هەر بەکارهێنەرێک
sessions = {}   # user → {"server": id, "history": [...]}
pending = {}    # user → {"1": server, ...}
BRAIN = {"mode": None, "servers": []}

# دەستنیشانکردنی لێکدانی ناوی مۆدێڵ — هەرگیز ناوی مۆدێڵ ناکرێتەوە
_LEAK_NORM = str.maketrans({"ي": "ی", "ێ": "ی", "ى": "ی", "ك": "ک"})
LEAK_RE = re.compile(r"\b(glm|gpt|claude|gemini|deepseek|qwen|llama|grok|kimi|mistral)[\w.\-]*\b|o4[\s\-]?mini|\bzerotwo\b|zero\s?two|\bquillbot\b|\bduckai\b|duck\s*\.?\s*ai\b|\banakin\b|ئەنەکین|\bnotegpt\b|\bllm7\b|\bg4f\b|\bchattide\b|\byollo\b|\bheck\b|\bhuggingface\b|\bakash\b|\bhotbot\b|\bgadegetkit\b|\bgiz\b|pi\.ai|chatbotapp|chatbotai|askaichat|novaapp|allchatbots|aimlapi|نۆت\s?جی\s?پی\s?تی|(قوین|جی\s*بی\s*تی|جیمینی|دیب\s*سیک|کلود|میسترال|زێرۆ\s?تۆ|کویل|داک)\s*\d*", re.I)


def leaks(s):
    return bool(LEAK_RE.search(str(s).translate(_LEAK_NORM)))
_lock = threading.Lock()
_MSG_SEM = threading.Semaphore(24)  # #94U22 LOAD: زۆرترین 24 هاندڵەری نامەی هاوکات — بەرگەی 20 کەسی هاوکات لە تێلەگرام
_POLL_FAILS = [0]  # #94U13 NEVER-STOP: ژمارەی شکستی لەسەریەکی getUpdates



def tg(method, **params):
    try:
        r = requests.post(f"{API}/{method}", json=params, timeout=(15, 25))
        return r.json()
    except Exception as e:
        print(f"[TG] {method}: {e}", flush=True)
        return {"ok": False, "description": str(e)}


def detect_brain(allow_fallback=True):
    """هەر دوو سێرڤەرەکە تێکەڵ بۆ بۆت — easemate + aifreeforever + pollinations — مۆدێل ئایدی ڕاستەقینە"""
    servers = []
    try:
        servers += em_servers()
    except Exception as e:
        print(f"[BRAIN] em fail: {e}", flush=True)
    try:
        for x in get_aff_servers(hide=False):
            y = dict(x); y["kind"] = "aff"; servers.append(y)
    except Exception:
        pass
    # #91X2: cbc ڕاگیرا — لیمێتی میوانی IP ی فلای پڕە (بەیانیان خۆی دەگەڕێتەوە — کۆدەکە ماوە)
    # try:
    #     servers.append({"id": "cbc-gpt5", "name": "GPT-5", "kind": "cbc"})
    # except Exception:
    #     pass
    try:
        servers += rwd_servers()
    except Exception as e:
        print(f"[BRAIN] rwd fail: {e}", flush=True)
    try:
        servers += act_servers()
    except Exception as e:
        print(f"[BRAIN] act fail: {e}", flush=True)
    try:
        servers += fla_servers()
    except Exception as e:
        print(f"[BRAIN] fla fail: {e}", flush=True)
    try:
        servers += z02_servers()
    except Exception as e:
        print(f"[BRAIN] z02 fail: {e}", flush=True)
    try:
        servers += qb_servers()
    except Exception as e:
        print(f"[BRAIN] qb fail: {e}", flush=True)
    try:
        servers += duck_servers()
    except Exception as e:
        print(f"[BRAIN] duck fail: {e}", flush=True)
    try:
        servers += alle_servers()
    except Exception as e:
        print(f"[BRAIN] alle fail: {e}", flush=True)
    try:
        servers += pia_servers()
    except Exception as e:
        print(f"[BRAIN] pia fail: {e}", flush=True)
    try:
        servers += cbox_servers()
    except Exception as e:
        print(f"[BRAIN] cbox fail: {e}", flush=True)
    try:
        servers += ak_servers()
    except Exception as e:
        print(f"[BRAIN] ak fail: {e}", flush=True)
    try:
        servers += ng_servers()
        sync_l7_models()
        servers += l7_servers()
        servers += _g4f_models()
        sync_ct_models()
        servers += ct_servers()
        sync_yl_models()
        servers += yl_servers()
        sync_hk_models()
        servers += hk_servers()
        sync_hf_models()
        servers += hf_servers()
        sync_akash_models()
        servers += aka_servers()
        sync_hb_models()
        servers += hb_servers()
        sync_gk_models()
        servers += gk_servers()
        sync_giz_models()
        servers += gz_servers()
        sync_pi_models()
        servers += pi_servers()
        sync_cb_models()
        servers += cb_servers()
        sync_ca_models()
        servers += ca_servers()
        sync_ac_models()
        servers += ac_servers()
        sync_nv_models()
        servers += nv_servers()
        sync_al_models()
        servers += al_servers()
        sync_aiml_models()
        servers += aiml_servers()
    except Exception as e:
        print(f"[BRAIN] ng fail: {e}", flush=True)
    # ئۆتۆ-سینک — ئەگەر سەرچاوەیەک مۆدێڵی نوێ زیاد کردبێت یان گۆڕیبێت
    try:
        sync_l7_models()
        sync_ct_models()
        sync_yl_models()
        sync_hk_models()
        sync_hf_models()
        sync_akash_models()
        sync_hb_models()
        sync_gk_models()
        sync_giz_models()
        sync_pi_models()
        sync_cb_models()
        sync_ca_models()
        sync_ac_models()
        sync_nv_models()
        sync_al_models()
        sync_aiml_models()
        sync_duck_models(servers)
    except Exception as e:
        print(f"[SYNC] duck fail: {e}", flush=True)
    try:
        sync_ak_models(servers)
    except Exception as e:
        print(f"[SYNC] ak fail: {e}", flush=True)
    servers = _apply_model_sync(servers)
    # pol هەمیشە لە زنجیرەکەدا بێت — لێگی کۆتایی (نەک تەنها فەڵباکی کۆتایی)
    try:
        pol_list = get_pol_servers()
        if pol_list:
            for x in pol_list:
                y = dict(x); y["kind"] = "pol"; servers.append(y)
    except Exception:
        pass
    if servers:
        return {"mode": "multi", "servers": servers}
    return {"mode": None, "servers": []}


def auto_refresh():
    """هەر ٥ خولەک لیستی سێرڤەرەکان نوێ دەکاتەوە —
    هەر مۆدەڵێکی نوێ لە ماڵپەرەکە خۆکارانە دەچێتە ناو سیستەمەکە"""
    while True:
        time.sleep(300)
        try:
            new = detect_brain(allow_fallback=False)
            if not new["servers"]:
                continue  # ماڵپەرەکە کاتییەکە بەردەست نییە — دۆخی ئێستا بمێنێتەوە
            with _lock:
                changed = (new["mode"] != BRAIN["mode"] or
                           [x["id"] for x in new["servers"]] != [x["id"] for x in BRAIN["servers"]])
                BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
                rebuild_aliases(new["servers"])
                valid = {x["id"] for x in new["servers"]}
                reborn = 0
                for s in sessions.values():
                    if s["server"] not in valid:
                        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر — کلیل + نەخشەی سەرچاوەکان
                        old_key = SRV_KEY_BY_ID.get(s["server"]) or s.get("mkey") or norm_model(s["server"])
                        alts = [x for x in MODEL_SOURCES.get(old_key, []) if x["id"] in valid]
                        if alts:
                            s["server"] = alts[0]["id"]
                            s["mkey"] = old_key
                            continue
                        mk = s.get("mkey") or old_key
                        rebind = next((x["id"] for x in new["servers"] if srv_key(x) == mk or norm_model(x["id"]) == mk), None)
                        if rebind:
                            s["server"] = rebind
                            continue
                        # ٢. دیلی نەوە — مۆدێڵەکە لابرا → نوێترین نەوەی هەمان خێزان
                        up = smart_rebind(new["servers"], s["server"])
                        if up:
                            s["server"] = up
                            s["mkey"] = SRV_KEY_BY_ID.get(up) or norm_model(up)
                            reborn += 1
                if reborn:
                    print(f"[REFRESH] 🔄 {reborn} سێشن بۆ نەوەی نوێتر نەقڵکران", flush=True)
            if changed:
                print(f"[REFRESH] ✨ لیستەکە نوێکرایەوە — {new['mode']} ({len(new['servers'])} سێرڤەر)", flush=True)
        except Exception as e:
            print(f"[REFRESH] هەڵە: {e}", flush=True)


# ─── یەکخستنی مۆدێلە دووبارەکان — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ ───
_MERGE_SUFFIXES = ("-orbio", "-0731", "-0813", "-preview")


def norm_model(mid):
    """کلیلێکی یەکگر بۆ ناسینی هەمان مۆدێڵ لە سەرچاوەی جیاواز"""
    s = str(mid).lower().strip()
    if "/" in s:
        s = s.split("/")[-1]
    s = s.replace("_", "-").replace(".", "-")
    for suf in _MERGE_SUFFIXES:
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s


def srv_key(x):
    """کلیلی سیمانتیکی مۆدێڵ — بۆ گروپکردنی هەمان مۆدێڵ لە سەرچاوەی جیاواز
       model_id ی دەقی (نموونە: gpt-5.6-luna) → کلیلی هاوبەش؛ ژمارەی/نەبوون → id"""
    mid = str(x.get("model_id") or "").strip()
    if not mid or mid.isdigit():
        mid = x["id"]
    return norm_model(mid)


# نەخشەی مۆدێڵ → هەموو سەرچاوەکانی (بۆ فەڵباکی ڕاستەوخۆی هەمان مۆدێڵ)
MODEL_SOURCES = {}
SRV_KEY_BY_ID = {}


def rebuild_aliases(servers):
    """MODEL_SOURCES نوێ دەکاتەوە — مۆدێڵ → لیستی هەموو سەرچاوەکانی بە ڕیز"""
    MODEL_SOURCES.clear()
    SRV_KEY_BY_ID.clear()
    for x in servers:
        k = srv_key(x)
        SRV_KEY_BY_ID[x["id"]] = k
        MODEL_SOURCES.setdefault(k, []).append(x)


def dedupe_servers(servers):
    """یەکێک بۆ هەر مۆدێڵ — یەکەم سەرچاوە سەرەکییە؛ دووەکییەکان لە model_sources دەمێننەوە
       ⚠️ #80: nv/cb (سەرچاوە نەیتیڤەکان) هەمیشە بینراون — dedupe یان ناکوژێنێتەوە"""
    rebuild_aliases(servers)
    seen = set()
    uniq = []
    for x in servers:
        k = srv_key(x)
        if x.get("kind") in ("nv", "cb"):
            k = f"{k}|{x.get('id')}"
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    return uniq


# ════════════════════════════════════════════════════════════
# ٢.٨) نەوەکان — دەزانی «نوێترین» ی هەر خێزانێک کامەیە
#      بۆ دیل ی خۆکاری: مۆدێڵی نامۆ → نوێترین نەوەی هەمان خێزان
# ════════════════════════════════════════════════════════════

import re as _re

# خشتەی نەوە — بەرزتر = نوێتر (خێزان → لیستی دوایینی بەشەکانی ژمارە)
_GEN_VERSIONS = {
    "gemini": [("3.7", [3, 7]), ("3.1", [3, 1]), ("3", [3]), ("2.5", [2, 5]), ("2", [2]), ("1.5", [1, 5])],
    "claude": [("5", [5]), ("4.8", [4, 8]), ("4.5", [4, 5]), ("4.1", [4, 1]), ("4", [4]), ("3.7", [3, 7]), ("3.5", [3, 5])],
    "gpt": [("6", [6]), ("5.6", [5, 6]), ("5.5", [5, 5]), ("5.4", [5, 4]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.1", [4, 1]), ("4o", [4]), ("4", [4])],
    "grok": [("4.5", [4, 5]), ("4.3", [4, 3]), ("4.2", [4, 2]), ("4", [4]), ("3", [3])],
    "deepseek": [("v4.1", [4, 1]), ("v4", [4]), ("v3.2", [3, 2]), ("r1", [1]), ("v3", [3])],
    "qwen": [("3.8", [3, 8]), ("3.7", [3, 7]), ("3.6", [3, 6]), ("3.5", [3, 5]), ("3", [3]), ("2.5", [2, 5])],
    "glm": [("5.3", [5, 3]), ("5.2", [5, 2]), ("5.1", [5, 1]), ("5", [5]), ("4.7", [4, 7]), ("4.5", [4, 5])],
    "kimi": [("k3", [3]), ("k2.6", [2, 6]), ("k2.5", [2, 5]), ("k2", [2])],
    "llama": [("4", [4]), ("3.3", [3, 3]), ("3.2", [3, 2]), ("3.1", [3, 1]), ("3", [3])],
    "nova": [("2", [2]), ("1", [1])],
    "phi": [("4", [4]), ("3", [3])],
    "hy3": [("4", [4]), ("3", [3])],
    "gemma": [("4", [4]), ("3", [3]), ("2", [2])],
}


def _gen_key(mid):
    """(خێزان، ژمارەی نەوە) — بۆ ڕیزکردن. بۆ نموونە gemini-3.8 → ('gemini', 3.8)"""
    s = str(mid).lower()
    fam = _model_family(s)
    ver = None
    if fam in _GEN_VERSIONS:
        nums = _re.findall(r"(\d+(?:\.\d+)?)", s)
        if nums:
            try:
                ver = float(nums[0])
            except ValueError:
                ver = None
    return (fam, ver if ver is not None else 0.0)


def _same_gen(a, b):
    """ئایا ئەم دوو مۆدێڵە هەمان نەوەن؟ (خێزان + ژمارەی سەرەکی یەکسان)"""
    fa, va = _gen_key(a)
    fb, vb = _gen_key(b)
    if fa != fb:
        return False
    if va == vb:
        return True
    # 3 و 3.0 و 3.8 → بەراوردی ژمارەی سەرەکی
    return int(va) == int(vb)


def _newest_in_family(servers, fam, exclude_id=None):
    """نوێترین مۆدێڵی زیندووی خێزانێک (کار دەکات + ئێستا لە لیستەکەدا هەیە)"""
    best, best_v = None, -1.0
    for x in servers:
        if exclude_id and x["id"] == exclude_id:
            continue
        f, v = _gen_key(x["id"])
        if f == fam and v > best_v:
            best, best_v = x, v
    return best


def _gen_upgrade_candidates(servers, dead_id):
    """کاندیدەکانی دیل بۆ مۆدێڵێکی مردوو: هەمان نەوە یان نوێتر، لە هەمان خێزان،
       ڕیزکراو بە نوێترین. هەرگیز مۆدێڵی کۆنتر نادات."""
    fam, dead_v = _gen_key(dead_id)
    cands = []
    for x in servers:
        f, v = _gen_key(x["id"])
        if f == fam and v >= dead_v:
            if x["id"] != dead_id and x not in cands:
                cands.append(x)
    cands.sort(key=lambda x: _gen_key(x["id"])[1], reverse=True)
    if not cands:
        nx = _newest_in_family(servers, fam)
        if nx:
            cands.append(nx)
    return cands


def smart_rebind(servers, dead_id):
    """دیلی زیرەک: مۆدێڵێکی نامۆ → نوێترین هەمان نەوە/نوێتر لە هەمان خێزان.
       ئەگەر هیچ نەبوو → None (پاشان فەڵباکی ئاسایی)."""
    if not dead_id:
        return None
    for c in _gen_upgrade_candidates(servers, dead_id):
        return c["id"]
    return None


def get_session(user_id):
    with _lock:
        s = sessions.get(user_id)
        if s is None:
            default = BRAIN["servers"][0]["id"] if BRAIN["servers"] else "openai"
            dflt = next((x for x in BRAIN["servers"] if x["id"] == default), None)
            s = {"server": default, "history": [], "mkey": (srv_key(dflt) if dflt else (norm_model(default) if default else None))}
            sessions[user_id] = s
        # #88: هەڵبژاردنی ئەدمین بۆ هەموو بەکارهێنەران جێبەجێ دەکرێت
        if GLOBAL_MODEL.get("server"):
            s["server"] = GLOBAL_MODEL["server"]
            s["mkey"] = GLOBAL_MODEL.get("mkey") or s.get("mkey")
        elif GLOBAL_MODEL.get("mkey"):
            # #91G: سەرچاوە گۆڕاوە — هەمان مۆدێڵ لە هەر سەرچاوەیەکی زیندوو
            _mk = GLOBAL_MODEL["mkey"]
            _alt = next((x for x in BRAIN["servers"] if srv_key(x) == _mk), None)
            if _alt:
                s["server"] = _alt["id"]
                s["mkey"] = _mk
        s["user_id"] = user_id
        return s


_LIMIT_RECHARGE_T = {}


def _is_limit_err(err):
    """#91: ئایا هەڵەکە لیمیتە؟ (402/429/credit/quota/limit/rate...)"""
    s = str(err).lower()
    return any(x in s for x in ("402", "429", "credit", "quota", "limit", "depleted", "exceed", "rate", "no free", "usage cap", "monthly"))


_REVIVE_T = {}  # #94U19: kind → دوایین کاتی revive (cooldown 180s)
_REVIVE_SEM = threading.Semaphore(3)  # #94U19: زۆرترین ٣ revive لە هەمان کات


def _revive_source(kind, err=None):
    """#94U19 UNIVERSAL-REVIVE: هەر سەرچاوەیەک داخرا یەکسەر زیندووی بکەرەوە —
       بڕێکەر + حەوز/ساینئەپ + جلسە + ڕیسینک + پرۆکسی — cooldown + async-سەیف"""
    if not kind:
        return
    now = time.time()
    if now - _REVIVE_T.get(kind, 0) < 180:
        return
    _REVIVE_T[kind] = now
    if not _REVIVE_SEM.acquire(blocking=False):
        return
    try:
        steps = []
        low = str(err or "").lower()
        if kind == "em" and any(w in low for w in ("today", "daily", "free tokens", "monthly")):
            _BREAKER[kind] = now + 3 * 3600
            steps.append("breaker-3h")
        else:
            _BREAKER.pop(kind, None)
            steps.append("breaker-clear")
        try:
            if kind in ("ca", "cb", "nv"):
                _pool_reap()
                {"ca": _ca_signup_new, "cb": _cb_signup_new, "nv": _nv_signup_new}[kind](force=True)
                steps.append("pool+signup")
            elif kind == "ac":
                _ac_signup_new()
                steps.append("signup")
            elif kind == "cbox":
                _cbox_new_account()
                steps.append("account")
            elif kind == "pia":
                _pia_signup_new()
                steps.append("signup")
            elif kind == "g4f":
                threading.Thread(target=_g4f_ensure_credits, args=(12, 3), daemon=True).start()
                steps.append("credits")
        except Exception as e:
            steps.append(f"pool-{str(e)[:24]}")
        try:
            if kind == "pi":
                PI_STATE["s"] = None
                steps.append("session")
            elif kind == "cbc":
                _CBC_STATE["t"] = 0  # #94U24: csrf/cookies ی نوێ لە داوای داهاتوو
                steps.append("session")
        except Exception:
            pass
        try:
            f = globals().get(f"sync_{kind}_models")
            if f:
                try:
                    f(force=True)
                except TypeError:
                    f([])
                steps.append("resync")
        except Exception as e:
            steps.append(f"resync-{str(e)[:24]}")
        try:
            _proxy_get(1)
            steps.append("proxy")
        except Exception:
            pass
        print(f"[REVIVE] {kind}: {' + '.join(steps)}", flush=True)
    finally:
        _REVIVE_SEM.release()


def _limit_recharge(kind, err):
    """#91: لیمیت تەواو بوو → یەکسان پڕکردنەوەی لیمیت:
       حەوز=ئەکاونتی نوێ | g4f=کرێدی نوێ | ac=سایناپ نوێ | ئەوانی تر=تۆکێن+پرۆکسی نوێ"""
    if not kind or not _is_limit_err(err):
        return
    now = time.time()
    if now - _LIMIT_RECHARGE_T.get(kind, 0) < 240:
        return
    _LIMIT_RECHARGE_T[kind] = now
    try:
        if kind in ("ca", "cb", "nv"):
            # #91P2: پاڵنان بە جیاتی سڕینەوە — ئەکاونت لە دەست ناچێت، تەنها دەگۆڕدرێت
            _pool_reap()
            # #94U23: ئەکاونتی نوێی یەکسەر (پێش داواکاری داهاتوو — بودجە لەژێر لۆک)
            threading.Thread(target=lambda k=kind: {"ca": _ca_signup_new, "cb": _cb_signup_new, "nv": _nv_signup_new}[k](force=True), daemon=True).start()
            print(f"[LIMIT-RECHARGE] {kind}: ئەکاونتی limit پاڵدرا کۆتایی + ئەکاونتی نوێ دروست دەکرێت...", flush=True)
        elif kind == "g4f":
            threading.Thread(target=_g4f_ensure_credits, args=(12, 3), daemon=True).start()
            print(f"[LIMIT-RECHARGE] g4f: دروستکردنی کرێدی نوێ...", flush=True)
        elif kind == "ac":
            threading.Thread(target=_ac_signup_new, daemon=True).start()
            print(f"[LIMIT-RECHARGE] ac: ئەکاونتی نوێ دروست دەکرێت...", flush=True)
        elif kind == "cbox":
            # #94CX: ئەکاونتی نوێ = ١ داواکاری — یەکسەر:
            threading.Thread(target=_cbox_new_account, daemon=True).start()
            print(f"[LIMIT-RECHARGE] cbox: ئەکاونتی نوێ (١ داواکاری)...", flush=True)
        elif kind == "pia":
            threading.Thread(target=_pia_signup_new, daemon=True).start()
            print(f"[LIMIT-RECHARGE] pia: ئەکاونتی نوێ...", flush=True)
        else:
            def _rs():
                try:
                    f = globals().get(f"sync_{kind}_models")
                    if f:
                        try:
                            f(force=True)
                        except TypeError:
                            f([])
                except Exception:
                    pass
                try:
                    _proxy_get(1)
                except Exception:
                    pass
            threading.Thread(target=_rs, daemon=True).start()
            print(f"[LIMIT-RECHARGE] {kind}: تۆکێنی نوێ + پرۆکسی نوێ...", flush=True)
    except Exception as e:
        print(f"[LIMIT-RECHARGE] {kind}: {str(e)[:50]}", flush=True)


def ask(session, question):
    """پرسیار — مۆدێڵی هەڵبژارد + زنجیرەی fallback: easemate → aifreeforever → pollinations"""
    history = session["history"]
    sys_msg = {"role": "system", "content": SYSTEM_PROMPT}
    srv = next((x for x in BRAIN["servers"] if x["id"] == session["server"]), None)
    if not srv and BRAIN["servers"]:
        # ١. هەمان مۆدێڵ لە سەرچاوەیەکی تر — بە کلیلی سیمانتیکی مۆدێڵ
        mk = session.get("mkey") or SRV_KEY_BY_ID.get(session.get("server") or "") or norm_model(session.get("server") or "")
        if mk:
            srv = next((x for x in BRAIN["servers"] if srv_key(x) == mk or norm_model(x["id"]) == mk), None)
            if srv:
                session["server"] = srv["id"]
    if not srv and BRAIN["servers"]:
        # ٢. هاوشێوەترین بەپێی خێزان — بەڵام هەڵبژاردەکە ناگۆڕدرێت
        fam = _model_family(session.get("server") or "")
        srv = pick_in_kind(BRAIN["servers"], fam, session.get("server") or "gpt") if fam else None
        if not srv:
            srv = BRAIN["servers"][0]
    order = []
    if srv:
        order.append(srv)
        # ⚡ فەڵباکی خێرا: هەمان مۆدێڵ لە سەرچاوەی تر — پێش هەر شتێکی تر
        for alt in MODEL_SOURCES.get(srv_key(srv), []):
            if alt["id"] != srv["id"] and alt not in order:
                order.append(alt)
    for kind in ("em", "aff", "rwd", "l7", "g4f", "pol"):
        if srv and srv.get("kind") == kind:
            continue
        cand = pick_in_kind(BRAIN["servers"], kind, srv["id"] if srv else "gpt")
        if cand and cand not in order:
            order.append(cand)
    last = None
    _flt = [c for c in order if time.time() >= _BREAKER.get(c.get("kind"), 0)]
    if _flt:
        order = _flt
    # #91F3: ئەگەر هەموو breaker بوون — تەنها یەکەم ی هەر سەرچاوەیەکی جیاواز (نەک هەموو دووبارە)
    else:
        _seen, _min = set(), []
        for c in order:
            if c.get("kind") not in _seen:
                _seen.add(c.get("kind"))
                _min.append(c)
        order = _min[:3]
    _ask_t0 = time.time()  # #94U17
    for cand in order:
        if time.time() - _ask_t0 > 110:  # #94U17: دێدلاینی گشتی — نەهێشتنی گیربوون
            print("[ASK] ⏱ دێدلاین 110s", flush=True)
            break
        try:
            k = cand.get("kind")
            if k == "em":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return em_chat(msgs, cand["model_id"]), "em"
            if k == "aff":
                bot = AIFreeChat(model=cand["id"], endpoint=cand.get("endpoint"))
                a = bot.chat(question, history=[sys_msg] + history)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aff"
            if k == "cbc":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                return cbc_chat(msgs), "cbc"
            if k == "rwd":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = rwd_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "rwd"
            if k == "act":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = act_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "act"
            if k == "fla":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = fla_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "fla"
            if k == "z02":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = z02_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "z02"
            if k == "qb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = qb_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "qb"
            if k == "duck":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = duck_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "duck"
            if k == "ak":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ak_chat(cand["model_id"], msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ak"
            if k == "ng":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ng_chat(msgs)
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ng"
            if k == "l7":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = l7_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "l7"
            if k == "g4f":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = g4f_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "g4f"
            if k == "ct":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ct_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ct"
            if k == "yl":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = yl_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "yl"
            if k == "hk":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hk_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hk"
            if k == "hf":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hf_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hf"
            if k == "aka":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = aka_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aka"
            if k == "hb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = hb_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "hb"
            if k == "gk":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = gk_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "gk"
            if k == "gz":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = gz_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "gz"
            if k == "pi":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = pi_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "pi"
            if k == "cb":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = cb_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "cb"
            if k == "ca":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ca_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ca"
            if k == "ac":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = ac_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "ac"
            if k == "nv":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = nv_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "nv"
            if k == "al":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = al_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "al"
            if k == "pia":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = pia_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "pia"
            if k == "cbox":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = cbox_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "cbox"
            if k == "alle":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = alle_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "alle"
            if k == "aiml":
                msgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                a = aiml_chat(msgs, cand["model_id"])
                if leaks(a):
                    raise EMError("identity leak")
                return a, "aiml"
            msgs = [sys_msg] + list(history[-20:]) + [{"role": "user", "content": question}]
            return pol_chat(cand["id"], msgs), "pol"
        except Exception as e:
            last = e
            _BREAKER[cand.get("kind")] = time.time() + (300 if _is_limit_err(e) else 90)
            _limit_recharge(cand.get("kind"), e)
            print(f"[BRAIN] {cand.get('kind', '?')} ({cand.get('id', '?')}) هەڵە: {str(e)[:80]}", flush=True)
            threading.Thread(target=_revive_source, args=(cand.get("kind"), e), daemon=True).start()
    # ═══ دیلی نەوە: هەموو زنجیرەکە بۆ ئەم مۆدێڵە مردووە → نوێترین نەوە بپشکنە ═══
    if BRAIN["servers"] and question:
        try:
            dead_id = session.get("server") or ""
            up = smart_rebind(BRAIN["servers"], dead_id)
            if up and up != dead_id:
                nsrv = next(x for x in BRAIN["servers"] if x["id"] == up)
                print(f"[BRAIN] 🔄 دیلی نەوە: {dead_id} → {up}", flush=True)
                k = nsrv.get("kind")
                nmsgs = [sys_msg] + history[-20:] + [{"role": "user", "content": question}]
                if k == "em":
                    return em_chat(nmsgs, nsrv["model_id"]), "em"
                if k == "cbc":
                    return cbc_chat(nmsgs), "cbc"
                if k == "rwd":
                    a = rwd_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "rwd"
                if k == "act":
                    a = act_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "act"
                if k == "fla":
                    a = fla_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "fla"
                if k == "z02":
                    a = z02_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "z02"
                if k == "qb":
                    a = qb_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "qb"
                if k == "duck":
                    a = duck_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "duck"
                if k == "ak":
                    a = ak_chat(nsrv["model_id"], nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ak"
                if k == "ng":
                    a = ng_chat(nmsgs)
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ng"
                if k == "l7":
                    a = l7_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "l7"
                if k == "g4f":
                    a = g4f_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "g4f"
                if k == "ct":
                    a = ct_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ct"
                if k == "yl":
                    a = yl_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "yl"
                if k == "hk":
                    a = hk_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hk"
                if k == "hf":
                    a = hf_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hf"
                if k == "aka":
                    a = aka_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "aka"
                if k == "hb":
                    a = hb_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "hb"
                if k == "gk":
                    a = gk_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "gk"
                if k == "gz":
                    a = gz_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "gz"
                if k == "pi":
                    a = pi_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "pi"
                if k == "cb":
                    a = cb_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "cb"
                if k == "ca":
                    a = ca_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ca"
                if k == "ac":
                    a = ac_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "ac"
                if k == "nv":
                    a = nv_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "nv"
                if k == "al":
                    a = al_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "al"
                if k == "pia":
                    a = pia_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "pia"
                if k == "cbox":
                    a = cbox_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "cbox"
                if k == "alle":
                    a = alle_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "alle"
                if k == "aiml":
                    a = aiml_chat(nmsgs, nsrv["model_id"])
                    if leaks(a):
                        raise EMError("identity leak")
                    return a, "aiml"
                return pol_chat(nsrv["id"], nmsgs), "pol"
        except Exception as e2:
            print(f"[BRAIN] دیلی نەوە شکستی هێنا: {str(e2)[:80]}", flush=True)
            last = e2
    raise last or RuntimeError("هیچ مێشکێک بەردەست نییە")


def split_msg(t, n=3900):
    """#91A10: بڕین لە دێڕی نوێ — tag ی HTML نابڕدرێت (TG parse دەمێنێت ساغ)"""
    out = []
    while t:
        if len(t) <= n:
            out.append(t)
            break
        cut = t.rfind("\n", n // 2, n)
        if cut < 0:
            cut = n
        out.append(t[:cut])
        t = t[cut:].lstrip("\n")
    return out


def keep_typing(chat_id, stop):
    while not stop.is_set():
        tg("sendChatAction", chat_id=chat_id, action="typing")
        stop.wait(4.0)


def _sanitize_tg_html(html_text):
    """ڕێگری لە 400 Bad Request — لابردنی تاگە نادروستەکان و ڕێگری لە <word="""
    if not html_text:
        return ""
    allowed = r'/?(?:b|i|u|s|strike|del|strong|em|code|pre|a\b[^>]*|tg-spoiler|blockquote)'
    return re.sub(rf'<(?!(?:{allowed})>)', '&lt;', html_text)


def reply(chat_id, text):
    safe_text = _sanitize_tg_html(text)
    r = tg("sendMessage", chat_id=chat_id, text=safe_text, parse_mode="HTML",
           disable_web_page_preview=True)
    if r.get("ok"):
        return
    # فەڵباکی زیرەک: یەکەم هەوڵ — بەشە-بەشە بە HTML (کێشە = درێژی)
    ok2 = True
    for part in split_msg(safe_text):
        r2 = tg("sendMessage", chat_id=chat_id, text=part, parse_mode="HTML",
                disable_web_page_preview=True)
        if not r2.get("ok"):
            ok2 = False
            break
    if ok2:
        return
    # دووەم: بەبێ HTML — وەک دەقی سادە
    for part in split_msg(text):
        plain = re.sub(r'<[^>]+>', '', part)
        tg("sendMessage", chat_id=chat_id, text=plain)


def handle_message(msg):
    chat_id = msg["chat"]["id"]
    user_id = msg.get("from", {}).get("id", chat_id)
    text = (msg.get("text") or "").strip()
    if not text:
        return

    print(f"[MSG] user={user_id}: {text[:60]}", flush=True)

    if text.startswith("/start"):
        reply(chat_id, WELCOME)
        return
    # ═══ #89: فەرمانەکانی خۆبەڕێوەبەری — تەنها ئەدمین ═══
    if text.startswith("/status"):
        if user_id != ADMIN_TG:
            return
        # بار گشتی: حەوزەکان + SELF-HEAL + مۆدێڵەکان
        try:
            def _n(f):
                try:
                    d = _json_load_safe(os.path.join(DATA_DIR, f)) or {}
                    if isinstance(d, dict):
                        return len(d.get("accounts", []))
                    return len(d)
                except Exception:
                    return 0
            def _a(f):
                # #94U38: ژمارەی زیندوو (وەک /health) — نەک کۆی گشتی
                try:
                    d = _json_load_safe(os.path.join(DATA_DIR, f)) or {}
                    accs = d.get("accounts", []) or []
                    lim = d.get("limits") or {}
                    exh = d.get("exhausted") or {}
                    td = _lim_today()
                    def _ok(a):
                        e = a.get("email") or "?"
                        if td in (lim.get(e) or {}).values():
                            return False
                        v = exh.get(e)
                        if v in (None, 0, "", False):
                            return True
                        try:
                            return float(v) <= time.time()
                        except Exception:
                            return str(v)[:10] != td
                    return sum(1 for a in accs if _ok(a))
                except Exception:
                    return 0
            ca, cb, nv, ac = _a("ca_accounts.json"), _a("cb_accounts.json"), _a("nv_accounts.json"), _a("ac_accounts.json")
            nmodels = len(dedupe_servers(BRAIN["servers"])) if BRAIN["servers"] else 0
            st = _HEAL_STATE.get("status", {})
            lines = [f"📊 <b>ڕاپۆرتی سیستەم</b>\n",
                     f"🤖 مۆدێڵ لە مێنیو: <b>{nmodels}</b>\n",
                     f"👥 حەوز (زیندوو/ئامانج): CA {ca}/1000 · CB {cb}/1000 · NV {nv}/1000 · AC {ac}/30\n",  # #94U38
                     "🩺 دوا پشکنینی خۆبەڕێوەبەری:"]
            if st:
                for k in sorted(st):
                    v = st[k]
                    age = int(time.time() - v.get("t", 0))
                    lines.append(f"  • {k}: {'✅' if v.get('ok') else '❌ ' + str(v.get('err', ''))[:40]} ({age}s پێش)")
            else:
                lines.append("  • هێشتا پشکنین نەکراوە — <code>/heal</code> بنووسە")
            reply(chat_id, "\n".join(lines))
        except Exception as e:
            reply(chat_id, f"⚠️ {str(e)[:80]}")
        return

    if text.startswith("/heal"):
        if user_id != ADMIN_TG:
            return
        reply(chat_id, "🩺 <b>پشکنینی تەواو دەست پێدەکات… (چەند چرکەیەک)</b>")
        def _heal_work():
            try:
                self_heal_once()
                st = _HEAL_STATE.get("status", {})
                lines = ["🩺 <b>ئەنجامی پشکنین + چاککردنەوە:</b>\n"]
                for k in sorted(st):
                    v = st[k]
                    lines.append(f"  • {k}: {'✅ زیندووە' if v.get('ok') else '❌ ' + str(v.get('err', ''))[:50]}")
                lines.append("\n✅ شکاوەکان بۆ sync ی توند نێردران — لە خولی داهاتوو دووبارە دەپشکنرێن")
                reply(chat_id, "\n".join(lines))
            except Exception as e:
                reply(chat_id, f"⚠️ {str(e)[:80]}")
        threading.Thread(target=_heal_work, daemon=True).start()
        return

    if text.startswith("/stats"):
        if user_id != ADMIN_TG:
            return
        lat = _PERF["lat"]
        avg = (sum(lat) / len(lat)) if lat else 0
        br = {k: int(v - time.time()) for k, v in _BREAKER.items() if v > time.time()}
        up = int(time.time() - BOOT_T)
        _uptxt = f"{up // 3600} کاتژمێر و {(up % 3600) // 60} خولەک" if up >= 3600 else f"{up // 60} خولەک"
        _hk = _hk_stats()
        reply(chat_id, f"📈 <b>ئامارەکانی سیستەمی خارق</b>\n"
                      f"🕵 هاکەر: {_hk['wins']}/{_hk['tries']} سەرکەوتوو | ڕێگاکان: {', '.join(f'{k}={v}' for k, v in _hk['routes'].items()) or '—'}\n"
                      f"⏱ کاراک: {_uptxt}\n"
                      f"⚡ داواکاری: {_PERF['req']} — ✅ {_PERF['ok']} / ❌ {_PERF['fail']}\n"
                      f"⏳ تێکڕای وەڵام: {avg:.1f} چرکە\n"
                      f"🧊 بریکەر (سەرچاوەی پشوو): {', '.join(f'{k}({v}s)' for k, v in br.items()) or '—'}\n"
                      f"💾 کاشی وەڵام: {len(_ANS_CACHE)} | بەکارهێنەری چالاک: {len(_USER_Q)}")
        return
    if text.startswith("/test "):
        if user_id != ADMIN_TG:
            return
        ref = text[6:].strip()
        if not ref:
            reply(chat_id, "✍️ نموونە: <code>/test openai/gpt-5.5</code>")
            return
        threading.Thread(target=_admin_test_model, args=(chat_id, ref), daemon=True).start()
        return
    if text.startswith("/crack"):
        # #94U2: HACK-TOOLKIT — ئەدمین-تەنها
        if user_id != ADMIN_TG:
            return
        arg = text[6:].strip()
        if not arg:
            reply(chat_id, "🛠 <b>HACK-TOOLKIT (#94U3)</b>\n"
                           "<code>/crack scan &lt;url&gt;</code> — سکان-کردنی سایت+JS بەندڵ\n"
                           "<code>/crack eps &lt;url&gt;</code> — تەنها endpoint ەکان\n"
                           "<code>/crack get &lt;url&gt;</code> — گەڕانەوەی کۆد (CF-impersonate)\n"
                           "<code>/crack replay &lt;url&gt; | &lt;json-body&gt;</code> — دووبارەکردنەوەی POST/SSE\n"
                           "<code>/crack sse &lt;url&gt; | &lt;json-body&gt;</code> — SSE-ستریم\n"
                           "<code>/crack auth &lt;url&gt;</code> — دۆزینەوەی ڕەوتی signup/login/refresh\n"
                           "<code>/crack forge &lt;url&gt; | &lt;json&gt;</code> — داواکاری دەستکرد\n"
                           "<code>/crack schema &lt;url&gt;</code> — ئۆراکڵی ProtoJSON (دەرهێنانی سکێم بە int-probe)\n"
                           "<code>/crack forge-device &lt;base&gt;</code> — دۆزینەوەی ئۆت + حەوزی ئایدێنتیتی دەستکرد\n"
                           "<code>/crack grpc &lt;dex/apk|url&gt; | [gateway]</code> — هەڵمژینی MethodDescriptor + پرۆبی POST")
            return
        threading.Thread(target=_crack_cmd, args=(chat_id, arg), daemon=True).start()
        return
    if text.startswith("/backup"):
        if user_id != ADMIN_TG:
            return
        reply(chat_id, "📦 <b>ئامادەکردنی باکئەپی حەوزەکان…</b>")
        threading.Thread(target=_perform_backup, args=(chat_id, True), daemon=True).start()
        return
    if text.startswith("/about"):
        reply(chat_id, ABOUT)
        return
    if text.startswith("/new"):
        get_session(user_id)["history"].clear()
        reply(chat_id, "✨ <b>بدأنا محادثة جديدة</b>\nاكتب رسالتك وسنبدأ خطوة بخطوة")
        return

    if text.startswith("/server"):
        # #88: تەنها ئەدمین — بۆ بەکارهێنەری تر بێدەنگ پشتگوێ دەخرێت
        if user_id != ADMIN_TG:
            return
        reply(chat_id, "🔄 <b>يتم جلب أحدث قائمة…</b>")
        new = detect_brain()
        if not new["servers"]:
            reply(chat_id, "⚠️ <b>تعذر جلب القائمة.</b> حاول بعد قليل.")
            return
        with _lock:
            BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        servers = new["servers"]
        s = get_session(user_id)
        if s["server"] not in [x["id"] for x in servers]:
            s["server"] = servers[0]["id"]
        # مۆدێلە دووبارەکان یەک دەخرێن — هەمان مۆدێڵ لە چەند سەرچاوە = یەک دەنگ
        # #91M: openai/gpt-5.5 هەمیشە یەکەم — داواکاری ئەدمین
        try:
            _pi = next(i for i, x in enumerate(servers) if x.get("id") == "openai/gpt-5.5")
            if _pi > 0:
                servers = [servers.pop(_pi)] + servers
        except StopIteration:
            pass
        uniq = dedupe_servers(servers)
        with _lock:
            pending[user_id] = {str(i): {"id": x["id"], "key": srv_key(x)} for i, x in enumerate(uniq, 1)}
        # بەشە-بەشە بنێرە (سنووری تێلەگرام ٤٠٩٦ پیت) — HTML لە هەر بەشێک ساغ دەمێنێتەوە
        parts_out = [f"🤖 <b>قائمة الموديلات</b> — {len(uniq)} موديل (المكرر بين المصادر مدموج):\n\n"]
        cur = parts_out[0]
        for i, x in enumerate(uniq, 1):
            mark = " ✅" if x["id"] == (GLOBAL_MODEL.get("server") or s["server"]) else ""
            ln = f"{i}. <code>{x['id']}</code>{mark}\n"
            if len(cur) + len(ln) > 3700:
                parts_out.append(cur)
                cur = ""
            cur += ln
        cur += "\n✍️ اكتب رقم الموديل فقط للتبديل مثال: <code>5</code>"
        parts_out.append(cur)
        for p in parts_out:
            if p.strip():
                reply(chat_id, p)
        return

    # هەڵبژاردنی سێرڤەر بە ژمارە — #88: تەنها ئەدمین + هەڵبژاردنی ئەدمین = بۆ هەموو بەکارهێنەران
    s = get_session(user_id)
    if text.isdigit():
        if user_id != ADMIN_TG:
            return  # بێدەنگ — بۆ بەکارهێنەری تر ژمارە وەک نامەی ئاسایی نادرێتەوە
        p = pending.get(user_id)
        if not p:
            reply(chat_id, "🤖 اكتب <code>/server</code> أولا لعرض قائمة الموديلات.")
            return
        if str(int(text)) not in p:
            reply(chat_id, f"⚠️ اكتب رقما بين <code>1</code> و <code>{len(p)}</code>.")
            return
        srv = p[str(int(text))]
        with _lock:
            GLOBAL_MODEL["server"] = srv["id"]
            GLOBAL_MODEL["mkey"] = srv["key"]
        try:  # #91G: هەڵبژاردەی ئەدمین هەمیشەییە — دیپلۆی نایگەڕێنێتەوە
            _json_save(os.path.join(DATA_DIR, "global_model.json"), dict(GLOBAL_MODEL))
        except Exception:
            pass
        s["server"] = srv["id"]
        s["mkey"] = srv["key"]
        s["history"].clear()
        reply(chat_id, f"✅ تم التبديل إلى الموديل <code>{srv['id']}</code> — مطبق على جميع المستخدمين")
        return

    # پرسیاری ئاسایی
    if not BRAIN["servers"]:
        new = detect_brain()
        BRAIN["mode"], BRAIN["servers"] = new["mode"], new["servers"]
        rebuild_aliases(new["servers"])
        if not BRAIN["servers"]:
            reply(chat_id, "⚠️ لا يوجد مصدر متاح الآن — حاول بعد قليل.")
            return
        s["server"] = BRAIN["servers"][0]["id"]

    stop = threading.Event()
    threading.Thread(target=keep_typing, args=(chat_id, stop), daemon=True).start()

    result = {}

    def work():
        try:
            result["answer"] = ask(s, text)
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=work, daemon=True)
    t.start()
    t.join(timeout=150)

    try:
        if "error" in result:
            answer = f"⚠️ <b>حدث خطأ:</b> {result['error']}\nحاول بعد قليل."
        elif "answer" not in result:
            answer = "⏳ <b>تأخر الرد كثيرا.</b> أعد الإرسال من فضلك."
        else:
            answer, mode = result["answer"]
            if answer:
                # #94U7: پاککردنەوەی خاڵبەندی (، . !) لە وەڵامی بۆتی دکتۆر التعافي بەپێی یاساکان
                clean_ans = re.sub(r'[,،!]', '', str(answer))
                clean_ans = re.sub(r'(?<!\d)\.(?!\d)', '', clean_ans)
                answer = clean_ans
                s["history"].append({"role": "user", "content": text})
                s["history"].append({"role": "assistant", "content": answer})
                s["history"] = s["history"][-20:]
            else:
                answer = "⚠️ لم يصل رد — حاول مرة أخرى."
    finally:
        stop.set()

    print(f"[ANS] user={user_id}: {len(answer)} chars", flush=True)
    for part in split_msg(answer):
        reply(chat_id, part)


def setup_commands():
    """فەرمانەکانی مێنیو — لەگەڵ دووبارەهەوڵ (تا هەرگیز ون نەبن)"""
    cmds = [
        {"command": "start", "description": "بدء المحادثة مع البوت"},
        {"command": "new", "description": "محادثة جديدة"},
        {"command": "about", "description": "معلومات عن البوت"},
    ]
    # فەرمانەکان لە هەموو سکۆپەکاندا دانراو — تا فەرمانی کۆنی هیچ سیستەمێکی تر ون نەمێنێت
    scopes = [
        {"type": "default"},
        {"type": "all_private_chats"},
        {"type": "all_group_chats"},
    ]
    for attempt in range(3):
        ok = True
        for sc in scopes:
            r = tg("setMyCommands", commands=cmds, scope=sc)
            if not r.get("ok"):
                ok = False
                print(f"[CMDS] {sc.get('type')} شکستی هێنا", flush=True)
        if ok:
            print("✅ فەرمانەکانی مێنیو لە هەموو سکۆپەکان دانران (بێ /server)", flush=True)
            # #88: /server تەنها لە مێنیوی ئەدمین
            admin_cmds = cmds + [{"command": "server", "description": "قائمة الموديلات — الأحدث دائما"},
                            {"command": "status", "description": "📊 ڕاپۆرتی سیستەم"},
                            {"command": "heal", "description": "🩺 پشکنین و چاککردنەوە"},
                            {"command": "stats", "description": "📈 ئامارەکانی خارق"},
                            {"command": "test", "description": "🧪 تاقیکردنەوەی مۆدێڵ"}]
            r = tg("setMyCommands", commands=admin_cmds, scope={"type": "chat", "chat_id": ADMIN_TG})
            print(f"[CMDS] ئەدمین-سکۆپ: {'✅' if r.get('ok') else 'شکست'}", flush=True)
            return
        print(f"[CMDS] هەوڵ {attempt+1} — دووبارە…", flush=True)
        time.sleep(2)


def start_hf_keepalive():
    """سێرڤەری بچووک + خۆپینگ — بۆ Hugging Face و Render (بۆ نەخەوتن)"""
    import os
    sid = os.environ.get("SPACE_ID")          # Hugging Face
    ext_url = os.environ.get("RENDER_EXTERNAL_URL")  # Render
    if not sid and not ext_url:
        return
    import http.server
    import socketserver
    port = int(os.environ.get("APP_PORT", 7860))

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("🤖 بۆتەکە زیندووە".encode("utf-8"))

        def log_message(self, *a):
            pass

    def serve():
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("0.0.0.0", port), H) as s:
                s.serve_forever()
        except Exception as e:
            print(f"[KEEP] serve: {e}", flush=True)

    threading.Thread(target=serve, daemon=True).start()
    url = ext_url or f"https://{sid.replace('/', '-').lower()}.hf.space"
    where = "Render" if ext_url else "Hugging Face"

    def ping():
        while True:
            time.sleep(840)  # ١٤ خولەک
            try:
                requests.get(url, timeout=15)
            except Exception:
                pass

    threading.Thread(target=ping, daemon=True).start()
    print(f"[KEEP] خۆپینگی {where} لەسەر {url}", flush=True)


def _self_update_daemon():
    """خۆ-نوێکردنەوە لە GitHub raw — هەر ١٠ خولەک؛ تەنها ئەگەر کۆدە نوێیە py_compile تێپەڕێت"""
    import sys as _s, time as _t, subprocess as _sp
    url = "https://raw.githubusercontent.com/Yusfkarim/ayai/main/main.py"
    local = os.path.abspath(__file__)
    while True:
        _t.sleep(600)
        try:
            r = requests.get(url, timeout=(10, 30), headers={"User-Agent": "selfupdater"})
            if r.status_code != 200:
                continue
            new = r.text
            if "def main(" not in new:
                continue
            try:
                cur = open(local, encoding="utf-8").read()
            except Exception:
                continue
            if new == cur:
                continue
            tmp = local + ".new"
            open(tmp, "w", encoding="utf-8").write(new)
            if _sp.run([_s.executable, "-m", "py_compile", tmp], capture_output=True).returncode != 0:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                continue
            os.replace(tmp, local)
            print("[SELF-UPDATE] کۆدی نوێ لە GitHub — ریستارت…", flush=True)
            _t.sleep(2)
            os.execv(_s.executable, [_s.executable] + _s.argv)
        except Exception:
            continue



# ══════════ #89: خۆبەڕێوەبەری گشتی — چاودێری + چاککردنەوەی خۆکارانەی هەموو سەرچاوەکان ══════════
_HEAL_STATE = {"t": 0.0, "status": {}}  # kind → {"ok":bool,"t":float,"err":str}


def _heal_probe(kind, fn):
    """یەک پشکنینی کورت بۆ سەرچاوەیەک — وەڵامی کورت = زیندوو (fn() بێ-ئارگومێنت)"""
    try:
        a = fn()
        return bool(a and len(str(a)) >= 2), ""
    except Exception as e:
        return False, str(e)[:60]


def self_heal_once():
    """یەک خولی پشکنین + چاککردنەوەی خۆکارانە — تەنها سەرچاوە کێشەدار/گرنگەکان (خێرا)"""
    probes = {}
    if MS.get("ct_ok"):
        probes["ct"] = lambda: ct_chat([{"role": "user", "content": "hi"}], list(MS["ct_ok"].keys())[0], timeout=45)
    if MS.get("hk_ok"):
        probes["hk"] = lambda: hk_chat([{"role": "user", "content": "hi"}], list(MS["hk_ok"].keys())[0], timeout=45)
    if MS.get("hf_ok"):
        probes["hf"] = lambda: hf_chat([{"role": "user", "content": "hi"}], list(MS["hf_ok"].keys())[0], timeout=45)
    # cbc لابراوە — ڕاگیراو (بڕوانە سەرەوە)
    if MS.get("ak_ok"):
        probes["ak"] = lambda: ak_chat(list(MS["ak_ok"].keys())[0], [{"role": "user", "content": "hi"}], timeout=45)
    # حەوزەکان — گرنگترین
    # #91Z: probe — مۆدێڵێکی کەم-داواکاری (nano لەوانەیە هەموو ئەکاونتەکانی limit بێت)
    _ca_m = next((k for k in MS.get("ca_ok", {}) if "gemini" in k or "claude" in k), "gpt-5.4-nano")
    probes["ca"] = lambda: ca_chat([{"role": "user", "content": "hi"}], _ca_m, timeout=50)
    _cb_m = next(iter(MS["cb_ok"].keys()), "4o-mini") if MS.get("cb_ok") else "4o-mini"
    def _cb_probe(_m=_cb_m):
        # #94U19: ئەگەر مۆدێلی یەکەم limit بوو → دووبارە بە 4o-mini
        try:
            return cb_chat([{"role": "user", "content": "hi"}], _m, timeout=50)
        except Exception:
            if _m != "4o-mini":
                return cb_chat([{"role": "user", "content": "hi"}], "4o-mini", timeout=50)
            raise
    probes["cb"] = _cb_probe
    probes["cbox"] = lambda: cbox_chat([{"role": "user", "content": "hi"}], "aichat", timeout=50)
    probes["nv"] = lambda: nv_chat([{"role": "user", "content": "hi"}], "auto", timeout=50)
    fixed = []
    # #91Z: DARK-RECOVERY — سەرچاوەی بەتاڵ (مانگانە وەک hf) هەر خولی سێیەم هەوڵی زیندووکردنەوە
    if (_HEAL_STATE.get("cyc", 0) % 3) == 0:
        for dk in ("hf", "hk", "ct"):
            try:
                if not MS.get(dk + "_ok"):
                    globals()[f"sync_{dk}_models"](force=True)
                    if MS.get(dk + "_ok"):
                        fixed.append(f"{dk}→ darkness-healed ✨")
                        print(f"[SELF-HEAL] ✨ {dk} لە تاریکییەوە گەڕایەوە!", flush=True)
            except Exception:
                pass
    for kind, fn in probes.items():
        fprev = int((_HEAL_STATE["status"].get(kind) or {}).get("fails", 0))
        if fprev >= 6 and (_HEAL_STATE.get("cyc", 0) % 3) != 0:
            continue  # #91++: پشووی بەرزکراو — هەر خولی سێیەم دووبارە هەوڵ
        ok, err = _heal_probe(kind, fn)
        _HEAL_STATE["status"][kind] = {"ok": ok, "t": time.time(), "err": err, "fails": (0 if ok else fprev + 1)}
        if not ok:
            try:
                _revive_source(kind, err)
                fixed.append(f"{kind}→revive")
            except Exception:
                pass
    if fixed:
        print(f"[SELF-HEAL] 🔧 چاککردنەوە: {', '.join(fixed)}", flush=True)
    st = _HEAL_STATE["status"]
    line = " ".join(f"{k}:{'✅' if v['ok'] else '❌'}" for k, v in sorted(st.items()))
    print(f"[SELF-HEAL] {line}", flush=True)
    _snapshot_save()


def _proxy_refresh_sources():
    """#91: تازەکردنەوەی لیستی پرۆکسی زیندوو — بەزۆر _proxy_get لیستەکە دادەنێت"""
    try:
        pl = _proxy_get(30)
        if pl:
            PROXY_ST["list"] = [p.replace("://", "://") for p in pl]
            PROXY_ST["src_t"] = time.time()
    except Exception as e:
        print(f"[PROXY-KEEPER] refresh: {str(e)[:50]}", flush=True)


def proxy_keeper_daemon():
    """#91: چاودێری پرۆکسی — هەر ٣٠ خولەک + 🔭 دۆزینەوەی مۆدێڵی نوێ هەر ٦ کاتژمێر"""
    time.sleep(120)
    cyc = 0
    while True:
        try:
            _proxy_refresh_sources()
            n = len(PROXY_ST.get("pool") or PROXY_ST.get("list") or [])
            _rn = sum(1 for v in (PROXY_ST.get("pool") or {}).values() if v.get("res"))
            print(f"[PROXY-KEEPER] حەوز: {n} | منزلی: {_rn} | خێراترین و تازەترین", flush=True)
        except Exception as e:
            print(f"[PROXY-KEEPER] هەڵە: {str(e)[:60]}", flush=True)
        cyc += 1
        if cyc % 12 == 0:
            def _sweep():
                done = []
                for nm in ("ca", "cb", "nv", "duck", "l7", "ac", "gk", "gz", "pi", "hb", "yl", "aka"):
                    try:
                        f = globals().get(f"sync_{nm}_models")
                        if not f:
                            continue
                        try:
                            f(force=True)
                        except TypeError:
                            f([])
                        done.append(nm)
                        time.sleep(3)
                    except Exception:
                        pass
                print(f"[DISCOVERY] 🔭 گەڕان بۆ مۆدێڵی نوێ تەواو بوو: {', '.join(done)}", flush=True)
            threading.Thread(target=_sweep, daemon=True).start()
        time.sleep(1800)


def self_heal_daemon():
    """هەر ١٠ خولەک — پشکنینی هەموو سەرچاوەکان + چاککردنەوەی شکاوەکان"""
    time.sleep(60)
    while True:
        try:
            _HEAL_STATE["cyc"] = _HEAL_STATE.get("cyc", 0) + 1
            self_heal_once()
        except Exception as e:
            print(f"[SELF-HEAL] هەڵە: {str(e)[:60]}", flush=True)
        time.sleep(600)



# ═══════════ #91+ خارق: چینەکانی بەهێزکردنی کۆتایی ═══════════
BOOT_T = time.time()
_PERF = {"req": 0, "ok": 0, "fail": 0, "lat": []}
_BREAKER = {}
_ANS_CACHE = {}
_USER_Q = {}
_HB = {"t": 0.0}
_DAILY = {"day": None}


def _uq(text):
    import hashlib
    return hashlib.md5(str(text).encode("utf-8", "ignore")).hexdigest()


_ask_orig = ask


def ask(session, question):
    """خارق: throttle + کاشی وەڵام + ئامار — لەسەر سەرەوەی ask ی ئەصلی"""
    uid = session.get("user_id")
    if uid and uid != ADMIN_TG:
        now = time.time()
        ql = [t for t in _USER_Q.get(uid, []) if now - t < 60]
        if len(ql) >= 12:
            return "⚠️ رسائل كثيرة جدًا — انتظر دقيقة ثم أعد الإرسال."
        ql.append(now)
        _USER_Q[uid] = ql
        # #91F4: پاککردنەوەی بەکارهێنەری کۆن (memory)
        if len(_USER_Q) > 500:
            for u2 in list(_USER_Q.keys())[:250]:
                if not [t for t in _USER_Q.get(u2, []) if now - t < 300]:
                    _USER_Q.pop(u2, None)
    _hist = session.get("history") or []
    ck = (str(session.get("mkey") or session.get("server") or ""),
          _uq(str(_hist[-6:]) + "||" + str(question)))  # #91Z: کۆنتێکستیش لە کلیل
    c = _ANS_CACHE.get(ck)
    if c and time.time() - c[0] < 300:
        return c[1]
    t0 = time.time()
    a = None
    for _att in range(2):
        try:
            a = _ask_orig(session, question)
            break
        except Exception:
            if _att == 1:
                _PERF["req"] += 1
                _PERF["fail"] += 1
                raise
            time.sleep(2.5)  # #91++: دووبارەی کۆتایی — تۆڕی کاتی
    dt = time.time() - t0
    _PERF["req"] += 1
    _PERF["ok"] += 1
    _PERF["lat"].append(dt)
    if len(_PERF["lat"]) > 200:
        del _PERF["lat"][:100]
    if a:
        _ANS_CACHE[ck] = (time.time(), a)
        if len(_ANS_CACHE) > 400:
            for k2, _ in sorted(_ANS_CACHE.items(), key=lambda x: x[1][0])[:200]:
                _ANS_CACHE.pop(k2, None)
    return a



def _limit_dawn_daemon():
    """#91Z: بەیانی لیمیتەکان — هەموو ڕۆژێک لە 00:10 UTC:
       ستاری دوێنێ دەسڕدرێتەوە + سەرچاوە مانگانە (hf/hk/ct) هەوڵی زیندووکردنەوەیان لێدەکرێت"""
    while True:
        try:
            now = time.time()
            nxt = (now // 86400 + 1) * 86400 + 600
            time.sleep(max(60, nxt - now))
            today = _lim_today()
            n_all = 0
            for nm, st, sv in (("CA", CA_ST, _ca_save_acc), ("AC", AC_ST, _ac_save_acc)):
                lim = st.get("limits") or {}
                n = 0
                for e, v in list(lim.items()):
                    if not isinstance(v, dict):
                        continue
                    for k in list(v.keys()):
                        val = v.get(k)
                        if val is True:
                            continue  # هەمیشەیی (lifetime) — دەمێنێتەوە
                        if str(val or "") < today:
                            v.pop(k, None)
                            n += 1
                if n:
                    try:
                        sv()
                    except Exception:
                        pass
                n_all += n
                if n:
                    print(f"[DAWN] {nm}: {n} لیمێتی دوێنێ سڕانەوە — ئەکاونتەکان گەڕانەوە", flush=True)
            # سەرچاوە مانگانە — هەوڵی زیندووکردنەوە
            healed = []
            for dk in ("hf", "hk", "ct"):
                try:
                    if not MS.get(dk + "_ok"):
                        globals()[f"sync_{dk}_models"](force=True)
                        if MS.get(dk + "_ok"):
                            healed.append(dk)
                except Exception:
                    pass
            try:
                if NV_ST.get("exc"):
                    NV_ST["exc"] = {}
                    _nv_save_acc()
                    print("[DAWN] NV: کۆڵەکانی دوێنێ پاککرانەوە", flush=True)
            except Exception:
                pass
            print(f"[DAWN] 🌅 خاڵی سفر — {n_all} لیمێت پاککرانەوە" + (f" + ✨ {healed}" if healed else ""), flush=True)
        except Exception as e:
            print(f"[DAWN] هەڵە: {str(e)[:60]}", flush=True)


def _xarq_watchdog():
    """چاودێری خودی بۆت — ئەگەر polling ڕاوەستا ٥ خولەک → ڕیستارتی تەواو (fly یەکسان دەیگەڕێنێتەوە)"""
    time.sleep(420)
    armed = False
    while True:
        try:
            t = _HB.get("t") or 0
            if t:
                armed = True
            if armed and t and time.time() - t > 900:
                print("[WATCHDOG] ⏰ polling وەستاویە — ڕیستارتی خودکار", flush=True)
                os._exit(1)
        except Exception:
            pass
        time.sleep(60)


def _daily_report():
    """ڕاپۆرتی ڕۆژانە بۆ ئەدمین — #91R2: تەنها یەک جار/ڕۆژ (state لە /data) + کاراک بە خولەک"""
    time.sleep(420)  # ٧ خولەک پاش boot — تا سیستەم گەرم بێت
    while True:
        try:
            day = time.strftime("%Y-%m-%d", time.gmtime())
            _sent = ""
            try:
                _sent = (open(os.path.join(DATA_DIR, "daily_sent.txt")).read() or "").strip()
            except Exception:
                pass
            if _sent != day:
                up = int(time.time() - BOOT_T)
                lat = _PERF["lat"]
                avg = (sum(lat) / len(lat)) if lat else 0
                st = _HEAL_STATE.get("status", {})
                okn = sum(1 for v in st.values() if v.get("ok"))
                po = {}
                for nm, f in (("CA", "ca_accounts.json"), ("CB", "cb_accounts.json"), ("NV", "nv_accounts.json")):
                    try:
                        d = _json_load_safe(os.path.join(DATA_DIR, f)) or {}
                        po[nm] = len(d.get("accounts", [])) if isinstance(d, dict) else len(d)
                    except Exception:
                        po[nm] = 0
                try:
                    nm = len(dedupe_servers(BRAIN["servers"])) if BRAIN["servers"] else 0
                except Exception:
                    nm = 0
                _uptxt = f"{up // 3600} کاتژمێر و {(up % 3600) // 60} خولەک" if up >= 3600 else f"{up // 60} خولەک"
                msg = (f"🌅 <b>ڕاپۆرتی ڕۆژانەی سیستەمی خارق</b> — {day}\n"
                       f"⏱ کاراک: {_uptxt}\n"
                       f"🧠 مۆدێڵ: {nm}\n"
                       f"✅ سەرچاوەی زیندوو: {okn}/{len(st) or '—'}\n"
                       f"💰 حەوز: CA {po['CA']} · CB {po['CB']} · NV {po['NV']}\n"
                       f"⚡ داواکاری: {_PERF['req']} (تێکڕای وەڵام {avg:.1f} چرکە)")
                sent_any = False
                for cid in REPORT_CHAT_IDS:
                    try:
                        r = tg("sendMessage", chat_id=cid, text=msg, parse_mode="HTML")
                        if r.get("ok"):
                            sent_any = True
                    except Exception as de:
                        print(f"[DAILY] {cid}: {de}", flush=True)
                if sent_any:
                    open(os.path.join(DATA_DIR, "daily_sent.txt"), "w").write(day)
        except Exception as e:
            print(f"[DAILY] {str(e)[:60]}", flush=True)
        time.sleep(600)




# ═══════════ #91++ چینی کڕاک: دووبارەهەوڵی شەفاف لە ئاستی HTTP ═══════════
# سەرچاوە ڕێگای خۆی بگۆڕێت (403/418/429/502/503) → UA نوێ + پرۆکسی + دووبارە — بێ دەست لێدان
_CRACK = {"hot": {}, "uas": [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
]}
_orig_sess_req = requests.sessions.Session.request


def _cracked_req(self, method, url, **kw):
    try:
        m = re.match(r"https?://([^/]+)", str(url))
        dom = m.group(1) if m else ""
    except Exception:
        dom = ""
    r = _orig_sess_req(self, method, url, **kw)
    try:
        if dom == "api.telegram.org" or kw.get("stream"):
            return r
        if r.status_code in (403, 418, 429, 502, 503):
            _CRACK["hot"][dom] = int(_CRACK["hot"].get(dom, 0)) + 1
            if _CRACK["hot"][dom] >= 6:  # #94U23: دۆمەینی مردوو — دووبارە مەکە (revive+fallback بەڕێوەی دەبەن)
                return r
            kw2 = dict(kw)
            h = dict(kw2.get("headers") or {})
            # #91ID: ئەگەر سێشنەکە ناسنامەی خۆی هەیە → پاراستنی (cookie+UA یەک دەمێنن)
            _sua = (getattr(self, "headers", None) or {}).get("User-Agent") if hasattr(self, "headers") else None
            h["User-Agent"] = _sua or _rand_ua()  # #91S+#91ID
            kw2["headers"] = h
            _rl = r.status_code in (403, 418, 429)  # #94U23: خێزانی سنوور/ڕێژە → پرۆکسی لە یەکەم شکستەوە (نەک سێیەم)
            if _CRACK["hot"].get(dom, 0) >= (1 if _rl else 2) and not kw2.get("proxies"):
                try:
                    pl = _proxy_get(1)
                    if pl:
                        kw2["proxies"] = {"http": pl[0], "https": pl[0]}
                except Exception:
                    pass
            time.sleep(random.uniform(0.3, 1.0))
            r2 = None
            # #91ST+/A8: TLS-STEALTH — یەکەم دووبارە بە curl_cffi (پەنجەمۆری وێبگەڕ) — STREAM ەش
            try:
                lib = _STEALTH_TLS.get("lib")
                if lib and _STEALTH_TLS.get("enabled"):
                    _m2 = method.lower()
                    _u2 = str(url)
                    _h2 = {**dict(self.headers or {}), **h}
                    _imp = random.choice(_CF_IMPERSONATE)
                    if _m2 == "get":
                        _kw2s = {"stream": True} if kw2.get("stream") else {}
                        r2 = lib.get(_u2, impersonate=_imp, headers=_h2,
                                     timeout=(10, max(15, int((kw2.get("timeout") or (10, 30))[-1]) if not isinstance(kw2.get("timeout"), int) else 30)),
                                     **_kw2s)
                    elif _m2 == "post" and kw2.get("json") is not None:
                        _kw2s = {"stream": True} if kw2.get("stream") else {}
                        r2 = lib.post(_u2, impersonate=_imp, headers=_h2, json=kw2["json"],
                                      timeout=(10, 45), **_kw2s)
            except Exception:
                r2 = None
            if r2 is None:
                r2 = _orig_sess_req(self, method, url, **kw2)
            if r2.status_code in (403, 418, 429, 502, 503):
                # #94U23: پرۆکسییە شکستخواردووەکە بسووتێنە + دووبارەی دووەم بە IP ی جیاواز
                try:
                    _used = (kw2.get("proxies") or {}).get("https") or (kw.get("proxies") or {}).get("https")
                    if _used:
                        _proxy_mark_bad(_used)
                    kw3 = dict(kw2)
                    _pl3 = [p for p in (_proxy_get(3) or []) if p != _used]
                    if _pl3:
                        kw3["proxies"] = {"http": _pl3[0], "https": _pl3[0]}
                        time.sleep(random.uniform(0.5, 1.2))
                        r2 = _orig_sess_req(self, method, url, **kw3)
                except Exception:
                    pass
            if r2.status_code not in (403, 418, 429, 502, 503):
                _CRACK["hot"][dom] = 0
            return r2
        if r.status_code < 400:
            _CRACK["hot"][dom] = 0
    except Exception:
        pass
    return r


requests.sessions.Session.request = _cracked_req


def _snapshot_save():
    """#91++: سناپشۆتی مۆدێڵەکان بۆ /data — ڕیستارت هەرگیز مۆدێڵ لەدەست نادات"""
    try:
        with _lock:
            ms = {k: dict(v) for k, v in MS.items() if k.endswith("_ok") and v}
            srv = list(BRAIN["servers"] or [])
        _json_save(os.path.join(DATA_DIR, "model_snapshot.json"),
                   {"t": time.time(), "ms": ms, "servers": srv})
    except Exception:
        pass


def _snapshot_load():
    try:
        d = json.load(open(os.path.join(DATA_DIR, "model_snapshot.json")))
        n = 0
        for k, v in (d.get("ms") or {}).items():
            if k in MS and not MS.get(k):
                MS[k] = dict(v)
                n += len(v)
        age = int(time.time() - d.get("t", 0))
        print(f"[SNAPSHOT] {n} مۆدێڵ لە کاشی کۆتایی هێنانەوە ({age} چرکە پێش)", flush=True)
        return d.get("servers") or []
    except Exception:
        return []



# ═══════════ #91U: چینی ULTRA — کراکەری بەقوەتی AI ═══════════
_API_RL = {}  # key → [t, t, ...] — rate limit per API key
_API_KEYS = {"sk-yf-31c00f02aa9221b336d7b4a274bb375c": {"name": "primary", "rpm": 60}}
_STS = {"t": 0.0, "ok": True, "last": ""}


_STRANGE_KEY_RPM = 20      # Max 20 req/min بۆ وێب و کلیدی نامۆ
_STRANGE_KEYS_SEEN = {}    # key -> {"count": int, "blocked_until": float, "burst": []}

# ─── #94U11: قاتی پێنجەم — Honeypot + بڵۆکی بڕوتفۆرس + دزەگری دەستدرێژ ───
_HP_PATHS = {"/.env", "/wp-login.php", "/wp-admin", "/admin", "/admin.php",
             "/config", "/.git", "/.git/config", "/phpmyadmin", "/.aws",
             "/credentials", "/xmlrpc.php", "/.DS_Store", "/backup.sql",
             "/dump.sql", "/actuator", "/debug/var_dump", "/telemetry"}
_IP_BLOCK = {}      # ip → کاتی کۆتایی بڵۆک
_BADKEY = {}        # ip → [کاتەکانی هەوڵی کلیدی هەڵە]
_HP_CNT = {}        # ip → ژمارەی داواکاری honeypot
_SEC_ALERT = [0.0]  # دوا کاتی ئاگاداری TG (throttle)


def _sec_ip(handler):
    """ئایپی متمانەپێکراو — Fly-Client-IP لەلایەن edge ەوە دادەنرێت، لێدۆرا نابێت"""
    try:
        return (handler.headers.get("Fly-Client-IP")
                or handler.headers.get("CF-Connecting-IP")
                or (handler.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
                or (handler.client_address[0] if handler.client_address else "?"))
    except Exception:
        return "?"


def _ip_blocked(ip):
    """ئایا ئەم ئایپیه بلۆکراوە؟ خۆ-پاککردنەوەی بڵۆکە کۆنەکان"""
    if not ip:
        return False
    exp = _IP_BLOCK.get(ip)
    if exp is None:
        return False
    if exp <= time.time():
        _IP_BLOCK.pop(ip, None)
        return False
    return True


def _sec_alert(msg):
    """ئاگاداری ئەمنی بۆ هەردوو چات — زۆتر لە یەک جار لە ٥ خولەک نانێردرێت"""
    if time.time() - _SEC_ALERT[0] < 300:
        return
    _SEC_ALERT[0] = time.time()
    for cid in (8381536661, 7585287282):
        try:
            tg("sendMessage", chat_id=cid, text=msg, parse_mode="HTML")
        except Exception:
            pass


def _note_badkey(ip):
    """هەوڵی کلیدی هەڵە — ١٠ هەوڵ لە ١٠ خولەکدا → بڵۆکی ١٥ خولەک + ئاگاداری TG"""
    if not ip:
        return
    now = time.time()
    arr = [x for x in (_BADKEY.get(ip) or []) if now - x < 600]
    arr.append(now)
    _BADKEY[ip] = arr[-25:]
    if len(arr) >= 10:
        _IP_BLOCK[ip] = now + 900
        _BADKEY[ip] = []
        print(f"[SEC] 🚨 brute-force لە {ip} — بڵۆک ١٥ خولەک", flush=True)
        _sec_alert(f"🚨 <b>بڕوتفۆرسی کلیدی API</b>\nIP: <code>{ip}</code>\n١٠+ کلیدی هەڵە لە ١٠ خولەکدا — ئایپیه بڵۆک کرا بۆ ١٥ خولەک")


def _note_honeypot(ip, path):
    """ڕێڕەوی تەڵە — بڵۆکی خێرا ٦ کاتژمێر + ئاگاداری TG"""
    if not ip:
        return
    now = time.time()
    _IP_BLOCK[ip] = max(_IP_BLOCK.get(ip, 0), now + 21600)
    _HP_CNT[ip] = (_HP_CNT.get(ip) or 0) + 1
    print(f"[SEC] 🍯 honeypot {ip} → {path} (کۆی گشتی {_HP_CNT[ip]})", flush=True)
    _sec_alert(f"🍯 <b>Honeypot — دەستدرێژکار دەستگیرکرا</b>\nIP: <code>{ip}</code>\nڕێڕەو: <code>{path}</code>\nبڵۆک ٦ کاتژمێر")


def _api_rate_ok(key, client_ip=""):
    """#94U6: سەپاندنی ڕێژە — بەهێزکراو بۆ وێب و کلیلە سەرەکی و نامۆکان"""
    now = time.time()
    # ١. ئەگەر کلیلی سەرەکییە یان فەرمی
    if key and (key in _API_KEYS or key == API_KEY):
        cfg = _API_KEYS.get(key) or {"rpm": 60}
        win = [t for t in _API_RL.get(key, []) if now - t < 60]
        if len(win) >= cfg.get("rpm", 60):
            return False, "rate limit — 60 req/min exceeded"
        win.append(now)
        _API_RL[key] = win
        return True, ""
    # ٢. کلیلی نامۆ یان داواکاری بێ-کلیل لە وێبسایتەوە
    track_id = key if key else f"guest_{client_ip or 'web'}"
    st = _STRANGE_KEYS_SEEN.setdefault(track_id, {"count": 0, "blocked_until": 0.0, "burst": []})
    if now < st.get("blocked_until", 0.0):
        remain = int(st["blocked_until"] - now)
        return False, f"unrecognized/guest key throttled: {remain}s cooldown remaining"
    st["burst"] = [t for t in st["burst"] if now - t < 60]
    limit = _STRANGE_KEY_RPM
    if len(st["burst"]) >= limit:
        st["blocked_until"] = now + 120  # بلۆکی ٢ خولەکی کاتی بۆ پاراستن لە سپام
        print(f"[SECURITY] 🚨 Strange/Guest key throttled: {track_id[:16]}...", flush=True)
        return False, f"rate limit — guest/unregistered key limited to {limit} req/min"
    st["burst"].append(now)
    st["count"] += 1
    return True, ""


def _self_check():
    """#91U: خۆپشکنین — نەک تەنها لۆگ — ڕاستەوخۆ تاقیکردنەوەی ناوەکی"""
    try:
        try:
            _check_code_integrity(is_boot=False)
        except Exception:
            pass
        br = len(BRAIN["servers"] or [])
        try:
            ap = len(API_BRAIN["servers"] or [])
        except Exception:
            ap = br  # API_BRAIN هێشتا دەستپێ نەکراوە — وەک BRAIN ژمارە پێبکە
        live = sum(1 for v in _HEAL_STATE.get("status", {}).values() if v.get("ok"))
        _STS["ok"] = br > 0 and ap > 0
        _STS["last"] = f"br={br} ap={ap} live={live}"
        _STS["t"] = time.time()
    except Exception as e:
        _STS["ok"] = False
        _STS["last"] = str(e)[:50]


_SELFCHK = {"fails": 0}


def _self_check_daemon():
    """هەر ٥ خولەک خۆپشکنینی ناوەکی — #94U2: ٢ خولی لەسەریەک پێش ڕیستارت (bootstrap-grace)"""
    time.sleep(300)
    while True:
        try:
            try:
                api_brain_ensure()  # #94U2: هەموو خولێک — بێ پێویستی تڕافیک
            except Exception:
                pass
            _self_check()
            if not _STS["ok"]:
                _SELFCHK["fails"] += 1
                if _SELFCHK["fails"] >= 2:
                    print(f"[SELF-CHECK] ⚠️ {_STS['last']} x{_SELFCHK['fails']} — ڕیستارتی خۆکار", flush=True)
                    os._exit(1)
                print(f"[SELF-CHECK] ⏳ {_STS['last']} — خولی {_SELFCHK['fails']}/2 — چاوەڕێ…", flush=True)
            else:
                if _SELFCHK["fails"]:
                    print(f"[SELF-CHECK] ✅ گەڕایەوە — {_STS['last']}", flush=True)
                _SELFCHK["fails"] = 0
        except Exception:
            pass
        time.sleep(300)


def _chaos_daemon():
    """#91U: CHAOS — تاقیکردنەوەی بەرخودان — هەر ٦ کاتژمێر پرۆبێی نەناسراو"""
    time.sleep(1800)
    while True:
        try:
            if BRAIN["servers"]:
                srv = random.choice(BRAIN["servers"][-5:])  # لە کۆتایی لیست — کەمتر بەکارهاتوو
                k = srv.get("kind")
                msgs = [{"role": "user", "content": "test"}]
                t0 = time.time()
                try:
                    fn = globals().get(f"{k}_chat")
                    if fn:
                        if k in ("ca", "cb", "nv", "ct", "hk", "hf", "aka", "hb", "gk", "gz", "pi", "ac", "l7", "g4f", "al", "aiml", "z02", "pia", "alle", "cbox"):
                            a = fn(msgs, srv.get("model_id") or srv.get("id"), timeout=30)
                        elif k in ("fla", "qb", "ng"):
                            a = fn(msgs, timeout=30)
                        else:
                            a = None
                        if a:
                            print(f"[CHAOS] ✅ {k} وەڵامی دا ({time.time()-t0:.1f}s)", flush=True)
                except Exception as e:
                    print(f"[CHAOS] ⚠️ {k}: {str(e)[:50]}", flush=True)
        except Exception:
            pass
        time.sleep(21600)  # ٦ کاتژمێر




# ═══════════ #91F2: FORTRESS — پێنج چینی کۆتایی ═══════════
_STATE_PERSIST = {"t": 0.0}


def _state_persist_daemon():
    """#91F2-1: پاشەکەوتی دۆخ — breaker+perf لە /data — ڕیستارت = بیرەوەری ناوەکە دەمێنێتەوە"""
    # لۆدی دۆخی پێشوو
    try:
        d = json.load(open(os.path.join(DATA_DIR, "state.json")))
        for k, v in (d.get("breaker") or {}).items():
            if v > time.time():
                _BREAKER[k] = v
        p = d.get("perf") or {}
        if p:
            _PERF["req"] += p.get("req", 0)
            _PERF["ok"] += p.get("ok", 0)
            _PERF["fail"] += p.get("fail", 0)
    except Exception:
        pass
    while True:
        try:
            now = time.time()
            if now - _STATE_PERSIST["t"] > 120:
                _STATE_PERSIST["t"] = now
                _json_save(os.path.join(DATA_DIR, "state.json"),
                           {"breaker": {k: v for k, v in _BREAKER.items() if v > now},
                            "perf": {"req": _PERF["req"], "ok": _PERF["ok"], "fail": _PERF["fail"]}})
        except Exception:
            pass
        time.sleep(120)


def _disk_guard_daemon():
    """#91F2-2: پارێزی دیسک — ئەگەر /data پڕ بێت → پاککردنەوەی کۆنەکان (قەت پڕ نابێت)"""
    time.sleep(600)
    while True:
        try:
            total = 0
            files = []
            for f in os.listdir(DATA_DIR):
                try:
                    p = os.path.join(DATA_DIR, f)
                    if os.path.isfile(p):
                        sz = os.path.getsize(p)
                        total += sz
                        files.append((sz, p, os.path.getmtime(p)))
                except Exception:
                    pass
            if total > 80 * 1024 * 1024:  # 80MB — سنووری ئاگاداری
                files.sort()  # کۆنترین + گەورەترین سەرەتا
                freed = 0
                for sz, p, mt in files:
                    if freed > 40 * 1024 * 1024:
                        break
                    if "accounts" in p or "state.json" in p or "webshare" in p or "global_model" in p:
                        continue  # فایلی ڕەسەن — دەست نادرێت
                    try:
                        os.remove(p)
                        freed += sz
                    except Exception:
                        pass
                print(f"[DISK] 🧹 {freed // 1024}KB ئازادکرا — کۆی: {total // 1024 // 1024}MB", flush=True)
        except Exception:
            pass
        time.sleep(1800)


def _rescue_daemon():
    """#91F2-3: ڕزگارکەر — ئەگەر هەموو سەرچاوەکان breaker بوون → breaker ەکانی سەرچاوە سەرەکییەکان بسڕەوە"""
    time.sleep(300)
    while True:
        try:
            now = time.time()
            active = [k for k, v in _BREAKER.items() if v > now]
            if len(active) >= 4:  # زۆربەی سەرچاوەکان لە پشوودان
                # سەرچاوە حەوزدارەکان هەمیشە ئازاد بن — ئەوان ئەکاونتیان هەیە
                for k in ("ca", "cb", "nv"):
                    if k in _BREAKER:
                        _BREAKER.pop(k, None)
                        print(f"[RESCUE] 🔓 breaker ی {k} لابرا — حەوز هەمیشە ئازادە", flush=True)
        except Exception:
            pass
        time.sleep(120)


def _hot_model_daemon():
    """#91F2-4: گەرمکردنی مۆدێڵەکان — هەر ٣٠ خولەک مۆدێڵی بەکارهێنراو گەرم دەکرێت (کاش)"""
    time.sleep(600)
    while True:
        try:
            # سێ مۆدێڵی سەرەکی — پێش داواکاری ڕاستەقینە گەرم بن
            warm = ["openai/gpt-5.5", "deepseek/deepseek-v3.2", "google/gemini-2.5-pro"]
            for mid in warm:
                try:
                    srv = next((x for x in API_BRAIN["servers"] if x.get("id") == mid), None)
                    if not srv:
                        continue
                    k = srv.get("kind")
                    fn = globals().get(f"{k}_chat")
                    if fn:
                        msgs = [{"role": "user", "content": "ping"}]
                        if k in ("ca", "cb", "nv", "ct", "hk", "hf", "aka", "hb", "gk", "gz", "pi", "ac", "l7", "g4f", "al", "aiml", "z02", "pia", "alle", "cbox"):
                            fn(msgs, srv.get("model_id") or mid, timeout=25)
                except Exception:
                    pass
                time.sleep(5)
            print("[WARM] 🔥 مۆدێڵە گرنگەکان گەرم کران", flush=True)
        except Exception:
            pass
        time.sleep(1800)


_API_KEYS_LOG = {"n": 0}


def _usage_snapshot_daemon():
    """#91F2-5: تۆماری بەکارهێنان — ڕاپۆرتی کاتژمێری ورد بۆ ئەدمین (تەنها ئەگەر چالاک بوو)"""
    time.sleep(3600)
    _last_req = 0
    while True:
        try:
            now = int(time.time())
            hr = time.strftime("%H:00", time.gmtime(now - 3600))
            delta = _PERF["req"] - _last_req
            _last_req = _PERF["req"]
            if delta > 0:
                lat = _PERF["lat"]
                avg = (sum(lat) / len(lat)) if lat else 0
                st = _HEAL_STATE.get("status", {})
                okn = sum(1 for v in st.values() if v.get("ok"))
                for cid in REPORT_CHAT_IDS:
                    try:
                        tg("sendMessage", chat_id=cid, parse_mode="HTML",
                           text=(f"📊 <b>کاتژمێری {hr} UTC</b>\n"
                                 f"⚡ داواکاری: {delta}\n"
                                 f"✅ سەرچاوە: {okn}/{len(st)}\n"
                                 f"⏳ تێکڕا: {avg:.1f}s\n"
                                 f"💾 کاش: {len(_ANS_CACHE)}"))
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(3600)



# ═══════════ #91S: SPIDER — چینی دۆزینەوەی خۆکاری ماڵپەڕەکان ═══════════
_SPIDER = {"found": {}, "t": 0.0}

_UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/604.1",
]


def _rand_ua():
    """#91S: ناسنامەی هەڕەمەکی — هەر داواکارییەکی دەرەکی جیاواز"""
    return random.choice(_UA_POOL)


_UA_STICK = {}


def _pick_ua(pool, win=600):
    """#91ID: IDENTITY-LOCK — هەمان UA بۆ ١٠ خولەک (وەک وێبگەڕی ڕاستەقینە).
       پێشتر: هەر داواکارییەک UA ی نوێ = same-session identity flip = دەستنیشانکردن!"""
    try:
        k = id(pool)
        now = time.time()
        v = _UA_STICK.get(k)
        if not v or now - v[0] > win:
            v = (now, random.choice(pool))
            _UA_STICK[k] = v
            if len(_UA_STICK) > 50:
                _UA_STICK.pop(next(iter(_UA_STICK)), None)
        return v[1]
    except Exception:
        return random.choice(pool) if pool else "Mozilla/5.0"


def _spider_scan():
    """#91S: سکانەری ماڵپەڕەکان — دۆزینەوەی ئەوانەی نوێیان زیاد کردووە (مۆدێڵ/ endpoint)
       هەر ١٢ کاتژمێر — کام سەرچاوە model_id ی نوێی هەیە و ئێمە نەمانەوە"""
    found = []
    checks = [
        # (ناو، url، pat) — دۆزینەوەی مۆدێڵ لە model/list ەکان
        ("g4f", G4F_BASE + "/v1/models", None),
        ("duck", None, None),  # duck خۆی sync دەکات
    ]
    for nm, url, _ in checks:
        if not url:
            continue
        try:
            r = requests.get(url, headers={"User-Agent": _rand_ua()}, timeout=(8, 15))
            if r.status_code == 200:
                j = r.json() or {}
                ids = [m.get("id") for m in (j.get("data") or []) if m.get("id")]
                found.append((nm, len(ids)))
                _SPIDER["found"][nm] = {"n": len(ids), "t": time.time()}
        except Exception:
            pass
    if found:
        print(f"[SPIDER] 🔭 سکان: {found}", flush=True)
    return found


def _spider_daemon():
    """#91S: هەر ١٢ کاتژمێر — سکانی تەواوی ماڵپەڕەکان بۆ مۆدێڵی نوێ"""
    time.sleep(900)
    while True:
        try:
            _spider_scan()
        except Exception:
            pass
        time.sleep(43200)



def _shadow_watch_daemon():
    """#91T: چاودێری مۆدێڵە بەناوبانگەکان — ئەگەر مۆدێڵێک زۆر داواکاری هەبوو و تک-سەرچاوە بوو → ڕاپۆرت + failover تایبەت"""
    import threading as _th
    _pop = {}
    time.sleep(600)
    while True:
        try:
            # MODEL_SOURCES — مۆدێڵی تک-سەرچاوە = مەترسی
            risky = [k for k, v in MODEL_SOURCES.items() if len(v) == 1]
            if risky:
                # #91T+: بۆ هەر مۆدێڵی تک — خێزانەکەی بدۆزە و fallback ی خێزانی پشتڕاست بکە
                fams = {}
                for k in risky:
                    fam = _model_family(k)
                    if fam:
                        fams.setdefault(fam, []).append(k)
                big = {f: len(v) for f, v in fams.items() if len(v) >= 3}
                print(f"[SHADOW] ⚠️ {len(risky)} تک-سەرچاوە | خێزانە گەورەکان: {big or '—'}", flush=True)
            # گەرمترین مۆدێڵەکان لە کاش
            hot = sorted(_ANS_CACHE.items(), key=lambda x: x[1][0], reverse=True)[:5]
            if hot:
                pass  # بێدەنگ — تەنها کاتێک مەترسی ڕاپۆرت
        except Exception:
            pass
        time.sleep(3600)



# ═══════════ #91ST: STEALTH — نەناسینەوەی کراک ═══════════
# ١) TLS fingerprint بە curl_cffi — وەک وێبگەڕی ڕاستەقینە
_STEALTH_TLS = {"enabled": True, "n": 0}
try:
    from curl_cffi import requests as _cf
    _STEALTH_TLS["lib"] = _cf
except Exception:
    _STEALTH_TLS["lib"] = None

_CF_IMPERSONATE = ["chrome124", "chrome120", "safari17_0", "edge101", "safari15_5"]


def stealth_get(url, **kw):
    """#91ST: GET بە TLS ی وێبگەڕ — دژی TLS-fingerprinting (Cloudflare/Akamai)"""
    lib = _STEALTH_TLS.get("lib")
    if lib and _STEALTH_TLS.get("enabled"):
        try:
            _STEALTH_TLS["n"] += 1
            r = lib.get(url, impersonate=random.choice(_CF_IMPERSONATE),
                        headers={"User-Agent": _rand_ua()}, timeout=kw.pop("timeout", (8, 16)),
                        proxies=kw.pop("proxies", None))
            return r
        except Exception:
            pass
    return requests.get(url, headers={"User-Agent": _rand_ua()}, timeout=kw.pop("timeout", (8, 16)), **kw)


def stealth_post(url, **kw):
    """#91ST: POST بە TLS ی وێبگەڕ"""
    lib = _STEALTH_TLS.get("lib")
    if lib and _STEALTH_TLS.get("enabled"):
        try:
            _STEALTH_TLS["n"] += 1
            r = lib.post(url, impersonate=random.choice(_CF_IMPERSONATE),
                         headers={"User-Agent": _rand_ua()}, timeout=kw.pop("timeout", (8, 20)),
                         proxies=kw.pop("proxies", None), **kw)
            return r
        except Exception:
            pass
    return requests.post(url, headers={"User-Agent": _rand_ua()}, timeout=kw.pop("timeout", (8, 20)), **kw)


# ٢) Session-Pool — سێشنی گەرم بۆ هەر دۆمەین (کوکی+warm)
_SESSION_POOL = {}
_SESS_LK = threading.Lock()


def _pool_sess(dom):
    """#91ST: سێشنی گەرم بۆ دۆمەین — کوکییەکان دەمێننەوە = بەکارهێنەری گەڕاوە"""
    s = _SESSION_POOL.get(dom)
    if not s:
        # #91F4: سنووری پۆڵ — 40 دۆمەین (memory guard)
        if len(_SESSION_POOL) > 40:
            _SESSION_POOL.pop(next(iter(_SESSION_POOL)), None)
        s = requests.Session()
        s.headers.update({"User-Agent": _rand_ua(),
                          "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.8", "en;q=0.7"]),
                          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"})
        _SESSION_POOL[dom] = s
    return s


# ٣) جیتر — کاتی هەڕەمەکی نێوان داواکارییەکان (پaternی مرۆیی)
def _human_delay():
    """#91ST: پاوزەی مرۆیی — 0.1 تا 0.8 چرکە هەڕەمەکی"""
    time.sleep(random.uniform(0.1, 0.8))


# ═══════════ /test — تاقیکردنەوەی مۆدێڵ بۆ ئەدمین ═══════════
def _admin_test_model(chat_id, model_ref):
    """تاقیکردنەوەی تەواوی مۆدێڵ — سەرچاوە + خێرایی + وەڵامی ڕاستەقینە"""
    t0 = time.time()
    reply(chat_id, f"🧪 <b>تاقیکردنەوە:</b> <code>{model_ref}</code> …")
    try:
        r = requests.post("http://127.0.0.1:8080/v1/chat/completions",
                          headers={"Authorization": "Bearer sk-yf-31c00f02aa9221b336d7b4a274bb375c",
                                   "Content-Type": "application/json"},
                          json={"model": model_ref,
                                "messages": [{"role": "user", "content": "تەنها بە یەک وشە وەڵام بدەوە: باشم"}]},
                          timeout=(10, 120))
        dt = time.time() - t0
        try:
            j = r.json()
        except Exception:
            j = {}
        if r.status_code == 200 and j.get("choices"):
            content = (j["choices"][0].get("message", {}) or {}).get("content", "")
            used = j.get("model") or model_ref
            ok = not leaks(content)
            emoji = "✅" if ok else "⚠️"
            reply(chat_id, f"{emoji} <b>ئەنجامی تاقیکردنەوە</b>\n"
                          f"📤 داواکاری: <code>{model_ref}</code>\n"
                          f"📥 وەڵام: <code>{str(content)[:60]}</code>\n"
                          f"⏱ خێرایی: {dt:.1f} چرکە\n"
                          f"🔌 سەرچاوەی بەکارهێنراو: <code>{used}</code>\n"
                          f"🛡 پاک (بێ لێک‌دوانەوە): {'بەڵێ ✅' if ok else 'نەخێر ⚠️'}")
        else:
            err = str(j.get("error") or r.text)[:80]
            reply(chat_id, f"❌ <b>شکستی هێنا</b> ({dt:.1f}s)\n⚠️ {err}")
    except Exception as e:
        reply(chat_id, f"❌ <b>هەڵە:</b> {str(e)[:80]}")



# ═══════════ #91HK: AI-HACKER — کراکەری زیرەکی خۆکار ═══════════
_HK_ST = {"routes": {}, "t": 0.0, "wins": 0, "tries": 0}


def _hk_try_routes(kind, url, method="GET", **kw):
    """#91HK: ڕێگای جیاواز بۆ هەمان ئامانج — وەک هاکەری ڕاستەقینە:
       1) ڕاستەوخۆ  2) curl_cffi impersonate  3) پرۆکسی  4) mobile UA  5) curl_cffi + پرۆکسی"""
    routes = []
    lib = _STEALTH_TLS.get("lib")
    # ڕێگای ١: ڕاستەوخۆ
    routes.append(("direct", lambda: requests.request(method, url, timeout=(8, 20), **kw)))
    # ڕێگای ٢: TLS
    if lib:
        routes.append(("tls", lambda: lib.request(method, url, impersonate=random.choice(_CF_IMPERSONATE),
                                                  timeout=(8, 20), **kw)))
    # ڕێگای ٣: پرۆکسی
    def _via_proxy():
        pl = _proxy_get(2)
        if not pl:
            raise EMError("no proxy")
        px = random.choice(pl)
        return requests.request(method, url, proxies={"http": px, "https": px}, timeout=(10, 25), **kw)
    routes.append(("proxy", _via_proxy))
    # ڕێگای ٤: mobile UA + TLS
    if lib:
        def _mob():
            mob = [u for u in _UA_POOL if "Mobile" in u or "Android" in u or "iPhone" in u]
            h = dict(kw.get("headers") or {})  # #91A5: pop ❌ — kw ی ڕەسەن تێناگۆڕین
            h["User-Agent"] = random.choice(mob)
            return lib.request(method, url, impersonate=random.choice(["safari15_5", "chrome120"]),
                               headers=h, timeout=(8, 20), **kw)
        routes.append(("mobile-tls", _mob))
    # ڕێگای ٥: TLS + پرۆکسی
    if lib:
        def _tls_px():
            pl = _proxy_get(2)
            if not pl:
                raise EMError("no proxy")
            px = random.choice(pl)
            return lib.request(method, url, impersonate=random.choice(_CF_IMPERSONATE),
                               proxies={"http": px, "https": px}, timeout=(10, 30), **kw)
        routes.append(("tls-proxy", _tls_px))
    # تاقیکردنەوەی ڕیزبەندی — لە کۆتایی: چی کار دەکات بیر دەکرێتەوە (route-memoization)
    prev = _HK_ST["routes"].get(dom_of := url.split("/")[2] if "://" in url else url)
    if prev:
        routes.sort(key=lambda x: 0 if x[0] == prev else 1)
    last = None
    for nm, fn in routes:
        try:
            _HK_ST["tries"] += 1
            r = fn()
            if r.status_code < 500:
                _HK_ST["wins"] += 1
                # #91A7: سنووری بیرگە — زۆرترین 200 دۆمەین
                if len(_HK_ST["routes"]) > 200:
                    _HK_ST["routes"].pop(next(iter(_HK_ST["routes"])), None)
                _HK_ST["routes"][url.split("/")[2] if "://" in url else url] = nm
                return r
            last = EMError(f"{nm}: HTTP{r.status_code}")
        except Exception as e:
            last = e
    raise last or EMError("hk: هەموو ڕێگاکان")


def _hk_stats():
    """ئاماری هاکەر"""
    return {"tries": _HK_ST["tries"], "wins": _HK_ST["wins"],
            "routes": dict(list(_HK_ST["routes"].items())[:6])}



# ══════════ Alle-AI (alle-ai.com) — §2.34 — Laravel API + Reverb WS ══════════
ALLE_API = "https://api.alle-ai.com/api/v1"
ALLE_WSS = "wss://api.alle-ai.com/app/pb1ry0ntlug7dm2fga0s?protocol=7&client=js&version=8.4.0-1reverb&flash=false"
ALLE_AUTH_EP = "https://api.alle-ai.com/broadcasting/auth"
ALLE_ACC_FILE = os.path.join(DATA_DIR, "alle_accounts.json")
ALLE_ST = {"accounts": [], "idx": 0, "limits": {}}
ALLE_LOCK = threading.Lock()
_ALLE_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"


def _alle_load_acc():
    d = _json_load_safe(ALLE_ACC_FILE) or {}
    ALLE_ST["accounts"] = d.get("accounts") or []
    ALLE_ST["idx"] = int(d.get("idx") or 0)
    ALLE_ST["limits"] = d.get("limits") or {}


def _alle_save_acc():
    _json_save(ALLE_ACC_FILE, {"accounts": ALLE_ST.get("accounts") or [],
                               "idx": ALLE_ST.get("idx") or 0,
                               "limits": ALLE_ST.get("limits") or {}})

_ALLE_SEED = [{"email": "fipexa5604@dreameg.com", "password": "fipexa5604@dreameg.comA",
               "conv": "6c073793-a0a0-4648-b29a-ea2fb989b11e", "pos": 6}]


def _alle_seed():
    if not (ALLE_ST.get("accounts") or []):
        ALLE_ST["accounts"] = [dict(a) for a in _ALLE_SEED]
        _alle_save_acc()
        print(f"[ALLE] ئەکاونتی سەرەتایی ✅ {ALLE_ST['accounts'][0]['email']}", flush=True)


_alle_load_acc()
_alle_seed()


def alle_servers():
    """٩ مۆدێلی چاتی Alle (هەموو خۆڕایی — خێزانی Gemini)"""
    out = []
    for uid, nm in (("gemini-3-7-flash", "Gemini 3.7 Flash"), ("gemini-3-6-flash", "Gemini 3.6 Flash"),
                    ("gemini-3-5-flash", "Gemini 3.5 Flash"), ("gemini-3-flash", "Gemini 3 Flash"),
                    ("gemini-3-1-pro", "Gemini 3.1 Pro"), ("gemini-3-1-flash-lite", "Gemini 3.1 Flash Lite"),
                    ("gemini-2-5-pro", "Gemini 2.5 Pro"), ("gemini-2-5-flash", "Gemini 2.5 Flash"),
                    ("gemini-2-5-flash-lite", "Gemini 2.5 Flash Lite")):
        out.append({"id": f"alle-{uid}", "name": f"{nm} (Alle)",
                    "model_id": uid, "kind": "alle"})
    return out


def _alle_hdrs(acc):
    return {"User-Agent": acc.get("ua") or _ALLE_UA, "Accept": "application/json",
            "Authorization": "Bearer " + (acc.get("token") or ""),
            "Origin": "https://app.alle-ai.com", "Referer": "https://app.alle-ai.com/chat"}


def _alle_login(acc, force=False):
    """لۆگین — token ی Laravel (uid|hash) + uid بۆ کەناڵی WS"""
    if acc.get("token") and not force:
        return True
    r = requests.post(ALLE_API + "/login",
                      json={"email": acc["email"], "password": acc["password"]},
                      headers={"User-Agent": acc.get("ua") or _ALLE_UA, "Accept": "application/json",
                               "Content-Type": "application/json",
                               "Origin": "https://app.alle-ai.com", "Referer": "https://app.alle-ai.com/auth"},
                      timeout=(10, 30))
    d = r.json() or {}
    data = d.get("data") or {}
    if not d.get("status") or not data.get("token"):
        raise EMError(f"alle login: {str(d.get('message'))[:60]}")
    acc["token"] = data["token"]
    acc["uid"] = (data.get("user") or {}).get("id")
    _alle_save_acc()
    print(f"[ALLE] لۆگین ✅ {acc['email']} uid={acc.get('uid')}", flush=True)
    return True


def _alle_mark(acc, mkey, err):
    """#91Z-P ی ئەکاونتەکانی تر — لیمیت وەک CA: mkey هەمیشە، ستاری * تەنها بۆ ڕوونەکان"""
    lm = ALLE_ST.setdefault("limits", {}).setdefault(acc.get("email") or "?", {})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    lm[mkey] = today
    low = str(err).lower()
    if any(w in low for w in ("free message", "no free", "daily", "message limit", "limit reached", "monthly limit")):
        lm["*"] = today
    _alle_save_acc()


class _AlleLimit(Exception):
    pass


def _alle_ask(acc, model_id, text, timeout=110, mkey=""):
    """فڵۆوی تەواو: WS → auth → subscribe → create/prompt → ai-response → چانکەکان"""
    import websocket as _ws
    _alle_login(acc)
    hdrs = _alle_hdrs(acc)
    w = _ws.create_connection(ALLE_WSS, timeout=12,
                              header=["Origin: https://app.alle-ai.com",
                                      "User-Agent: " + (acc.get("ua") or _ALLE_UA)])
    try:
        hello = json.loads(w.recv())
        sid = (json.loads(hello.get("data") or "{}") or {}).get("socket_id")
        if not sid:
            raise EMError("alle: ws hello شکست")
        r = requests.post(ALLE_AUTH_EP, json={"socket_id": sid,
                                              "channel_name": f"private-App.Models.User.{acc.get('uid')}"},
                          headers=hdrs, timeout=(10, 20))
        au = (r.json() or {}).get("auth")
        if not au:
            raise EMError("alle: broadcasting/auth شکست")
        w.send(json.dumps({"event": "pusher:subscribe",
                           "data": {"auth": au, "channel": f"private-App.Models.User.{acc.get('uid')}"}}))
        pos = int(acc.get("pos") or 1)
        r = requests.post(ALLE_API + "/create/prompt",
                          json={"conversation": acc["conv"], "prompt": text, "position": [pos, pos],
                                "combine": False, "compare": False, "web_search": False},
                          headers={**hdrs, "Content-Type": "application/json"}, timeout=(10, 30))
        if r.status_code == 401:
            _alle_login(acc, force=True)
            hdrs = _alle_hdrs(acc)
            r = requests.post(ALLE_API + "/create/prompt",
                              json={"conversation": acc["conv"], "prompt": text, "position": [pos, pos],
                                    "combine": False, "compare": False, "web_search": False},
                              headers={**hdrs, "Content-Type": "application/json"}, timeout=(10, 30))
        if r.status_code != 200:
            raise EMError(f"alle: prompt {r.status_code} {r.text[:60]}")
        pid = (r.json() or {}).get("id")
        acc["pos"] = pos + 1
        _alle_save_acc()
        r = requests.post(ALLE_API + "/ai-response",
                          json={"conversation": acc["conv"], "model": model_id, "is_new": False,
                                "prompt": pid, "prev": [], "combine": False, "compare": False},
                          headers={**hdrs, "Content-Type": "application/json"}, timeout=(10, 30))
        if r.status_code == 429:
            raise _AlleLimit(f"alle ڕێژە: {r.text[:80]}")
        if r.status_code == 403:
            # Access Denied — لیمیت ی ئەکاونت یان مۆدێلی ڕێگەنەدراو
            raise _AlleLimit(f"alle 403: {(r.json() or {}).get('message', '')[:60]}")
        if r.status_code != 200:
            raise EMError(f"alle: ai-response {r.status_code} {r.text[:60]}")

        parts, t0 = [], time.time()
        w.settimeout(max(5, min(30, timeout - (time.time() - t0))))
        while time.time() - t0 < timeout:
            try:
                m = json.loads(w.recv())
            except _ws.WebSocketTimeoutException:
                break
            ev = m.get("event", "")
            if "ping" in ev or "pong" in ev or "subscription" in ev:
                continue
            dd = m.get("data", "{}")
            try:
                dd = json.loads(dd) if isinstance(dd, str) else dd
            except Exception:
                dd = {}
            if ev.endswith("chat.chunk"):
                parts.append(str(dd.get("chunk") if isinstance(dd, dict) else dd))
            elif ev.endswith("chat.stream.failed"):
                msg = str((dd or {}).get("error") or (dd or {}).get("message") or "failed")[:90]
                raise _AlleLimit(f"alle stream: {msg}") if any(
                    x in msg.lower() for x in ("limit", "quota", "credit", "free", "exceeded")) else EMError(f"alle: {msg}")
            elif ev.endswith("chat.stream.complete"):
                break
        ans = "".join(parts).strip()
        if not ans:
            raise EMError("alle: وەڵام بەتاڵ")
        return ans
    finally:
        try:
            w.close()
        except Exception:
            pass


def _alle_pick(mkey):
    """هەڵبژاردنی ئەکاونت — ئەوانەی لیمیتن بۆ ئەم مۆدێلە دەپەڕێت (وەک #91P2: دەگەڕێن، نەسڕدرێنەوە)"""
    accs = ALLE_ST.get("accounts") or []
    if not accs:
        return None
    today = time.strftime("%Y-%m-%d", time.gmtime())
    lim = ALLE_ST.get("limits") or {}
    n = len(accs)
    for i in range(n):
        a = accs[(ALLE_ST.get("idx", 0) + i) % n]
        L = lim.get(a.get("email") or "?") or {}
        if L.get("*") == today or L.get(mkey) == today:
            continue
        ALLE_ST["idx"] = (ALLE_ST.get("idx", 0) + i + 1) % n
        return a
    return None


def alle_chat(messages, model_id, timeout=110, depth=0):
    """چاتی alle-ai.com — WS streaming؛ لیمیت وەک ئەکاونتەکانی تر نیشانە دەکرێت (#91Z-P)"""
    mkey = f"alle-{model_id}"
    with ALLE_LOCK:
        acc = _alle_pick(model_id)
    if not acc:
        raise EMError("alle: هیچ ئەکاونتێکی بەردەست نییە (لیمیت؟)")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    rest = [m for m in messages if m.get("role") != "system"][-9:]
    if rest and rest[-1].get("role") == "user":
        last = rest.pop()
    else:
        last = {"role": "user", "content": "سلام"}
    tx = ""
    for m in rest[-7:]:
        who = "بەکارهێنەر" if m.get("role") == "user" else "وەڵام"
        tx += f"{who}: {str(m.get('content'))[:700]}\n"
    if sys_txt:
        tx = f"[ئاراستەی سیستەم: {sys_txt}]\n{tx}"
    tx += f"بەکارهێنەر: {last.get('content')}"
    try:
        return _alle_ask(acc, model_id, tx, timeout, mkey)
    except _AlleLimit as e:
        _alle_mark(acc, model_id, str(e))
        raise EMError(str(e))
    except EMError as e:
        s = str(e)
        if "401" in s and depth == 0:
            _alle_login(acc, force=True)
            return alle_chat(messages, model_id, timeout, depth=1)
        if any(x in s.lower() for x in ("limit", "quota", "credit", "exceeded", "free")) and depth == 0:
            _alle_mark(acc, model_id, s)
            with ALLE_LOCK:
                acc2 = _alle_pick(model_id)
            if acc2 and acc2 is not acc:
                return alle_chat(messages, model_id, timeout, depth=1)
        raise EMError(f"alle: {s[:80]}")


# ══════════ Piax (piax.org) — §2.35 — openrouter-پشتگیر + ئۆتۆ-ساینئەپ ══════════
PIA_API = "https://piax-api.piax.org"
PIA_ACC_FILE = os.path.join(DATA_DIR, "pia_accounts.json")
PIA_ST = {"accounts": [], "idx": 0, "limits": {}, "signups": {"date": "", "n": 0}, "next_num": 0}
PIA_LOCK = threading.Lock()
_PIA_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
# مۆدێلە فرییەکان — سکانکرا لایڤ (کۆدی لایڤ ٢٠٢٦-٠٩)
PIA_AGENTS = [("32", "gpt-4.1-nano", "GPT 4.1 Nano"),
              ("33", "o3-mini", "o3 Mini"),
              ("167", "deepseek-v3.2", "DeepSeek V3.2"),
              ("136", "glm-4.7", "GLM 4.7"),
              ("163", "kimi-k2.5", "Kimi K2.5"),
              ("175", "minimax-m3", "MiniMax M3")]


def _pia_load_acc():
    d = _json_load_safe(PIA_ACC_FILE) or {}
    PIA_ST["accounts"] = d.get("accounts") or []
    PIA_ST["idx"] = int(d.get("idx") or 0)
    PIA_ST["limits"] = d.get("limits") or {}
    PIA_ST["signups"] = d.get("signups") or {"date": "", "n": 0}
    PIA_ST["next_num"] = int(d.get("next_num") or 0)


def _pia_save_acc():
    _json_save(PIA_ACC_FILE, {"accounts": PIA_ST.get("accounts") or [], "idx": PIA_ST.get("idx") or 0,
                              "limits": PIA_ST.get("limits") or {},
                              "signups": PIA_ST.get("signups") or {"date": "", "n": 0},
                              "next_num": PIA_ST.get("next_num") or 0})


_PIA_SEED = [{"email": "vemim87080@dreameg.com",
              "token": "eyJhbGciOiJIUzI1NiJ9.eyJqdGkiOiIyMjU5NjIzNS1iZWFmLTQwYTQtYjlmOS05YjU0OTNiOGUzOWEiLCJpYXQiOjE3ODk5NTg0NDEsImFjY291bnRJZCI6IjExNzc2ODA3MzMxMTI2MzMzNDQiLCJ0IjoxNzg5OTU4NDQxLCJjaGFubmVsIjoiZW1haWwiLCJ1c2VySWQiOiIxMTc3NjgwNzI4NDY1MzQ0NTEyIn0.vzExTVJAWIkr2W53hRT_Ue_yPSPwq3-6obGRHUI9WL0"}]


def _pia_seed():
    accs = PIA_ST.get("accounts") or []
    have = {a.get("email") for a in accs}
    changed = False
    for a in _PIA_SEED:
        if a["email"] not in have:
            PIA_ST.setdefault("accounts", []).append(dict(a))
            changed = True
    if changed:
        _pia_save_acc()
        print(f"[PIA] ئەکاونتی سەرەتایی ✅", flush=True)


_pia_load_acc()
_pia_seed()


def pia_servers():
    out = []
    for aid, model, nm in PIA_AGENTS:
        out.append({"id": f"pia-{model}", "name": f"{nm} (Piax)",
                    "model_id": aid, "kind": "pia"})
    return out


def _pia_pick(agent_id):
    accs = PIA_ST.get("accounts") or []
    if not accs:
        return None
    today = time.strftime("%Y-%m-%d", time.gmtime())
    lim = PIA_ST.get("limits") or {}
    n = len(accs)
    for i in range(n):
        a = accs[(PIA_ST.get("idx", 0) + i) % n]
        L = lim.get(a.get("email") or "?") or {}
        if L.get("*") == today or L.get(agent_id) == today:
            continue
        PIA_ST["idx"] = (PIA_ST.get("idx", 0) + i + 1) % n
        return a
    return None


def _pia_mark(acc, agent_id, err):
    lm = PIA_ST.setdefault("limits", {}).setdefault(acc.get("email") or "?", {})
    today = time.strftime("%Y-%m-%d", time.gmtime())
    lm[agent_id] = today
    low = str(err).lower()
    if any(w in low for w in ("subscription", "upgrade", "quota", "limit", "frequent", "credit", "balance", "exceed")):
        lm["*"] = today
        _replace_dead_soon("pia")  # #94U24: مردنی گشتی → نوێ لە جێی
    _pia_save_acc()


class _PiaLimit(Exception):
    pass


def pia_chat(messages, agent_id, timeout=110, depth=0):
    """چاتی piax — SSE (openrouter-chunks)؛ sys دەفڕێتە ناو پرۆمپت؛ ئەکاونت-ڕۆتەیشن + لیمیت"""
    with PIA_LOCK:
        acc = _pia_pick(agent_id)
    if not acc:
        raise EMError("piax: هیچ ئەکاونتێکی بەردەست نییە")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    rest = [m for m in messages if m.get("role") != "system"][-8:]
    q = ""
    for m in rest[:-1]:
        who = "بەکارهێنەر" if m.get("role") == "user" else "وەڵام"
        q += f"{who}: {str(m.get('content'))[:600]}\n"
    last = rest[-1] if rest else {"role": "user", "content": "سلام"}
    if sys_txt:
        q = f"[ئاراستەی سیستەم: {sys_txt}]\n{q}"
    q += f"بەکارهێنەر: {last.get('content')}"
    try:
        r = requests.post(PIA_API + "/ai-api/ai/agent/chatStream",
                          json={"device": {"deviceType": "pc", "osPlatform": "web"},
                                "agentId": str(agent_id), "query": q[:8000],
                                "conversationId": "", "parentMessageId": "", "files": []},
                          headers={"Accept-Language": "en", "User-Agent": _PIA_UA,
                                   "Authorization": acc.get("token") or "",
                                   "Content-Type": "application/json",
                                   "Origin": "https://www.piax.org",
                                   "Referer": "https://www.piax.org/chat"},
                          timeout=(12, timeout), stream=True)
        if r.status_code == 401:
            _pia_mark(acc, agent_id, "auth")
            raise EMError("piax: توکن مردووە")
        parts = []
        for raw in r.iter_lines(chunk_size=None):
            if not raw:
                continue
            ln = raw.decode("utf-8", "ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
            if not ln.startswith("data:"):
                continue
            payload = ln[5:].strip()
            if payload == "[DONE]":
                break
            try:
                d = json.loads(payload)
            except Exception:
                continue
            if d.get("event") == "error":
                msg = str(d.get("answer") or d.get("message") or "error")[:90]
                if any(x in msg.lower() for x in ("subscription", "upgrade", "quota", "limit", "frequent", "credit")):
                    raise _PiaLimit(msg)
                raise EMError(f"piax: {msg}")
            ch = (d.get("choices") or [{}])[0]
            delta = (ch.get("delta") or {}).get("content") or ch.get("text") or ""
            if delta:
                parts.append(delta)
        ans = "".join(parts).strip()
        if not ans:
            raise EMError("piax: وەڵام بەتاڵ")
        return ans
    except _PiaLimit as e:
        _pia_mark(acc, agent_id, str(e))
        raise EMError(f"piax: {e}")
    except EMError:
        raise
    except Exception as e:
        s = str(e)
        if any(x in s.lower() for x in ("limit", "quota", "frequent", "subscription")) and depth == 0:
            _pia_mark(acc, agent_id, s)
            raise EMError(f"piax: {s[:80]}")
        raise EMError(f"piax: {s[:80]}")


def _pia_signup_new():
    """#91PIA-AUTO: ئەکاونتی نوێی piax — temp-mail.org + کۆد + لۆگین (هەموو خۆکارانە لە VM)"""
    try:
        today = time.strftime("%Y-%m-%d", time.gmtime())
        sg = PIA_ST.get("signups") or {"date": "", "n": 0}
        if sg.get("date") != today:
            sg = {"date": today, "n": 0}
        if len(PIA_ST.get("accounts") or []) >= 60:  # #94U32: 12→60
            return None
        if not _sg_reserve(PIA_ST, 30, today, PIA_LOCK):  # #94U23 بودجە لەژێر لۆک؛ #94U32: 6→30
            return None
        s = requests.Session()
        s.headers.update({"User-Agent": _rand_ua(), "Accept": "application/json",
                          "Origin": "https://temp-mail.org", "Referer": "https://temp-mail.org/"})
        r = s.post("https://web2.temp-mail.org/mailbox", timeout=(10, 30))
        mb = r.json() or {}
        email, jwt = mb.get("mailbox"), mb.get("token")
        if not email or not jwt:
            print(f"[PIA-SIGNUP] mailbox fail: {r.status_code}", flush=True)
            return None
        s2 = requests.Session()
        s2.headers.update({"User-Agent": _rand_ua(), "Accept-Language": "en",
                           "Origin": "https://www.piax.org", "Referer": "https://www.piax.org/"})
        r2 = s2.post(PIA_API + "/user-api/user/sendEmailVerifyCode",
                     json={"channel": "pia", "email": email, "device": {"deviceType": "pc", "osPlatform": "web"}},
                     timeout=(10, 40))
        if (r2.json() or {}).get("code") != 1:
            print(f"[PIA-SIGNUP] sendCode fail: {r2.text[:80]}", flush=True)
            return None
        code = None
        mh = {"Authorization": "Bearer " + jwt, "Accept": "application/json"}
        for _ in range(16):
            time.sleep(6)
            try:
                r3 = s.get("https://web2.temp-mail.org/messages", headers=mh, timeout=(10, 25))
                msgs = (r3.json() or {}).get("messages") or []
            except Exception:
                continue
            if msgs:
                mid = msgs[0].get("_id")
                if not mid:
                    continue
                try:
                    r4 = s.get(f"https://web2.temp-mail.org/messages/{mid}", headers=mh, timeout=(10, 25))
                    nums = re.findall(r"\b(\d{4,8})\b", r4.text or "")
                except Exception:
                    continue
                if nums:
                    code = nums[0]
                    break
        if not code:
            print(f"[PIA-SIGNUP] کۆد نەگەیشت {email}", flush=True)
            return None
        r5 = s2.post(PIA_API + "/user-api/user/emailLogin",
                     json={"email": email, "code": code, "channel": "pia"}, timeout=(10, 40))
        d5 = r5.json() or {}
        if not d5.get("token"):
            print(f"[PIA-SIGNUP] login fail: {r5.text[:100]}", flush=True)
            return None
        with PIA_LOCK:
            PIA_ST.setdefault("accounts", []).append({"email": email, "token": d5["token"]})
            _pia_save_acc()
        print(f"[PIA-SIGNUP] ئەکاونتی نوێ ✅ {email}", flush=True)
        return email
    except Exception as e:
        print(f"[PIA-SIGNUP] {str(e)[:80]}", flush=True)
        return None


def _pia_signup_daemon():
    """هەر ٦ کاتژمێر — ئەگەر هەموو ئەکاونتەکان لیمیت بوون یان کەم بوون → نوێ دروست دەکات"""
    while True:
        try:
            time.sleep(3600 * 2)
            accs = PIA_ST.get("accounts") or []
            today = time.strftime("%Y-%m-%d", time.gmtime())
            lim = PIA_ST.get("limits") or {}
            alive = [a for a in accs if (lim.get(a.get("email") or "?") or {}).get("*") != today]
            if len(alive) < 6:  # #94U32: 2→6
                _pia_signup_new()
        except Exception:
            time.sleep(300)


# ══════════ Chat-box.ai (cx-) — §2.36 — فڵانت‌پرینت+ads-کەناڵ — بێ ئیمێڵ، تەنها API ══════════
# کراک: POST /auth/fingerprint + X-Device-Fingerprint + x-user-origin-source: ads
#   → ئەکاونتی دەستبەجێ (originChannel=ads) → چاتی فڕی "AI Chat" (best-available) — SSE
# توکن ١٥ خولەک — /auth/refresh بە refreshToken؛ ئەکاونت=١ داواکاری — بێسنوور
CBOX_API = "https://chat-box.ai/app/api/v1"
CBOX_ACC_FILE = os.path.join(DATA_DIR, "cbox_accounts.json")
CBOX_ST = {"accounts": [], "idx": 0, "signups": {"date": "", "n": 0}}
CBOX_LOCK = threading.Lock()
_CBOX_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
# مۆدێڵی فڕی — "AI Chat" (subtitle: Best available model) — ٢٨ پارەدارەکە سرێڵن لە سێرڤەر (isPaidUser gate)
CBOX_FREE_ID = "88cc1733-9cf1-4652-a7be-f9a6dbe01737"
# دوو مۆدێڵ: Text + WebSearch (وێبسێڕچ لەسەر فری کار دەکات — زانیاری نوێ)
CBOX_MODELS = [("aichat", "AI Chat", "Chatbox AI"), ("websearch", "AI WebSearch", "Chatbox WebSearch")]
CBOX_DAY_CAP = 100  # چات/ڕۆژ بۆ هەر ئەکاونتێک — خۆپاراستن (١ داواکاری=١ ئەکاونت بۆ دروستکردن)


def _cbox_load():
    d = _json_load_safe(CBOX_ACC_FILE) or {}
    CBOX_ST["accounts"] = d.get("accounts") or []
    CBOX_ST["idx"] = int(d.get("idx") or 0)
    CBOX_ST["signups"] = d.get("signups") or {"date": "", "n": 0}


def _cbox_save():
    _json_save(CBOX_ACC_FILE, {"accounts": CBOX_ST.get("accounts") or [],
                               "idx": CBOX_ST.get("idx") or 0,
                               "signups": CBOX_ST.get("signups") or {"date": "", "n": 0}})


def _cbox_new_account():
    """١ داواکاری — ئەکاونتی نوێی ads-کەناڵ (بێ ئیمێڵ، بێ OTP، بێ playwright)"""
    try:
        fp = str(uuid.uuid4())
        r = requests.post(CBOX_API + "/auth/fingerprint", json={},
                          headers={"User-Agent": _CBOX_UA, "Accept": "application/json",
                                   "Origin": "https://chat-box.ai", "Referer": "https://chat-box.ai/app/en",
                                   "X-Device-Fingerprint": fp, "x-device-fingerprint": fp,
                                   "x-user-origin-source": "ads", "Content-Type": "application/json"},
                          timeout=(12, 40))
        if r.status_code not in (200, 201):
            print(f"[CX] fingerprint fail: {r.status_code}", flush=True)
            return None
        d = r.json() or {}
        at, rt = d.get("accessToken"), d.get("refreshToken")
        if not at:
            return None
        today = time.strftime("%Y-%m-%d", time.gmtime())
        acc = {"fp": fp, "at": at, "rt": rt, "day": today, "n": 0, "dead": 0}
        with CBOX_LOCK:
            CBOX_ST.setdefault("accounts", []).append(acc)
            sg = CBOX_ST.get("signups") or {"date": "", "n": 0}
            if sg.get("date") != today:
                sg = {"date": today, "n": 0}
            sg["n"] = sg.get("n", 0) + 1
            CBOX_ST["signups"] = sg
            _cbox_save()
        return acc
    except Exception as e:
        print(f"[CX] new-acct: {str(e)[:80]}", flush=True)
        return None


def _cbox_refresh(acc):
    """توکنی نوێ بە refreshToken — ئەگەر شکست → ئەکاونت مردوو"""
    try:
        r = requests.post(CBOX_API + "/auth/refresh", json={"refreshToken": acc.get("rt") or ""},
                          headers={"User-Agent": _CBOX_UA, "Accept": "application/json",
                                   "Origin": "https://chat-box.ai", "Referer": "https://chat-box.ai/app/en",
                                   "X-Device-Fingerprint": acc.get("fp") or "", "Content-Type": "application/json"},
                          timeout=(12, 40))
        if r.status_code in (200, 201):
            d = r.json() or {}
            if d.get("accessToken"):
                acc["at"] = d["accessToken"]
                if d.get("refreshToken"):
                    acc["rt"] = d["refreshToken"]
                acc["dead"] = 0
                with CBOX_LOCK:
                    _cbox_save()
                return True
    except Exception:
        pass
    acc["dead"] = 1
    return False


def _cbox_alive():
    today = time.strftime("%Y-%m-%d", time.gmtime())
    out = []
    for a in (CBOX_ST.get("accounts") or []):
        if a.get("dead"):
            continue
        if a.get("day") == today and int(a.get("n") or 0) >= CBOX_DAY_CAP:
            continue
        out.append(a)
    return out


def _cbox_pick():
    accs = _cbox_alive()
    if not accs:
        acc = _cbox_new_account()
        return acc
    n = len(accs)
    for i in range(n):
        a = accs[(CBOX_ST.get("idx", 0) + i) % n]
        CBOX_ST["idx"] = (CBOX_ST.get("idx", 0) + i + 1) % n
        return a
    return accs[0]


def cbox_servers():
    out = []
    for key, model, nm in CBOX_MODELS:
        out.append({"id": f"cx-{key}", "name": f"{nm} (Chatbox)", "model_id": key, "kind": "cbox"})
    return out


class _CxLimit(Exception):
    pass


def cbox_chat(messages, model_key="aichat", timeout=110, depth=0):
    """چاتی chat-box.ai — SSE (chunk/complete)؛ مولتی‌پارت؛ ئەکاونت-ڕۆتەیشن + refresh + دروستکردنی خۆکار"""
    acc = _cbox_pick()
    if not acc:
        raise EMError("cx: ئەکاونت نەدروست بوو")
    sys_txt = " ".join(m["content"] for m in messages if m.get("role") == "system")[:32000]
    rest = [m for m in messages if m.get("role") != "system"][-8:]
    q = ""
    for m in rest[:-1]:
        who = "بەکارهێنەر" if m.get("role") == "user" else "وەڵام"
        q += f"{who}: {str(m.get('content'))[:600]}\n"
    last = rest[-1] if rest else {"role": "user", "content": "سلام"}
    if sys_txt:
        q = f"[ئاراستەی سیستەم: {sys_txt}]\n{q}"
    q += f"بەکارهێنەر: {last.get('content')}"
    mid = CBOX_FREE_ID
    for _ in range(2):
        parts = []
        final_msg = ""
        try:
            rt = "WebSearch" if str(model_key) == "websearch" else "Text"
            files = [("message", (None, q[:8000])),
                     ("modelId", (None, mid)),
                     ("roomType", (None, rt))]
            r = requests.post(CBOX_API + "/chat/stream", files=files,
                              headers={"User-Agent": _CBOX_UA, "Accept": "text/event-stream",
                                       "Origin": "https://chat-box.ai", "Referer": "https://chat-box.ai/app/en",
                                       "X-Device-Fingerprint": acc.get("fp") or "",
                                       "x-device-fingerprint": acc.get("fp") or "",
                                       "x-user-origin-source": "ads",
                                       "Authorization": "Bearer " + (acc.get("at") or "")},
                              timeout=(12, timeout), stream=True)
            if r.status_code == 401:
                if _cbox_refresh(acc):
                    continue
                acc["dead"] = 1
                with CBOX_LOCK:
                    _cbox_save()
                na = _cbox_new_account()
                if na and depth == 0:
                    return cbox_chat(messages, model_key, timeout, depth=1)
                raise EMError("cx: توکن مردووە")
            if r.status_code in (403, 429):
                body = ""
                try:
                    body = r.text[:300]
                except Exception:
                    pass
                # FEATURE_NOT_SUPPORTED → ئەکاونت ناکات → نوێ
                acc["dead"] = 1
                with CBOX_LOCK:
                    _cbox_save()
                na = _cbox_new_account()
                if na and depth == 0:
                    return cbox_chat(messages, model_key, timeout, depth=1)
                raise EMError(f"cx: gate {r.status_code} {body[:80]}")
            err_evt = None
            for raw in r.iter_lines(chunk_size=None):
                if not raw:
                    continue
                ln = raw.decode("utf-8", "ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
                if not ln.startswith("data:"):
                    continue
                payload = ln[5:].strip()
                try:
                    d = json.loads(payload)
                except Exception:
                    continue
                if isinstance(d, dict) and d.get("error"):
                    err_evt = str((d.get("error") or {}).get("errors", [{}])[0].get("type") if (d.get("error") or {}).get("errors") else (d.get("error") or {}).get("message") or "error")
                    break
                ev = (d.get("event") or {}) if isinstance(d, dict) else {}
                et = ev.get("type")
                if et == "chunk" and ev.get("content"):
                    parts.append(str(ev["content"]))
                elif et == "complete":
                    fm = ev.get("fullMessage") or {}
                    final_msg = str(fm.get("message") or "")
                    ws = fm.get("webSearch") or {}
                    _wsl = ws.get("links") or []
                    if _wsl:
                        try:
                            _src = "\n".join(f"🔗 {l.get('title') or 'source'}: {l.get('url') or l}" for l in _wsl[:4] if l)
                            if _src:
                                final_msg = (final_msg or "") + "\n" + _src
                        except Exception:
                            pass
                elif et == "error":
                    err_evt = str(ev.get("error") or ev.get("message") or "stream error")
                    break
            if err_evt:
                low = err_evt.lower()
                if any(x in low for x in ("free_tier", "limit", "quota", "usage", "subscription", "not_supported")):
                    acc["dead"] = 1
                    with CBOX_LOCK:
                        _cbox_save()
                    na = _cbox_new_account()
                    if na and depth == 0:
                        return cbox_chat(messages, model_key, timeout, depth=1)
                    raise _CxLimit(err_evt[:90])
                # #94U42: هەڵەی کاتی سێرڤەر (SERVER_ERROR) → یەک دووبارە بە ئەکاونتی نوێ، نەک ❌ یەکسەر
                if depth == 0:
                    try:
                        na = _cbox_new_account()
                    except Exception:
                        na = None
                    if na:
                        return cbox_chat(messages, model_key, timeout, depth=1)
                raise EMError(f"cx: {err_evt[:90]}")
            ans = (final_msg or "".join(parts)).strip()
            if not ans:
                raise EMError("cx: وەڵام بەتاڵ")
            # سەرکەوتوو — ژماردن
            today = time.strftime("%Y-%m-%d", time.gmtime())
            if acc.get("day") != today:
                acc["day"], acc["n"] = today, 0
            acc["n"] = int(acc.get("n") or 0) + 1
            with CBOX_LOCK:
                _cbox_save()
            return ans
        except _CxLimit as e:
            raise EMError(f"cx: {e}")
        except EMError:
            raise
        except Exception as e:
            s = str(e)
            if depth == 0:
                na = _cbox_new_account()
                if na:
                    return cbox_chat(messages, model_key, timeout, depth=1)
            raise EMError(f"cx: {s[:80]}")
    raise EMError("cx: دووبارە بوونەوە سەرکەوتوو نەبوو")


def _cbox_seed():
    """لە بووت — ئەگەر حەوز بەتاڵە → ٢ ئەکاونت"""
    try:
        if not _cbox_alive():
            for _ in range(2):
                _cbox_new_account()
            print(f"[CX] حەوز: {len(_cbox_alive())} ئەکاونتی زیندوو", flush=True)
    except Exception as e:
        print(f"[CX] seed: {str(e)[:70]}", flush=True)


def _memwatch_daemon():
    """#94U10+#94U15: چاودێری بیرگە — سنووری ڕێژەیی لە کۆی RAM (بۆ 1GB: GC لە 800MB، ڕیستارت لە 920MB)"""
    import gc as _gc
    try:
        with open("/proc/meminfo") as _f:
            _mt = next(int(_l.split()[1]) for _l in _f if _l.startswith("MemTotal:"))
        _GC_KB, _EXIT_KB = int(_mt * 0.78), int(_mt * 0.90)
    except Exception:
        _GC_KB, _EXIT_KB = 800 * 1024, 920 * 1024
    while True:
        try:
            time.sleep(120)
            rss = 0
            try:
                with open("/proc/self/status") as f:
                    for ln in f:
                        if ln.startswith("VmRSS:"):
                            rss = int(ln.split()[1])  # kB
                            break
            except Exception:
                continue
            mb = rss // 1024
            if rss > _EXIT_KB:
                print(f"[MEM] 🚨 {mb}MB — خۆ-ڕیستارت", flush=True)
                try:
                    import requests as _rq
                    _tok = re.search(r"bot(\d+:[A-Za-z0-9_\-]+)", open(__file__, encoding="utf-8", errors="ignore").read())
                    if _tok:
                        for _c in (8381536661, 7585287282):
                            _rq.post(f"https://api.telegram.org/bot{_tok.group(1)}/sendMessage",
                                     json={"chat_id": _c, "text": f"⚠️ بیرگە {mb}MB — خۆ-ڕیستارت ئەنجامدرا"}, timeout=10)
                except Exception:
                    pass
                os._exit(1)  # fly reboots the container
            elif rss > _GC_KB:
                _gc.collect()
                print(f"[MEM] ⚠️ {mb}MB — GC کرایەوە", flush=True)
        except Exception:
            time.sleep(60)


def _api_selfping_daemon():
    """#94U15 ANTI-CRASH: ئەگەر /health بێوەڵام بوو ٣ جار لەسەریەک → traceback + ڕیستارتی خۆکار"""
    _fails = 0
    time.sleep(150)
    while True:
        try:
            _port = int(os.environ.get("API_PORT", 8080))
            _r = requests.get(f"http://127.0.0.1:{_port}/health", timeout=10)
            _ok = _r.status_code == 200
        except Exception:
            _ok = False
        if _ok:
            _fails = 0
        else:
            _fails += 1
            print(f"[SELF-PING] ⚠️ /health بێوەڵام ({_fails}/3)", flush=True)
            if _fails >= 3:
                print("[SELF-PING] 💀 API وەستاوە — traceback + ڕیستارت", flush=True)
                try:
                    faulthandler.dump_traceback()
                except Exception:
                    pass
                os._exit(1)
        time.sleep(30)


def _prewarm_daemon():
    """#94U8: pre-warm — هەر ٤٥ خولەک توکنی هەر سێ حەوز نوێ بکەرەوە
    تا یەکەم داواکاری بەکارهێنەر چاوەڕوانی fetch-token نەبێت (خێرایی-یەکەم-توکن)"""
    while True:
        try:
            time.sleep(2700)
            try:
                _ca_token()
            except Exception:
                pass
            try:
                _cb_token()
            except Exception:
                pass
        except Exception:
            time.sleep(60)


def _cbox_daemon():
    """#94U8: هەر ٣٠ خولەک — تا ١٠ ئەکاونتی زیندوو (لۆد + خێرایی)"""
    while True:
        try:
            time.sleep(1800)
            if len(_cbox_alive()) < 10:
                _cbox_new_account()
        except Exception:
            time.sleep(300)


def main():
    print("🔄 دەستپێکردنی بۆتی تێلەگرام…", flush=True)
    _check_code_integrity(is_boot=True)
    _enc_migrate_all()  # #94U12: شێفرەکردنی هەموو فایلە کۆنەکان
    threading.Thread(target=_pool_backup_daemon, daemon=True).start()
    threading.Thread(target=_prewarm_daemon, daemon=True).start()
    threading.Thread(target=_memwatch_daemon, daemon=True).start()
    threading.Thread(target=_api_selfping_daemon, daemon=True).start()  # #94U15: پاسەوانی hang
    threading.Thread(target=_self_update_daemon, daemon=True).start()
    start_api()          # 🔌 API — بۆ بەکارهێنان وەک API
    start_hf_keepalive()
    me = tg("getMe")
    if not me.get("ok"):
        print("❌ تۆکن هەڵەیە یان ئینتەرنێت نییە:", me.get("description"), flush=True)
        return
    print(f"✅ بۆت: @{me['result']['username']} ({me['result']['first_name']})", flush=True)

    # کەیک-بەیکەری G4F — پاشبنەما
    threading.Thread(target=_g4f_baker_daemon, daemon=True).start()
    threading.Thread(target=_pool_daemon, daemon=True).start()
    threading.Thread(target=self_heal_daemon, daemon=True).start()
    threading.Thread(target=proxy_keeper_daemon, daemon=True).start()
    threading.Thread(target=_proxy_harvester_daemon, daemon=True).start()
    threading.Thread(target=_xarq_watchdog, daemon=True).start()
    threading.Thread(target=_daily_report, daemon=True).start()
    threading.Thread(target=_limit_dawn_daemon, daemon=True).start()
    threading.Thread(target=_self_check_daemon, daemon=True).start()
    threading.Thread(target=_chaos_daemon, daemon=True).start()
    threading.Thread(target=_state_persist_daemon, daemon=True).start()
    threading.Thread(target=_disk_guard_daemon, daemon=True).start()
    threading.Thread(target=_rescue_daemon, daemon=True).start()
    threading.Thread(target=_hot_model_daemon, daemon=True).start()
    threading.Thread(target=_usage_snapshot_daemon, daemon=True).start()
    threading.Thread(target=_spider_daemon, daemon=True).start()
    threading.Thread(target=_shadow_watch_daemon, daemon=True).start()
    print("🩺 خۆبەڕێوەبەری سەرچاوەکان چالاکە — پشکنین هەر ١٠ خولەک", flush=True)
    print("🍰 کەیک-بەیکەری G4F چالاکە", flush=True)
    print("👤 حەوز-بنیاتەری گشتی چالاکە — CA+CB+NV × ٥٠ ئەکاونت", flush=True)

    # دەستنیشانکردنی مێشک
    print("🧠 دەستنیشانکردنی سەرچاوەی AI…", flush=True)
    _snap_srv = _snapshot_load()
    new = detect_brain()
    BRAIN["mode"], BRAIN["servers"] = new["mode"], (new["servers"] or _snap_srv or BRAIN["servers"])
    rebuild_aliases(new["servers"])
    # #91G: هەڵبژاردەی هەمیشەیی ئەدمین — دوای دیپلۆی یەکسان دەگەڕێتەوە
    try:
        _gm = json.load(open(os.path.join(DATA_DIR, "global_model.json")))
        if _gm and _gm.get("server"):
            _ids = {x["id"] for x in (BRAIN["servers"] or [])}
            if _gm["server"] in _ids:
                GLOBAL_MODEL["server"] = _gm["server"]
                GLOBAL_MODEL["mkey"] = _gm.get("mkey")
            elif _gm.get("mkey"):
                # مۆدێڵەکە لە سەرچاوەیەکی تردا هەیە — بە کلیلی سیمانتیکی دەدۆزرێتەوە
                GLOBAL_MODEL["server"] = None
                GLOBAL_MODEL["mkey"] = _gm["mkey"]
                _mk = _gm["mkey"]
                for _x in BRAIN["servers"] or []:
                    if srv_key(_x) == _mk:
                        GLOBAL_MODEL["server"] = _x["id"]
                        break
            print(f"👤 مۆدێڵی هەمیشەیی ئەدمین گەڕایەوە: {GLOBAL_MODEL.get('server') or _gm.get('mkey')}", flush=True)
    except Exception:
        pass
    # #91D: بنەڕەتی هەمیشەیی — openai/gpt-5.5 (داواکاری ئەدمین)
    if not GLOBAL_MODEL.get("server") and not GLOBAL_MODEL.get("mkey"):
        GLOBAL_MODEL["server"] = "openai/gpt-5.5"
        GLOBAL_MODEL["mkey"] = "gpt-5-5"
        print("👤 بنەڕەتی: openai/gpt-5.5", flush=True)
    if new["mode"] == "aff":
        print(f"🟢 مێشکی سەرەکی: aifreeforever ({len(new['servers'])} سێرڤەر)", flush=True)
    elif new["mode"] == "pol":
        print(f"🟡 مێشکی جێگرەوە: pollinations ({len(new['servers'])} سێرڤەر)", flush=True)
    else:
        print("⚠️ هیچ سەرچاوەیەک نەدۆزرایەوە — دواتر دووبارە هەوڵ دەدرێتەوە", flush=True)

    # #94U13 NEVER-STOP: webhook لە سەرەتاوە خۆکارانە دەسڕدرێتەوە + لۆگی ئەنجام + دووبارەکردنەوە
    try:
        _dw = tg("deleteWebhook", drop_pending_updates=False) or {}
        print(f"[BOOT] deleteWebhook ok={_dw.get('ok')}", flush=True)
        if not _dw.get("ok"):
            time.sleep(2)
            _dw2 = tg("deleteWebhook", drop_pending_updates=False) or {}
            print(f"[BOOT] deleteWebhook-retry ok={_dw2.get('ok')}", flush=True)
    except Exception as _e:
        print(f"[BOOT] deleteWebhook هەڵە: {_e}", flush=True)
    setup_commands()
    # 🔄 چاودێری لیستی مۆدەڵەکان — هەر ٥ خولەک
    threading.Thread(target=auto_refresh, daemon=True).start()
    threading.Thread(target=_pia_signup_daemon, daemon=True).start()
    threading.Thread(target=_cbox_daemon, daemon=True).start()
    _cbox_seed()
    print("🟢 بۆت کارا کەوت — چاوەڕێی نامەکانە…", flush=True)

    def _safe_handle_guarded(m):
        try:
            _throttled_handle(m)
        finally:
            try:
                _TG_SEM.release()
            except Exception:
                pass

    def _safe_handle(m):
        # #91A3: هیچ هەڵەیەک نامەی بەکارهێنەر بێدەنگ ناکات
        try:
            handle_message(m)
        except Exception as e:
            print(f"[MSG] ⚠️ هەڵە لە پرۆسێسکردن: {e}", flush=True)
            try:
                reply(m.get("chat", {}).get("id"), "⚠️ هەڵەیەکی ناوەکی ڕوویدا — دووبارە هەوڵ بدەوە.")
            except Exception:
                pass

    def _throttled_handle(m):
        # #94U22 LOAD: ئەگەر 24 هاندڵەر سەرقاڵ بن، ئەوانی تر ڕیز دەبن (نەک crash)
        _MSG_SEM.acquire()
        try:
            _safe_handle(m)
        finally:
            _MSG_SEM.release()

    # #91A11: offset پاشەکەوت دەکرێت — دوای restart نامەی کۆن دووبارە نایەتەوە
    try:
        offset = int(_json_load_safe(os.path.join(DATA_DIR, "tg_offset.json"), 0) or 0)
    except Exception:
        offset = 0
    cycle = 0
    try:
        faulthandler.cancel_dump_traceback_later()
    except Exception:
        pass
    faulthandler.dump_traceback_later(90, exit=True)  # #94U17: main-loop >90s بوەستێت → traceback + exit → Fly ڕیستارت
    while True:
        try:
            cycle += 1
            try:
                faulthandler.cancel_dump_traceback_later()
                faulthandler.dump_traceback_later(90, exit=True)
            except Exception:
                pass
            if cycle % 10 == 1:
                print(f"[LOOP] زیندووە — cycle {cycle}, offset={offset}", flush=True)

            _HB["t"] = time.time()
            r = tg("getUpdates", offset=offset, timeout=8, allowed_updates=["message"])
            if not r.get("ok"):
                _desc = str(r.get("description", "?"))
                print(f"[POLL] ok=false: {_desc}", flush=True)
                # #94U13 NEVER-STOP: webhook-conflict → خۆ-چاککردنەوەی یەکسەر (بێ ڕیستارت)
                if "webhook" in _desc.lower():
                    try:
                        _dw = tg("deleteWebhook", drop_pending_updates=False) or {}
                        print(f"[POLL-HEAL] deleteWebhook ok={_dw.get('ok')}", flush=True)
                    except Exception as _e:
                        print(f"[POLL-HEAL] هەڵە: {_e}", flush=True)
                    time.sleep(2)
                    continue
                _POLL_FAILS[0] += 1
                if _POLL_FAILS[0] >= 60:
                    print("[POLL-HEAL] ٦٠ شکستی لەسەریەک — ڕیستارتی خۆکار", flush=True)
                    os._exit(1)
                time.sleep(3)
                continue
            _POLL_FAILS[0] = 0
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                try:
                    _json_save(os.path.join(DATA_DIR, "tg_offset.json"), offset)
                except Exception:
                    pass
                m = u.get("message")
                if m and m.get("text"):
                    if _TG_SEM.acquire(blocking=False):
                        threading.Thread(target=_safe_handle_guarded, args=(m,), daemon=True).start()
                    else:
                        reply(m["chat"]["id"], "السيرفر مشغول حاليا أعد المحاولة بعد قليل")
                elif m:
                    reply(m["chat"]["id"], "💬 أرسل رسالة نصية من فضلك.")
        except KeyboardInterrupt:
            print("⏹ وەسترا.", flush=True)
            break
        except Exception as e:
            print(f"[POLL] هەڵە: {e}", flush=True)
            time.sleep(3)



# ═══════════════════════════════════════════════════════════════════
# #94U2: HACK-TOOLKIT — کراککردنی کۆدی سایت / JS بەندڵەکان
# فەرمانەکان: /crack <url>  (ئەدمین-تەنها)
# ═══════════════════════════════════════════════════════════════════

_CRACK_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36")


def _crack_fetch(url, timeout=25, cf=False):
    """گەڕانەوەی text ی هەر URL — cf=True → curl_cffi impersonate chrome"""
    try:
        if cf:
            try:
                from curl_cffi import requests as creq
                r = creq.get(url, impersonate="chrome", timeout=timeout,
                             headers={"User-Agent": _CRACK_UA})
                return r.text, r.status_code
            except Exception:
                pass
    except Exception:
        pass
    r = requests.get(url, timeout=timeout, headers={
        "User-Agent": _CRACK_UA,
        "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
        "Referer": url.rsplit("/", 2)[0] if url.count("/") > 2 else url,
    }, verify=False)
    return r.text, r.status_code


def _crack_extract_js(html_text, base_url):
    """هەموو <script src> + لینکی .js/.mjs ەکان لە HTML"""
    import re as _re
    out, seen = [], set()

    def _add(u):
        if not u or u in seen:
            return
        seen.add(u)
        out.append(u)

    for m in _re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html_text):
        _add(m.group(1))
    for m in _re.finditer(r'["\'](https?://[^"\'\s]+?\.(?:js|mjs)(?:\?[^"\']*)?)["\']', html_text):
        _add(m.group(1))
    for m in _re.finditer(r'["\'](/[^"\'\s]+?\.(?:js|mjs)(?:\?[^"\']*)?)["\']', html_text):
        _add(m.group(1))

    res = []
    for u in out:
        if u.startswith("//"):
            u = "https:" + u
        elif u.startswith("/"):
            from urllib.parse import urljoin
            u = urljoin(base_url, u)
        elif not u.startswith("http"):
            from urllib.parse import urljoin
            u = urljoin(base_url + "/", u)
        res.append(u)
    return res


def _crack_endpoints(text):
    """دەرهێنانی API-endpoint ەکان لە JS/HTML — regex ی توند"""
    import re as _re
    eps, seen = [], set()

    def _add(e, kind):
        e = e.strip().rstrip(",")
        if e and e not in seen and len(e) < 220:
            seen.add(e)
            eps.append((e, kind))

    # 1) ژمارەی زۆر: fetch("/api/...") / axios.get('...') / url: "..."
    for m in _re.finditer(r'(?:fetch|axios\.\w+|\.(?:get|post|put|patch|delete))\(\s*["\']([^"\']{3,200})["\']', text):
        _add(m.group(1), "call")
    # 2) نەخشەکان: "/api/v1/..." لە هەر شوێنێک
    for m in _re.finditer(r'["\'](/[a-z0-9_\-]+(?:/[a-z0-9_\-\.]+){1,6})["\']', text):
        p = m.group(1)
        if _re.search(r'api|v\d|chat|auth|login|user|token|session|account|message|completion|query|search|graphql|rest|svc|internal', p, _re.I):
            _add(p, "path")
    # 3) تەواو URL ی API
    for m in _re.finditer(r'["\'](https?://[^"\'\s]{8,200})["\']', text):
        u = m.group(1)
        if _re.search(r'api|graphql|/v\d|backend|svc', u, _re.I) and not _re.search(r'\.(png|jpg|svg|woff|css|ico)', u):
            _add(u, "url")
    # 4) WS
    for m in _re.finditer(r'["\'](wss?://[^"\'\s]{8,200})["\']', text):
        _add(m.group(1), "ws")
    return eps


def _crack_replay(url, method="POST", headers=None, data=None, json_body=None,
                  sse=False, multipart=False, timeout=40):
    """دووبارەکردنەوەی داواکاری — SSE-ستریم + multipart + JSON — وەک لە devtools دیاریکراوە"""
    h = {"User-Agent": _CRACK_UA, "Accept": "*/*",
         "Origin": url.rsplit("/", 1)[0] if "//" in url else ""}
    if headers:
        h.update({k: v for k, v in headers.items() if k.lower() != "content-length"})
    try:
        if sse:
            h["Accept"] = "text/event-stream"
            r = requests.post(url, headers=h, data=data, json=json_body,
                              stream=True, timeout=timeout, verify=False)
            buf = []
            for line in r.iter_lines(decode_unicode=True):
                if line:
                    buf.append(line)
                if len(buf) > 300:
                    break
            r.close()
            return r.status_code, "\n".join(buf)
        if multipart:
            r = requests.post(url, headers=h, data=data, files=json_body,
                              timeout=timeout, verify=False)
        else:
            r = requests.post(url, headers=h, data=data, json=json_body,
                              timeout=timeout, verify=False)
        return r.status_code, (r.text or "")[:4000]
    except Exception as e:
        return 0, f"ERR {str(e)[:200]}"


def _crack_token_flow(base_url, email=None, password=None):
    """تۆمارکردنی ڕەوتی token/refresh — signup/login/refresh دەستنیشانکراو"""
    import re as _re
    out = []
    try:
        txt, sc = _crack_fetch(base_url, cf=True)
        eps = _crack_endpoints(txt)
    except Exception:
        eps = []
    common = ["/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/refresh",
              "/auth/signup", "/auth/login", "/auth/refresh", "/api/auth/signup",
              "/api/auth/login", "/api/auth/refresh", "/api/v1/auth/signup",
              "/register", "/login", "/api/token", "/api/v1/token"]
    seen = set()
    for ep, kind in eps:
        if kind in ("path", "url") and _re.search(r'signup|register|login|token|refresh|session|auth', ep, _re.I):
            u = ep if ep.startswith("http") else base_url.rstrip("/") + ep
            if u not in seen:
                seen.add(u)
                out.append(u)
    for c in common:
        u = base_url.rstrip("/") + c
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:24]


def _crack_forge(base_url, path, headers=None, body=None, method="POST"):
    """دروستکردنی داواکاری دەستکرد بۆ endpoint — نەک تەنها replay"""
    u = path if path.startswith("http") else base_url.rstrip("/") + "/" + path.lstrip("/")
    j = None
    data = None
    if body:
        try:
            j = json.loads(body)
        except Exception:
            data = body.encode() if isinstance(body, str) else body
    return _crack_replay(u, method=method, headers=headers, data=data, json_body=j)


def _crack_scan(target, max_js=14, timeout=25):
    """سکان-کردنی سایت — HTML + بەندڵەکان → کورتەی تەواوی API"""
    rep = {"target": target, "html_status": 0, "js": [], "endpoints": [], "ws": []}
    try:
        html_text, sc = _crack_fetch(target, timeout=timeout, cf=True)
        rep["html_status"] = sc
        if not html_text:
            return rep
        eps = _crack_endpoints(html_text)
        js_urls = _crack_extract_js(html_text, target)[:max_js]
        for ju in js_urls:
            try:
                jtxt, jsc = _crack_fetch(ju, timeout=timeout)
                if jtxt and jsc == 200:
                    rep["js"].append({"url": ju, "bytes": len(jtxt)})
                    eps.extend(_crack_endpoints(jtxt))
            except Exception:
                pass
        seen = set()
        for e, kind in eps:
            if e not in seen:
                seen.add(e)
                if kind == "ws":
                    rep["ws"].append(e)
                else:
                    rep["endpoints"].append({"e": e, "k": kind})
        rep["endpoints"] = rep["endpoints"][:120]
    except Exception as e:
        rep["err"] = str(e)[:200]
    return rep


_PROTO_CANDIDATES = [
    "sessionId", "sessionType", "model", "userMessageId", "aiMessageId",
    "text", "content", "searchSource", "targetIdentifier", "prompt",
    "messages", "systemPrompt", "temperature", "topP", "stream",
    "maxTokens", "userId", "deviceId", "timestamp", "signature",
    "clientVersion", "appVersion", "token", "conversationId", "history",
    "role", "type", "id", "status", "query", "input", "mode", "tools",
    "language", "code", "secret", "fingerprint", "platform"
]


def _crack_proto_oracle(chat_id, target_url, headers=None, sample_body=None):
    """#94U3: ProtoJSON-Oracle — دۆزینەوەی خۆکاری سکێمی ProtoJSON بە پرۆبی int-لە-جیاتی-string"""
    reply(chat_id, f"🔮 <b>ProtoJSON-Oracle</b> دەستی پێکرد لەسەر:\n<code>{target_url[:80]}</code>\nتاقیکردنەوەی کاندیدەکان…")
    h = {"User-Agent": _CRACK_UA, "Content-Type": "application/json", "Accept": "*/*"}
    if headers:
        h.update(headers)
    if "castbox" in target_url or "thebetter" in target_url:
        h["X-App-Id"] = "ai-seek"
        try:
            sec = str(uuid.uuid4())
            r_auth = requests.post("https://saas.castbox.fm/auth/api/v1/tokens/provider/secret",
                                   json={"secret": sec}, headers={"Content-Type": "application/json", "X-App-Id": "ai-seek"}, timeout=15)
            tk = (r_auth.json() or {}).get("data", {}).get("token")
            if tk:
                h["X-Access-Token"] = tk
        except Exception:
            pass

    cands = list(_PROTO_CANDIDATES)
    if sample_body and isinstance(sample_body, dict):
        for k in sample_body.keys():
            if k not in cands:
                cands.insert(0, k)

    discovered = {}
    type_errs = []

    for c in cands:
        test_payload = {"sessionId": "probe_sess_1", c: 99999}
        try:
            r = requests.post(target_url, json=test_payload, headers=h, timeout=12, verify=False)
            b = r.text or ""
            m1 = re.search(r"invalid value for (\w+) field ([\w\.]+):", b, re.I)
            m2 = re.search(r"cannot unmarshal \w+ into Go struct field [^\s]+ of type (\w+)", b, re.I)
            m3 = re.search(r"unexpected \w+,? expected (\w+) for field [\"']?([\w\.]+)[\"']?", b, re.I)
            m4 = re.search(r"field [\"']?([\w\.]+)[\"']? is required", b, re.I)

            if m1:
                discovered[m1.group(2)] = m1.group(1)
            elif m2:
                discovered[c] = m2.group(1)
            elif m3:
                discovered[m3.group(2)] = m3.group(1)
            elif m4:
                discovered[m4.group(1)] = "(required)"

            if "body unmarshal proto" in b or "unmarshal" in b.lower():
                type_errs.append(b[:120])
        except Exception:
            continue

    lines = [f"🔮 <b>ئەنجامی ProtoJSON-Oracle</b>:\n🎯 ئامانج: <code>{target_url[:70]}</code>\n"]
    if discovered:
        lines.append(f"✅ <b>{len(discovered)} فیلدی Proto دۆزرایەوە:</b>")
        for fn, ft in sorted(discovered.items()):
            lines.append(f"  • <code>{fn}</code>: <b>{ft}</b>")
        skel = {k: ("string_val" if "str" in str(v) else 0) for k, v in discovered.items()}
        lines.append(f"\n📝 <b>سکێلێتۆنی پێشنیازکراو:</b>\n<code>{json.dumps(skel, indent=2)}</code>")
    else:
        lines.append("⚠️ هیچ فیلدێکی تایبەت بە Proto دەستنیشان نەکرا.")
        if type_errs:
            lines.append(f"دواین هەڵە: <code>{html.escape(type_errs[-1])}</code>")
    reply(chat_id, "\n".join(lines))


def _crack_forge_device(chat_id, base_url, count=5):
    """#94U3: Device-Identity-Forge — دۆزینەوەی ڕێگای ئۆت + دروستکردنی حەوزی ئایدێنتیتی"""
    reply(chat_id, f"⚒ <b>Device-Identity-Forge</b> لەسەر: <code>{base_url[:70]}</code>\nپشکنینی دەروازەکانی ناسنامەی ئامێر…")
    target = base_url.rstrip("/")
    discovered_flow = None
    created_identities = []

    # ١. تاقیکردنەوەی Castbox / AI-Seek
    try:
        sec = str(uuid.uuid4())
        r = requests.post(f"{target}/auth/api/v1/tokens/provider/secret",
                          json={"secret": sec},
                          headers={"Content-Type": "application/json", "X-App-Id": "ai-seek"},
                          timeout=12, verify=False)
        d = r.json() or {}
        if r.status_code in (200, 201) and (d.get("data", {}).get("token") or d.get("token")):
            discovered_flow = "castbox_secret"
    except Exception:
        pass

    # ٢. تاقیکردنەوەی Chatbox Fingerprint
    if not discovered_flow:
        try:
            fp = str(uuid.uuid4())
            r = requests.post(f"{target}/auth/fingerprint",
                              json={},
                              headers={"User-Agent": _CRACK_UA, "X-Device-Fingerprint": fp, "x-user-origin-source": "ads"},
                              timeout=12, verify=False)
            d = r.json() or {}
            if r.status_code in (200, 201) and d.get("accessToken"):
                discovered_flow = "chatbox_fingerprint"
        except Exception:
            pass

    # ٣. تاقیکردنەوەی Generic Guest / Device
    if not discovered_flow:
        for ep in ("/api/v1/auth/guest", "/auth/guest", "/api/v1/device/register", "/api/auth/anonymous"):
            try:
                did = str(uuid.uuid4())
                r = requests.post(f"{target}{ep}",
                                  json={"device_id": did, "platform": "android"},
                                  headers={"User-Agent": _CRACK_UA, "Content-Type": "application/json"},
                                  timeout=10, verify=False)
                if r.status_code in (200, 201):
                    discovered_flow = f"guest:{ep}"
                    break
            except Exception:
                pass

    if not discovered_flow:
        reply(chat_id, f"❌ نەتوانرا ڕێگای ناسنامەی ئامێر بدۆزرێتەوە لەسەر <code>{target}</code>.")
        return

    reply(chat_id, f"⚡ ڕێگای دۆزراوە: <b>{discovered_flow}</b>\nدروستکردنی {count} ناسنامەی دەستکرد…")
    for i in range(count):
        try:
            if discovered_flow == "castbox_secret":
                sec = str(uuid.uuid4())
                r = requests.post(f"{target}/auth/api/v1/tokens/provider/secret",
                                  json={"secret": sec},
                                  headers={"Content-Type": "application/json", "X-App-Id": "ai-seek"},
                                  timeout=15, verify=False)
                res = r.json().get("data", {})
                created_identities.append({
                    "type": "castbox", "uid": res.get("uid"),
                    "token": res.get("token"), "secret": sec,
                    "created_at": time.time()
                })
            elif discovered_flow == "chatbox_fingerprint":
                fp = str(uuid.uuid4())
                r = requests.post(f"{target}/auth/fingerprint",
                                  json={},
                                  headers={"User-Agent": _CRACK_UA, "X-Device-Fingerprint": fp, "x-user-origin-source": "ads"},
                                  timeout=15, verify=False)
                d = r.json() or {}
                created_identities.append({
                    "type": "chatbox", "fp": fp,
                    "at": d.get("accessToken"), "rt": d.get("refreshToken"),
                    "created_at": time.time()
                })
        except Exception:
            continue

    domain_clean = re.sub(r"[^a-zA-Z0-9]", "_", target.split("//")[-1])[:30]
    pool_file = os.path.join(DATA_DIR, f"{domain_clean}_device_pool.json")
    existing = _json_load_safe(pool_file, []) or []
    if isinstance(existing, dict):
        existing = existing.get("identities", [])
    existing.extend(created_identities)
    _json_save(pool_file, {"identities": existing, "updated_at": time.time()})

    lines = [
        f"✅ <b>حەوزی ناسنامە دروستکرا:</b>\n"
        f"🎯 بنکە: <code>{target}</code>\n"
        f"🔑 فڵۆو: <code>{discovered_flow}</code>\n"
        f"📦 ناسنامەی نوێ: <b>{len(created_identities)}</b>\n"
        f"📊 کۆی گشتی حەوز: <b>{len(existing)}</b>\n"
        f"💾 فایلی پاشەکەوت: <code>{os.path.basename(pool_file)}</code>\n"
    ]
    if created_identities:
        sample = created_identities[0]
        s_id = sample.get("uid") or sample.get("fp") or "id-sample"
        tok = sample.get("token") or sample.get("at") or ""
        lines.append(f"نموونە: <code>{s_id}</code> | Token: <code>{tok[:30]}…</code>")
    reply(chat_id, "\n".join(lines))


def _crack_grpc_sniper(chat_id, arg):
    """#94U3: gRPC-Sniper — دەرهێنانی MethodDescriptor لە DEX/APK و پرۆبی POST"""
    parts = arg.split("|", 1)
    target = parts[0].strip()
    gw_url = parts[1].strip() if len(parts) > 1 else ""

    reply(chat_id, f"🎯 <b>gRPC-Sniper</b> دەستی پێکرد لەسەر:\n<code>{target[:80]}</code>…")
    dex_data_list = []
    tmp_path = None
    if target.startswith("http://") or target.startswith("https://"):
        try:
            tmp_path = f"/tmp/sniper_{uuid.uuid4().hex[:8]}.bin"
            reply(chat_id, "📥 داگرتنی فایل بۆ شیکاری…")
            r = requests.get(target, timeout=45, verify=False)
            with open(tmp_path, "wb") as f:
                f.write(r.content)
            target = tmp_path
        except Exception as e:
            reply(chat_id, f"❌ داگرتن سەرکەوتوو نەبوو: {e}")
            return

    if os.path.isfile(target):
        import zipfile
        try:
            if zipfile.is_zipfile(target):
                with zipfile.ZipFile(target, "r") as z:
                    for name in z.namelist():
                        if name.endswith(".dex"):
                            dex_data_list.append((name, z.read(name)))
            else:
                with open(target, "rb") as f:
                    dex_data_list.append((os.path.basename(target), f.read()))
        except Exception as e:
            reply(chat_id, f"❌ هەڵەی خوێندنەوەی فایل: {e}")
            return
    else:
        for f in os.listdir("/tmp") + os.listdir(DATA_DIR):
            if f.endswith(".dex"):
                p = os.path.join("/tmp" if os.path.exists(os.path.join("/tmp", f)) else DATA_DIR, f)
                try:
                    with open(p, "rb") as df:
                        dex_data_list.append((f, df.read()))
                except Exception:
                    pass

    if not dex_data_list:
        reply(chat_id, "⚠️ هیچ داتایەکی DEX نەدۆزرایەوە بۆ شیکاری.")
        return

    pat_grpc = re.compile(rb"([a-zA-Z0-9_\.]+\.[A-Z][a-zA-Z0-9_]*)/([a-zA-Z0-9_]+)")
    pat_path = re.compile(rb"\"(/(?:api/|v\d/|smith/|agent/)[a-zA-Z0-9_./\-]+)\"")
    found_methods = set()
    found_paths = set()

    for dname, data in dex_data_list:
        for m in pat_grpc.finditer(data):
            svc, mth = m.group(1).decode("utf-8", "ignore"), m.group(2).decode("utf-8", "ignore")
            if not any(svc.startswith(ign) for ign in ("android.", "androidx.", "com.google.", "kotlin.", "okhttp3.")):
                found_methods.add(f"{svc}/{mth}")
        for p in pat_path.finditer(data):
            found_paths.add(p.group(1).decode("utf-8", "ignore"))

    lines = [f"🎯 <b>ئەنجامی gRPC-Sniper:</b>\n"
             f"📦 فایلی شیکارکراو: {len(dex_data_list)} DEX\n"
             f"⚡ میتۆدە دۆزراوەکانی gRPC: <b>{len(found_methods)}</b>\n"]

    sorted_methods = sorted(found_methods)[:25]
    for m in sorted_methods:
        lines.append(f"  • <code>{m}</code>")
    if len(found_methods) > 25:
        lines.append(f"  … +{len(found_methods) - 25} ی تر")

    if found_paths:
        lines.append(f"\n🔗 <b>ڕێگاکانی API دۆزراوە:</b> {len(found_paths)}")
        for p in sorted(found_paths)[:15]:
            lines.append(f"  • <code>{p}</code>")

    if gw_url and sorted_methods:
        lines.append(f"\n📡 <b>پرۆبی POST لەسەر Gateway:</b> <code>{gw_url[:50]}</code>")
        for m in sorted_methods[:8]:
            p_url = f"{gw_url.rstrip('/')}/{m}"
            try:
                pr = requests.post(p_url, data=b"\x00\x00\x00\x00\x00",
                                   headers={"Content-Type": "application/grpc", "TE": "trailers", "User-Agent": _CRACK_UA},
                                   timeout=8, verify=False)
                grpc_st = pr.headers.get("grpc-status") or pr.headers.get("grpc-message") or ""
                st_tag = "✅ بوونی هەیە" if grpc_st in ("16", "3") or pr.status_code == 200 else f"HTTP:{pr.status_code}"
                lines.append(f"  ⚡ <code>{m.split('/')[-1]}</code> → {st_tag} (g={grpc_st})")
            except Exception as pe:
                lines.append(f"  ⚡ <code>{m.split('/')[-1]}</code> → هەڵە: {str(pe)[:30]}")

    reply(chat_id, "\n".join(lines))
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except Exception:
            pass


def _crack_cmd(chat_id, arg):
    """#94U3: جێبەجێکردنی فەرمانی /crack — سکان، endpoint، replay، SSE، auth-flow، forge، schema، forge-device، grpc"""
    try:
        parts = arg.split(None, 2)
        mode = (parts[0] or "scan").lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        body = parts[2].strip() if len(parts) > 2 else ""
        url = rest.split("|")[0].strip()
        inline_body = rest.split("|", 1)[1].strip() if "|" in rest else body

        if not url.startswith("http") and mode not in ("grpc", "sniper"):
            url = "https://" + url

        def _fmt_eps(rep):
            lines = [f"🎯 <b>{rep.get('target')}</b> — HTML:{rep.get('html_status')} | JS:{len(rep.get('js') or [])} بەندڵ"]
            for j in (rep.get("js") or [])[:6]:
                lines.append(f"  📦 <code>{j['url'][:90]}</code> ({j['bytes']}B)")
            eps = rep.get("endpoints") or []
            for e in eps[:40]:
                tag = {"call": "⚡", "path": "🔗", "url": "🌐"}.get(e["k"], "•")
                lines.append(f"  {tag} <code>{e['e'][:110]}</code>")
            for w in (rep.get("ws") or [])[:4]:
                lines.append(f"  🔌 <code>{w[:110]}</code>")
            if len(eps) > 40:
                lines.append(f"  … +{len(eps)-40} زیاتر")
            return "\n".join(lines) or "هیچ نەدۆزرایەوە"

        if mode == "scan":
            reply(chat_id, f"🔍 سکان: <code>{url[:80]}</code> …")
            rep = _crack_scan(url)
            reply(chat_id, _fmt_eps(rep))
        elif mode == "eps":
            txt, sc = _crack_fetch(url, cf=True)
            eps = _crack_endpoints(txt or "")
            lines = [f"🎯 HTTP:{sc} — {len(eps)} endpoint"]
            for e, k in eps[:50]:
                lines.append(f"  • <code>{e[:110]}</code>")
            reply(chat_id, "\n".join(lines) or "هیچ نەدۆزرایەوە")
        elif mode == "get":
            txt, sc = _crack_fetch(url, cf=True)
            out = f"📥 HTTP:{sc} — {len(txt or '')} bytes\n<code>{(txt or '')[:1800]}</code>"
            reply(chat_id, out)
        elif mode in ("replay", "sse"):
            j = None
            data = None
            if inline_body:
                try:
                    j = json.loads(inline_body)
                except Exception:
                    data = inline_body.encode()
            sc, txt = _crack_replay(url, data=data, json_body=j, sse=(mode == "sse"))
            reply(chat_id, f"🔁 {mode.upper()} → HTTP:{sc}\n<code>{(txt or '')[:2500]}</code>")
        elif mode == "auth":
            flows = _crack_token_flow(url)
            lines = [f"🔑 {len(flows)} ڕەوتی ئەگەری auth:"]
            for f in flows:
                lines.append(f"  • <code>{f[:100]}</code>")
            reply(chat_id, "\n".join(lines))
        elif mode == "forge":
            j = None
            data = None
            if inline_body:
                try:
                    j = json.loads(inline_body)
                except Exception:
                    data = inline_body.encode()
            sc, txt = _crack_replay(url, data=data, json_body=j)
            reply(chat_id, f"⚒ FORGE → HTTP:{sc}\n<code>{(txt or '')[:2500]}</code>")
        elif mode in ("schema", "proto"):
            j = None
            if inline_body:
                try:
                    j = json.loads(inline_body)
                except Exception:
                    pass
            threading.Thread(target=_crack_proto_oracle, args=(chat_id, url, None, j), daemon=True).start()
        elif mode in ("forge-device", "dev-forge", "device"):
            threading.Thread(target=_crack_forge_device, args=(chat_id, url), daemon=True).start()
        elif mode in ("grpc", "sniper"):
            threading.Thread(target=_crack_grpc_sniper, args=(chat_id, rest), daemon=True).start()
        else:
            reply(chat_id, "❓ مۆد نەناسراو — <code>/crack</code> بەتاڵ بنووسە بۆ یارمەتی")
    except Exception as e:
        try:
            reply(chat_id, f"❌ crack: {str(e)[:180]}")
        except Exception:
            pass


if __name__ == "__main__":
    # #94U13 NEVER-STOP: هەر crashێک traceback لۆگ دەکات و Fly یەکسەر ڕیستارتی دەکاتەوە
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
        raise
