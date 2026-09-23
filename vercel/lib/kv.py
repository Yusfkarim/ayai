"""Vercel KV (Upstash REST) + in-memory fallback. NO Fly, NO files."""
import os as _os

try:
    import requests as _rq
except Exception:
    _rq = None

_URL = (_os.environ.get("KV_REST_API_URL")
        or _os.environ.get("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
_TOK = (_os.environ.get("KV_REST_API_TOKEN")
        or _os.environ.get("UPSTASH_REDIS_REST_TOKEN") or "")
_MEM = {}
_WARNED = [False]


def _warn():
    if not _WARNED[0]:
        _WARNED[0] = True
        print("[KV] no KV_REST env — memory fallback (data dies with instance)", flush=True)


def use_rest():
    return bool(_URL and _TOK and _rq)


def _pipe(*cmds):
    r = _rq.post(_URL + "/pipeline", headers={"Authorization": "Bearer " + _TOK},
                 json=[list(c) for c in cmds], timeout=(8, 25))
    r.raise_for_status()
    return r.json() or []


def kv_get(key, default=None):
    if use_rest():
        try:
            res = _pipe(["GET", key])
            v = res[0].get("result") if res else None
            return v if v is not None else default
        except Exception:
            pass
    else:
        _warn()
    return _MEM.get(key, default)


def kv_set(key, value, ex=None):
    if use_rest():
        try:
            cmd = ["SET", key, value] + (["EX", int(ex)] if ex else [])
            _pipe(cmd)
            return True
        except Exception:
            pass
    else:
        _warn()
    _MEM[key] = value
    return True


def kv_delete(key):
    if use_rest():
        try:
            _pipe(["DEL", key])
        except Exception:
            pass
    _MEM.pop(key, None)
    return True


def kv_jget(key, default=None):
    import json as _j
    v = kv_get(key)
    if v is None:
        return default
    try:
        return _j.loads(v)
    except Exception:
        return default


def kv_jset(key, obj, ex=None):
    import json as _j
    return kv_set(key, _j.dumps(obj, ensure_ascii=False), ex)


def kv_lpush(key, *values):
    if use_rest():
        try:
            _pipe(["LPUSH", key] + list(values))
            return True
        except Exception:
            pass
    else:
        _warn()
    lst = _MEM.get(key) or []
    _MEM[key] = list(values) + lst
    return True


def kv_lrange(key, start=0, stop=-1):
    if use_rest():
        try:
            res = _pipe(["LRANGE", key, start, stop])
            return res[0].get("result") or [] if res else []
        except Exception:
            pass
    else:
        _warn()
    lst = _MEM.get(key) or []
    return lst[start:None if stop == -1 else stop + 1]


def kv_ltrim(key, start=0, stop=-1):
    if use_rest():
        try:
            _pipe(["LTRIM", key, start, stop])
            return True
        except Exception:
            pass
    else:
        _warn()
    lst = _MEM.get(key) or []
    _MEM[key] = lst[start:None if stop == -1 else stop + 1]
    return True


def kv_lrem(key, value, count=0):
    if use_rest():
        try:
            _pipe(["LREM", key, count, value])
            return True
        except Exception:
            pass
    else:
        _warn()
    _MEM[key] = [x for x in (_MEM.get(key) or []) if x != value]
    return True


def kv_incr(key):
    if use_rest():
        try:
            res = _pipe(["INCR", key])
            return int(res[0].get("result") or 0) if res else 0
        except Exception:
            pass
    else:
        _warn()
    _MEM[key] = int(_MEM.get(key) or 0) + 1
    return _MEM[key]
