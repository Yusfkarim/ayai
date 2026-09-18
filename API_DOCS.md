# 🌐 API ـی چاتبۆتەکەت — ئامادەیە!

## زانیاری بنەڕەتی

| شت | بەها |
|---|---|
| **ناونیشان** | `https://syuhjsbot-yf.fly.dev` |
| **کلیلی API** | `sk-yf-31c00f02aa9221b336d7b4a274bb375c` |
| **سێرڤەرەکان** | ٣٦ (٢٧ easemate + ٩ aifreeforever + pollinations) |
| **دۆخ** | 🟢 ٢٤/٧ لە Fly.io |

## 🔑 کلیدەکە لە کوێ دادەنێم؟

لە هەموو داواکارییەکدا یەکێک لەمانە:
```
Authorization: Bearer sk-yf-31c00f02aa9221b336d7b4a274bb375c
```
یان
```
X-API-Key: sk-yf-31c00f02aa9221b336d7b4a274bb375c
```

## 📡 خاڵەکانی کۆتایی (Endpoints)

### ١. لیستی سێرڤەرەکان
```bash
curl -H "Authorization: Bearer sk-yf-31c00f02aa9221b336d7b4a274bb375c" \
  https://syuhjsbot-yf.fly.dev/v1/models
```

### ٢. چات — شێوازی OpenAI (پێشنیارکراو)
```bash
curl -X POST https://syuhjsbot-yf.fly.dev/v1/chat/completions \
  -H "Authorization: Bearer sk-yf-31c00f02aa9221b336d7b4a274bb375c" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "server-1",
    "messages": [
      {"role": "user", "content": "سڵاو! چۆنی؟"}
    ]
  }'
```
**وەڵام:**
```json
{
  "choices": [{
    "message": {"role": "assistant", "content": "سڵاو! من باشم..."}
  }]
}
```

### ٣. چات — شێوازی سادە
```bash
curl -X POST https://syuhjsbot-yf.fly.dev/chat \
  -H "X-API-Key: sk-yf-31c00f02aa9221b336d7b4a274bb375c" \
  -H "Content-Type: application/json" \
  -d '{"server": 1, "message": "پایتەختی عێراق چییە؟"}'
```
**وەڵام:** `{"answer": "...", "server": "server-1"}`

## 🐍 بە Python

### ڕێگای یەکەم — بە کتێبخانەی OpenAI (باشترین)
```python
pip install openai
```
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-yf-31c00f02aa9221b336d7b4a274bb375c",
    base_url="https://syuhjsbot-yf.fly.dev/v1"
)

response = client.chat.completions.create(
    model="server-1",   # یان server-2 ... server-5
    messages=[{"role": "user", "content": "شیعرێکی کورت بە کوردی بڵێ"}]
)
print(response.choices[0].message.content)
```

### ڕێگای دووەم — بە requests
```python
import requests

r = requests.post("https://syuhjsbot-yf.fly.dev/chat",
    headers={"X-API-Key": "sk-yf-31c00f02aa9221b336d7b4a274bb375c"},
    json={"server": 1, "message": "سڵاو!"})
print(r.json()["answer"])
```

## 🟨 بە JavaScript
```javascript
const res = await fetch("https://syuhjsbot-yf.fly.dev/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": "Bearer sk-yf-31c00f02aa9221b336d7b4a274bb375c",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    model: "server-1",
    messages: [{role: "user", content: "Hello!"}]
  })
});
const data = await res.json();
console.log(data.choices[0].message.content);
```

## 🗺 نەخشەی سێرڤەرەکان (ئێستا)

### ✨ easemate.ai — ٢٧ مۆدێڵ (نوێ!)
هەموو مۆدێلەکانی easemate بەبێ ساینئاپ زیادکراون — بە ناوی ڕاستەقینەی بانگ بکە:

| ID لە API | ناو | پلە |
|---|---|---|
| `openai/gpt-5.5` | GPT-5.5 | ئەدوانس |
| `openai/gpt-5.6-luna` | GPT-5.6 Luna | ئەدوانس |
| `openai/gpt-5.4` | GPT-5.4 | ئەدوانس |
| `openai/gpt-5.2-chat` | GPT-5.2 | ئەدوانس |
| `openai/gpt-5.1` | GPT-5.1 | ئەدوانس |
| `openai/gpt-5` | GPT-5 | ئەدوانس |
| `openai/gpt-4o-mini` | GPT-4o mini | بنەڕەتی |
| `openai/o4-mini` | o4-mini | ئەدوانس |
| `anthropic/claude-opus-5` | Claude Opus 5 | ئەدوانس |
| `anthropic/claude-fable-5` | Claude Fable 5 | ئەدوانس |
| `anthropic/claude-3-haiku` | Claude 3 Haiku | بنەڕەتی |
| `google/gemini-3.5-flash` | Gemini 3.5 Flash | ئەدوانس |
| `google/gemini-3.1-pro-preview` | Gemini 3.1 Pro | ئەدوانس |
| `google/gemini-3.1-flash-lite` | Gemini 3.1 Flash Lite | بنەڕەتی |
| `google/gemini-3-flash-preview` | Gemini 3.0 Flash | بنەڕەتی |
| `google/gemini-2.5-pro` | Gemini 2.5 Pro | ئەدوانس |
| `x-ai/grok-4.3` | Grok 4.3 | ئەدوانس |
| `deepseek/deepseek-v4-pro-0813` | DeepSeek V4 Pro | ئەدوانس |
| `deepseek/deepseek-v4-flash-0731` | DeepSeek V4 Flash | بنەڕەتی |
| `deepseek/deepseek-v4.1-flash` | DeepSeek V4.1 Flash | بنەڕەتی |
| `deepseek/deepseek-v3.2` | DeepSeek V3.2 | بنەڕەتی |
| `deepseek/deepseek-r1` | DeepSeek R1 | بنەڕەتی |
| `moonshotai/kimi-k2.5` | Kimi K2.5 | بنەڕەتی |
| `moonshotai/kimi-k2.6` | Kimi 2.6 | ئەدوانس |
| `qwen/qwen3-235b-a22b` | Qwen3 235B | بنەڕەتی |
| `z-ai/glm-5.3-flash` | GLM 5.3 Flash | بنەڕەتی |
| `meta-llama/llama-3.3-70b-instruct` | Meta Llama 3.3 | بنەڕەتی |

*بە ژمارەشیان بانگ دەکرێت: `"model": "18"` یان `"model": "em-18"` = Gemini 3.1 Pro*
*لیستەکە خۆکارانە نوێ دەبێتەوە — ئەگەر easemate مۆدێڵی نوێ زیاد بکات، خۆی دێت.*

### aifreeforever (٥ مۆدێڵ)
| ID لە API | مۆدەڵی ناوەوە |
|---|---|
| `gemini-3-1` | جیمینای |
| `gpt-5-mini` | GPT Mini |
| `deepseek-v4-flash` | DeepSeek V4 |
| `kimi-k2-6` | Kimi |
| `deepseek-v3-2` | DeepSeek V3.2 |

*هەروەها `server-1` ... `server-36` بە ڕیزبەندی هەموو سێرڤەرەکان.*

## ⚙️ تایبەتمەندییەکی زیادە

- `"stream": true` لە داواکاری OpenAI-style بەکاربهێنە → وەڵام بە شێوەی SSE
- گفتوگۆی درێژ: هەموو messages ـەکە بنێرەوە (وەک OpenAI) — بۆتەکە ٢٠ نامەی کۆتایی لەبەر دەگرێت
- ⚡ **زنجیرەی مێشک:** هەر داواکارییەک سەرەتا بۆ مۆدێڵی هەڵبژارد دەچێت؛ ئەگەر ئەو بەردەست نەبوو → خۆکارانە **هاوشێوەترین مۆدێڵ** لە easemate → aifreeforever → pollinations تاقی دەکاتەوە — وەڵام هەمیشە دێت
- 🛡 **پاراستنی کەسایەتی:** ئەگەر مۆدێڵێک لاواز بێت و ناوی خۆی (GLM، GPT...) لە وەڵام بهێنێت، خۆکارانە دووبارە بەهێزتر دەکرێتەوە و ئەگەر هەر لێکی کردەوە → دەگوازرێتەوە بۆ مۆدێڵی هاوشێوە — کەسایەتی هەرگیز تێکنەچوو
- ⚠️ easemate خۆی بۆ هەر IP ـێک ژمارەیەکی کەم نامەی خۆڕایی لە ڕۆژێکدا دەدات — کاتێک تەواو بوو، خۆکارانە دەگوازرێتەوە بۆ aifreeforever
- دۆخی سێرڤەر: `GET https://syuhjsbot-yf.fly.dev/health` (بێ کلید)

## ⚠️ گرنگ

- **کلیدەکە بە کەس مەدە** — هەرکەس بیبینێت بە بێ بەرامبەر بەکاری دەبات
- بۆ گۆڕینی کلید: `flyctl secrets set API_KEY="کلیدی_نوێ" -a syuhjsbot-yf`
- **بۆتەکەی تێلەگرام** هەروا لە هەمان سێرڤەردا کار دەکات — API و بۆت پێکەوەن


> ⚡ **API بێ دیفۆڵت:** هیچ سیستەم پرۆمپتێکی بنەڕەتی نییە — هەر پرۆژەیەک system prompt ی خۆی دەنێرێت و مۆدێڵ بەپێی ئەوە وەڵام دەداتەوە؛ ئەگەر هیچ نەنێردرێت مۆدێڵ بە شێوەی ئاسایی وەڵام دەداتەوە.
