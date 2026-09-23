"""Shims: consts + states + dummies injected into _ported_raw namespace. NO Fly."""
import os
import threading


def install(R):
    R.BASE_URL = "https://aifreeforever.com"
    R.UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
    R.POL_URL = "https://text.pollinations.ai/"
    R.GZ_BASE = "https://www.giz.ai"
    R.GZ_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36")
    R.GZ_PFB9 = "c7380813ca955a386914044983fbcf6a082dbf2bea2eb91917b37ba33d6ff05b"
    R.GZ_COOLDOWN = {"quota": 600.0, "login": 600.0}
    R.GZ_CDN = "https://cdnwww.giz.ai/api/model/choices/textGeneration"
    R.GZ_SKIP = {"dynamic"}
    R.LR_B = "https://www.app.lorka.ai"
    R.LR_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")
    R.KURDISH_NUMS = ["الأول", "الثاني", "الثالث", "الرابع", "الخامس",
                      "السادس", "السابع", "الثامن", "التاسع", "العاشر"]
    R.SERVER_PRIORITY = [["gemini"], ["gpt"]]
    R.ACH_API = "https://us-central1-allchatprod.cloudfunctions.net"
    R.ACH_ORIG = {"Origin": "https://app.askallchat.com",
                  "Referer": "https://app.askallchat.com/"}
    R.ACH_MODELS = [("consensus", "GPT-5 Consensus", ""),
                     ("code", "GPT-5 Code", ""),
                     ("math", "GPT-5 Math", ""),
                     ("deep", "Deep Analysis", ""),
                     ("web", "Live Web Search", ""),
                     ("gemini", "Gemini Flash-Lite", "google/gemini-2.5-flash-lite"),
                     ("gpt4o", "GPT-4o Mini", "openai/gpt-4o-mini"),
                     ("llama", "Llama 3.1 8B", "meta-llama/llama-3.1-8b-instruct")]
    R.ACH_REAL = {k: m for k, _, m in R.ACH_MODELS if m}
    R.ACH_SMART = ("consensus", "code", "math", "deep", "web")
    R.ACH_WRAPS = {
        "consensus": "\n\n(تکایە بە شیکردنەوەیەکی قووڵ، بەراوردی فرە-ڕوانگە، و هەنگاوە بیرکارییەکان وەڵام بدەوە)",
        "code": "\n\n(تکایە بە کۆدی تەواو و ڕوونکردنەوەی تەکنیکی قووڵ وەڵام بدەوە)",
        "math": "\n\n(تکایە بە هاوکێشەی ماتماتیکی و سەلماندنی هەنگاو بە هەنگاو وەڵام بدەوە)",
        "deep": "\n\n(تکایە بە بەراوردی فرە-ڕوانگەی قووڵ و شیکردنەوەی ڕەخنەگرانە وەڵام بدەوە)",
        "web": "\n\n(تکایە بە دوایین زانیاری و سەرچاوەی تازە لە ئینتەرنێت وەڵام بدەوە)",
    }
    R.ACH_BUDGET = 3
    R.ACH_DAY_CAP = 250
    R.ACH_FB_KEY = os.environ.get("ACH_FB_KEY") or ""
    R.ACH_ST = {}
    R.ACH_LOCK = threading.Lock()
    R.ACH_ACC_FILE = "/tmp/vpx_ach.json"
    R.DATA_DIR = "/tmp"
    R._UA_POOL = [R.UA, R.LR_UA, R.GZ_UA]
    # dummies — file-json path never runs (KV overrides), but keep import/call safe
    R._ENC_MAGIC = ""
    R._JSON_LOCKS = {}
    R._JSON_LOCKS_G = threading.Lock()
    R._get_fernet = None

    def _nope(*a, **k):
        raise RuntimeError("file-json disabled on Vercel (KV only)")

    R._json_save_locked = _nope
    # proxy defaults (providers.py overrides with KV versions)
    R._proxy_get = lambda n=3: []
    R._proxy_mark_bad = lambda px: None
    return R
