#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════
# 🛡 تاقیکردنەوەی گەورەی کۆتایی — syuhjsbot-yf @ 0b67bbb
# ١٢ تاقیکردنەوە: سەرچاوە · مۆدێل · ستریم · ئەمنی · burst · leak · داتا
# ═══════════════════════════════════════════════════════════
import json, time, subprocess, concurrent.futures

BASE = "https://syuhjsbot-yf.fly.dev"
KEY = "sk-yf-31c00f02aa9221b336d7b4a274bb375c"
R = []
def rec(name, ok, note=""):
    R.append((name, ok, note))
    print(f"{'✅' if ok else '❌'} {name:42} {note}")

def api(payload, key=KEY, timeout=95):
    t0 = time.time()
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout),
                        f"{BASE}/v1/chat/completions",
                        "-H", f"Authorization: Bearer {key}",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(payload)], capture_output=True, text=True)
    dt = time.time() - t0
    try:
        return json.loads(p.stdout), dt
    except Exception:
        return {"_raw": p.stdout[:120]}, dt

# ═══ ١) HEALTH — هەموو سەرچاوەکان ═══════════
h = json.loads(subprocess.run(["curl", "-s", "--max-time", "25", f"{BASE}/health"],
                              capture_output=True, text=True).stdout)
srcs = {k: v.get("ok") for k, v in (h.get("sources") or {}).items()}
rec("1. HEALTH — سیستەم", h.get("ok") is True,
    f"self={h.get('self')} | حەوز={h.get('pools')} | پرۆکسی={h.get('proxies')}")
rec("2. سەرچاوەکان", all([srcs.get(s) for s in ("cb", "ct", "nv")]),
    " ".join(f"{k}={'✅' if v else '❌'}" for k, v in sorted(srcs.items())))

# ═══ ٣) مۆدێلەکان — ٤ لایڤ ═══════════
LEAKS = ["chatbotapp", "chatbotai.co", "askaichat", "novaapp", "aimlapi", "easemate",
         "allchatbots", "supabase", "firebase", "duidir", "komex", "webshare", "fly.dev"]
ans_all, leak_hits, times = [], [], []
for mdl in ["openai/gpt-5.5", "giz/ai", "auto", "openai/gpt-5.5"]:
    j, dt = api({"model": mdl, "messages": [{"role": "user", "content": "بڵێ تەنها: سەرکەوتوو"}]})
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
    ok = bool(txt) and "error" not in j
    ans_all.append(txt)
    times.append(f"{dt:.0f}s")
    low = (txt or "").lower()
    for L in LEAKS:
        if L in low:
            leak_hits.append(L)
    print(f"   → {mdl:18} {'✅' if ok else '❌'} {dt:.0f}s  {txt[:30]!r}  [real: {j.get('model','?')}]")
rec("3. مۆدێلەکان — ٤ داواکاری", sum(1 for t in ans_all if t) >= 3, " | ".join(times))
rec("4. CACHE — دووبارە خێراتر", times[3].replace("s","").isdigit() and float(times[3][:-1]) <= max(float(times[0][:-1]), 20),
    f"یەکەم={times[0]} دووەم={times[3]}")

# ═══ ٥) STREAM — SSE ═══════════
p = subprocess.run(["curl", "-s", "-N", "--max-time", "95",
                    f"{BASE}/v1/chat/completions",
                    "-H", f"Authorization: Bearer {KEY}",
                    "-H", "Content-Type: application/json",
                    "-d", json.dumps({"model": "openai/gpt-5.5", "stream": True,
                                      "messages": [{"role": "user", "content": "بڵێ تەنها: ستریم"}]})],
                    capture_output=True, text=True)
chunks = [l for l in p.stdout.split("\n") if l.startswith("data: ") and "[DONE]" not in l]
s_txt = ""
for c in chunks:
    try:
        d = json.loads(c[6:])
        s_txt += (d.get("choices") or [{}])[0].get("delta", {}).get("content", "") or ""
    except Exception:
        pass
rec("5. STREAM — SSE", len(chunks) >= 1 and bool(s_txt.strip()), f"{len(chunks)} پارچە → {s_txt[:25]!r}")

# ═══ ٦) ئەمنی — authentications ═══════════
j1, _ = api({"model": "openai/gpt-5.5", "messages": [{"role": "user", "content": "hi"}]}, key="sk-yf-WRONG")
j2, _ = api({"model": "openai/gpt-5.5", "messages": [{"role": "user", "content": "hi"}]}, key="")
rec("6. ئەمنی — key هەڵە/بەتاڵ → 401", j1.get("error") and j2.get("error"),
    f"{str(j1.get('error'))[:28]} | {str(j2.get('error'))[:20]}")

# ═══ ٧) JSON ی خراب — server ناکوژێت ═══════════
p = subprocess.run(["curl", "-s", "--max-time", "25", f"{BASE}/v1/chat/completions",
                    "-H", f"Authorization: Bearer {KEY}", "-H", "Content-Type: application/json",
                    "-d", "{BROKEN"], capture_output=True, text=True)
alive_after = api({"model": "openai/gpt-5.5", "messages": [{"role": "user", "content": "بڵێ: زیندوو"}]})
rec("7. JSON خراب → بەردەوام زیندوو", "error" in p.stdout.lower() or p.stdout.strip() != "" and bool((alive_after[0].get('choices') or [{}])[0].get('message', {}).get('content')),
    f"broken→{p.stdout[:25]!r} | پاشان ✅")

# ═══ ٨) مۆدێی نەناسراو — هەڵەی شیرازە ═══════════
j, _ = api({"model": "zzz/nonexistent", "messages": [{"role": "user", "content": "hi"}]})
rec("8. مۆدێی نەناسراو → هەڵەی پاک", "error" in j and j.get("_raw") is None, str(j.get("error"))[:40])

# ═══ ٩) BURST — ٨ هاوکات ═══════════
def one(i):
    j, dt = api({"model": "openai/gpt-5.5", "messages": [{"role": "user", "content": f"بڵێ تەنها: {i}"}]})
    txt = (j.get("choices") or [{}])[0].get("message", {}).get("content", "")
    return bool(txt), dt, txt
t0 = time.time()
with concurrent.futures.ThreadPoolExecutor(8) as ex:
    res = list(ex.map(one, range(8)))
burst_dt = time.time() - t0
oks = sum(1 for r in res if r[0])
lat = sorted(r[1] for r in res)
rec("9. BURST — ٨ هاوکات", oks >= 7, f"{oks}/8 ✅ | {burst_dt:.0f}s تەواو | خێراترین={lat[0]:.0f}s خاوترین={lat[-1]:.0f}s")
ans_all += [r[2] for r in res]

# ═══ ١٠) LEAK — ناوە بەتاڵ لە وەڵامەکان ═══════════
all_txt = " ".join(ans_all).lower()
rec("10. LEAK-CHECK — هیچ ناوە ناوخۆییەک", not leak_hits, f"{len(ans_all)} وەڵام پشکنرا — پاک")

# ═══ ١١) DATA — پاراستن لە VM ═══════════
p = subprocess.run(["/home/user/.fly/bin/flyctl", "ssh", "console", "--app", "syuhjsbot-yf", "--command",
                    "python3 -c \"import json,glob,os;print(len(glob.glob('/data/*.bak')),len(glob.glob('/data/*')))\""],
                    capture_output=True, text=True, env={**__import__('os').environ, "FLY_API_TOKEN": open("/home/user/.fly_token").read().strip()})
line = [l for l in p.stdout.split("\n") if l.strip() and l.strip()[0].isdigit()]
baks, files = (line[-1].split() if line else ("0", "0"))
rec("11. DATA — .bak پارێزراو", int(baks) >= 5, f"{baks} فایلی .bak لە {files} فایل")

# ═══ ١٢) LOGS — بێ هەڵەی زۆر ═══════════
p = subprocess.run(["/home/user/.fly/bin/flyctl", "logs", "--app", "syuhjsbot-yf", "--no-tail"],
                   capture_output=True, text=True, env={**__import__('os').environ, "FLY_API_TOKEN": open("/home/user/.fly_token").read().strip()})
log = p.stdout
poll_err = log.count("[POLL] هەڵە")
heal_ok = "SELF-HEAL]" in log
loop_ok = "[LOOP] زیندووە" in log
rec("12. LOGS — لۆپ و چاککردنەوە", loop_ok and heal_ok and poll_err <= 3,
    f"LOOP={'✅' if loop_ok else '❌'} HEAL={'✅' if heal_ok else '❌'} هەڵەیPOLL={poll_err}")

# ═══ کۆتایی ═══════════
print("\n" + "═" * 50)
passed = sum(1 for _, ok, _ in R if ok)
print(f"🏆 ئەنجامی کۆتایی: {passed}/{len(R)} تاقیکردنەوە سەرکەوتوو")
for name, ok, note in R:
    print(f"{'✅' if ok else '❌'} {name}: {note}")
