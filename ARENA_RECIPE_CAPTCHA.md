# arena.ai (#77) — ڕیسێپی تەواو — حلکرا ✅ (2026-09-20)

## دۆخ: کار دەکات — playwright + وەڵام-گرتن (سەرکەوتوو: '4'، 'ARENA-OK'، 'SECOND')

## ئەوەی کار دەکات (کۆدی لە main.py §2.36 — kind="ar"):
1. **Login** بێ captcha: `POST /nextjs-api/sign-in/email {email, password}` → 200 + کوکی
   (negebo3462@findize.com / pass=ئیمەیلەکەی+A)
2. **براوزەری وەستاو**: chromium-headless (playwright) — login بە requests، کوکیەکان دەچنە ناو context
3. **ناردن لەناو براوزەر خۆی** (تۆکنی recaptcha Enterprise v3 تەنها لەناو خۆی دروست دەبێت):
   - `goto arena.ai` → native-setter بۆ textarea + `input` event → Enter keydown
   - مۆدالی **ToS** لە یەکەم ناردن: دوگمەی Agree بە `getBoundingClientRect` بیدۆزەوە + `mouse.click(x,y)` —
     ⚠️ `button.click()` بە JS ناتوانێت (click handler لە pointer events — coordinate پێویستە)
   - وەڵام بگرە بە **response-listener** (نەک route.abort — ئەوە تۆکن بەفیڕۆ دەدات و ٤٢٩ دەدات)
4. **پارسکردنەوە**: SSE — `a0:"…"` = وەڵامی A، `b0:"…"` = وەڵامی B — A با، ئەگەر بەتاڵ بوو B
5. **٤٢٩** = لیمیت (~١-٢ نامە/چەند خولەک) → cooldown ٣٦٠s → زنجیرە سەرچاوەی تر هەڵدەگرێت
6. براوزەر ٣٠٠s بێ کار → دادەخرێت (ڕام) — تەردی تایبەت بەخۆی (sync_playwright = thread-bound)

## ڕاگرتنە گرنگەکان (هەڵە+چارەسەر):
- **تۆکنی دەرەکی replay** (تەنانەت فۆرماتی دروست ~2500 پیت) → 403. چارەسەر: ناردن لەناو براوزەر
- **route.abort + replay** → جاری هەیە داواکاری ڕەسەن دەگاتە سێرڤەر → تۆکن بەکارهاتوو → 429 "prompt failed"
- **بەرزکردنەوەی بۆدی خۆکار** → 403 بەهۆی کەمی `modelBMessageId` + `userMessage.metadata.autoModalityMetadata`
- **keyboard native setter**: فۆنتی نموونەی ماڵپەر `Ctrl+A` ناتوانێت دیاری بکات — native setter بەکاربهێنە
- **Click بە JS** لەسەر Agree ناکوژێتەوە — mouse.click بە coordinate ی DOM

## پێکهاتەی Fly:
- Dockerfile: `pip install playwright` + `python3 -m playwright install --with-deps chromium`
- ⚠️ VM پێشتر 256MB بوو — `flyctl scale memory 1024` پێویستە بۆ chromium
- ID جوب: هەر TG نامەیەک → `goto` تازە → evaluation تازە (جیاکردنەوەی بەکارهێنەران)

## مۆدێڵی مێنیو:
- `ar-battle` — "Arena Battle (arena.ai)" — battle mode: دوو مۆدێڵی نەناسراو (A/B) وەڵام دەدەن
- direct mode قەدەغەیە بۆ نامەی-١ (سێرڤەر) — battle هەمیشە سەلامەتە

## #78 — دایرێکت + مۆدێڵەکان (تەواو):
- **دایرێکت**: worker route.continue_ دەکات — app تۆکن دروست دەکات، بۆدی دەگۆڕدرێت
  (modelAId=UUID + content + UUID7ی نوێ) → 200 → a0/b0.
- **مۆدێڵەکان**: sync_arena_models — flight-data ی SSR → 218 → text→text → ٩٠ مۆدێڵ (MS.ar_ok).
  UUID ی هەر مۆدێڵ لە `{"id":"<uuid>","organization":...}` لە flight. key = `name` (نەک publicName).
- **Fly**: shared-cpu-1x = chromium HANG (V8 CodeRange OOM)! performance-1x = 2GB OOM!
  ✅ **performance-2x (2 CPU + 4GB)** — هەردوو مۆدەکە سەرکەوتوو.
- dedupe: مۆدێڵە هاوبەشەکان (minimax-m2.7 وەک LLM7) یەک ئێنتریان هەیە — ئەو نەیتیڤە دەرەکە دەبات.
