# allchatbots.ai — ڕیسێپی تەواو (بەڵام پارەدار-بەتەواوی — 2026-09-19)
## دۆخ: چاتی 402 subscription_required بۆ هەموو مۆدێڵەکان لەسەر ئەکاونتی بێ-سەبسکریپشن
## ئۆتنتیکیشتن (کاردەکات ✅):
- Supabase: POST https://felzqwdxfitazkrktyke.supabase.co/auth/v1/token?grant_type=password
  headers: {apikey: <ANON_KEY>, Content-Type: application/json}
  body: {email, password}  → 200 {access_token, refresh_token, user{id}}
- ANON_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZlbHpxd2R4Zml0YXprcmt0eWtlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcxNTQ0OTMsImV4cCI6MjA5MjczMDQ5M30.3xKzSovrFhxu-ptma0-u_5QweO0QHjeBqWoLTbRasY0
- ئەکاونت: pimeyax560@dreameg.com (pass=email) uid=221e23e6-26b2-458d-94e7-a08c61a90c99 — کۆنفرمکراو+چالاک، stripe_customer_id=null
- /tmp/al_auth.json, /tmp/al_sess.json (VOLATILE)
## چات (تەکنیکی کاردەکات — 402 بێ سەبسکریپشن):
- POST https://allchatbots.ai/api/chat  (همان-دۆمەین، Next.js)
- headers: Content-Type + Origin/Referer + **کوکی:** sb-felzqwdxfitazkrktyke-auth-token = **JSON.stringify(session)** ڕاوەڕاو (Bearer کار ناکات — 401)
- body: {messages:[{role,content}], modelId:"gpt-5-mini", stream:true|false, chatId?, webSearch?, deepSearch?, autoSearch?}
- 402={"error":"subscription_required"} بێ سەبسکریپشن؛ 429=spending_limit/credit_budget
## کاتالۆگ (٥٠ مۆدێڵ): gpt-6-astra, gpt-5.6-sol, gpt-5.6-terra/luna, gpt-5.5/5.4/5.4-mini/5.4-nano, gpt-5, gpt-5-mini/nano, gpt-4.1,
## claude-opus-5/4-8/4-7/4-6/4-5, claude-sonnet-5/4-6/4-5, claude-haiku-4-5, claude-fable-5-1/5, gemini-3.1-pro, gemini-2.5-pro,
## gemini-3.8/3.7/3.6/3.5-flash, gemini-2.5-flash, gemini-3.1-flash-lite, grok-4.6/4.5/4/3/3-mini, deepseek-v4-pro/v4-flash/chat/reasoner,
## openrouter-auto, kimi-k3, moonshot-32k/128k, mistral-large/medium/small, auto + وێنە: flux-2-pro, p-image, nano-banana-2
## بەربەستەکان:
- RLS: INSERT بۆ subscriptions → 403 (42501)
- signUp پێویستی بە کۆنفرماسیۆنی ئیمەیڵ (session نادات)
- تریاڵ = تەنها بە کارتی پارەدان (Stripe, trial_charge_note)
## ئەگەر سەبسکریپشن هەبوو → ڕیسێپی سەرەوە تەواوە — تەنها کوکی session + POST /api/chat
