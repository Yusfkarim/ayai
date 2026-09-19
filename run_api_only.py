# ڕەنەری API-tənha — بۆ تاقیکردنەوەی Nova لە سندوق (TG لەسەر Fly دەمێنێتەوە)
import os, sys, time
sys.path.insert(0, "/home/user/chatbot-host")
os.environ.setdefault("API_PORT", "8080")
import main
main.start_api()
print("[API-ONLY] API ۆخت…", flush=True)
new = main.detect_brain()
main.BRAIN["mode"], main.BRAIN["servers"] = new["mode"], new["servers"]
main.rebuild_aliases(new["servers"])
main.sync_nv_models(force=False)
print(f"[API-ONLY] ئامادە — {len(main.BRAIN['servers'])} سێرڤەر | NV: {len(main.MS.get('nv_ok') or {})}", flush=True)
while True:
    time.sleep(3600)
