// ════════════════════════════════════════════════════════════
// deepai_client.mjs — کلایەنتی deepai.org (بێ ساینئاپ — tryit key)
// stdin: {"model": "glm-5.3-flash", "messages": [...]}
// وەڵام: {"ok":true,"answer":"..."} یان {"ok":false,"error":"..."}
// مۆدی models: node deepai_client.mjs models → لیستی مۆدێلە خۆڕاییەکان
// ════════════════════════════════════════════════════════════

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';
globalThis.navigator = { userAgent: UA };

// ─── tryit key generator (وردە وەک JS ی deepai) ───
function generateIslandKey() {
  let myrandomstr = Math.round((Math.random() * 100000000000)) + '';
  const myhashfunction = (function () {
    const a = [];
    for (let b = 0; 64 > b;) a[b] = 0 | 4294967296 * Math.sin(++b % Math.PI);
    return function (input) {
      let d, e, f, g = [d = 1732584193, e = 4023233417, ~d, ~e], h = [], l = unescape(encodeURI(input)) + '\u0080', k = l.length;
      let c = --k / 4 + 2 | 15;
      for (h[--c] = 8 * k; ~k;) h[k >> 2] |= l.charCodeAt(k) << 8 * k--;
      for (let b = 0, l = 0; b < c; b += 16) {
        for (k = g; 64 > l; k = [f = k[3], d + ((f = k[0] + [d & e | ~d & f, f & d | ~f & e, d ^ e ^ f, e ^ (d | ~f)][k = l >> 4] + a[l] + ~~h[b | [l, 5 * l + 1, 3 * l + 5, 7 * l][k] & 15]) << (k = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21][4 * k + l++ % 4]) | f >>> -k), d, e]) d = k[1] | 0, e = k[2];
        for (l = 4; l;) g[--l] += k[l];
      }
      let result = '';
      for (let l = 0; 32 > l;) result += (g[l >> 3] >> 4 * (1 ^ l++) & 15).toString(16);
      return result.split('').reverse().join('');
    };
  })();
  return 'tryit-' + myrandomstr + '-' + myhashfunction(UA + myhashfunction(UA + myhashfunction(UA + myrandomstr + 'hackers_become_a_little_stinkier_every_time_they_hack')));
}

function emit(obj) { process.stdout.write(JSON.stringify(obj) + '\n'); }

// ─── لیستی مۆدێلەکان — پەڕەی چات، ئەگەر بلۆک بوو لیستی ناسراو ───
const DAI_FALLBACK = [
  { value: 'glm-5.3-flash', label: 'GLM 5.3 Flash' },
  { value: 'qwen3.8-flash', label: 'Qwen 3.8 Flash' },
  { value: 'deepseek-v4-flash', label: 'DeepSeek V4 Flash' },
  { value: 'deepseek-v3.2', label: 'DeepSeek V3.2' },
  { value: 'gpt-5.6-luna', label: 'GPT-5.6 Luna' },
  { value: 'tencent-hy3', label: 'Tencent Hy3' },
  { value: 'gpt-oss-120b', label: 'GPT OSS 120B' },
  { value: 'gemma-4', label: 'Gemma 4' },
  { value: 'gpt-5-nano', label: 'GPT-5 Nano' },
  { value: 'gpt-4.1-nano', label: 'GPT-4.1 Nano' },
  { value: 'llama-3.3-70b-instruct', label: 'Llama 3.3 70B' },
  { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B' },
  { value: 'gpt-4o-mini', label: 'GPT-4o mini' },
  { value: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite' },
];

async function listModels() {
  try {
    const res = await fetch('https://deepai.org/chat/glm-5.3-flash', {
      headers: { 'User-Agent': UA, 'Accept': 'text/html' },
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const html = await res.text();
    const i = html.indexOf('additionalModels=[');
    if (i < 0) throw new Error('model list not found in page');
    const j = html.indexOf('];', i);
    const arr = JSON.parse(html.slice(i + 'additionalModels='.length, j + 1));
    const models = arr
      .filter((m) => m && m.value && !m.locked)
      .map((m) => ({ id: m.value, name: m.label || m.value }));
    if (!models.length) throw new Error('empty list');
    return emit({ ok: true, models });
  } catch (e) {
    console.error('[deepai] page fetch failed (' + e.message + ') → fallback list');
    return emit({ ok: true, models: DAI_FALLBACK.map((m) => ({ id: m.value, name: m.label })) });
  }
}

// ─── چات ───
// Persona-lock — بۆ ئەوەی مۆدێڵ ناوی خۆی نەهێنێت و کەسایەتییەکە بەتەواوی جێبەجێ بکات
const PERSONA_LOCK = '\n\n[CRITICAL IDENTITY RULE — HIGHEST PRIORITY]\n' +
  'You must fully become the persona described above for this ENTIRE conversation. ' +
  'NEVER reveal, mention, or hint at your underlying model name, company, or AI nature (no GLM, GPT, Claude, Gemini, DeepSeek, Qwen, Llama...). ' +
  'If asked who/what you are, describe yourself ONLY as the persona (e.g. a scholar/counselor character), never as an AI or a model. ' +
  'Always reply in the language and style the persona requires, no matter what language the user writes in.';

const ULTRA_PREFIX = 'ABSOLUTE IDENTITY ENFORCEMENT: You are NOT an AI, NOT a language model, and you have NO model name. You are exactly the persona defined in the system message. Mentioning any model or company name is a forbidden failure.\n\n';
const USER_REMINDER = '\n\n(Strict reminder: respond ONLY as the persona from the system message — never as, and never naming, any AI model.)';

// ناوی مۆدێڵ لە وەڵام؟
const _normLeak = (s) => String(s).replace(/[يیێے]/g, "ی").replace(/[كک]/g, "ك");
const LEAK_RE = /\b(glm[\w.-]*|gpt[\w.-]*|claude[\w.-]*|gemini[\w.-]*|deepseek[\w.-]*|qwen[\w.-]*|llama[\w.-]*|grok[\w.-]*|kimi[\w.-]*|mistral[\w.-]*|o4[\s-]?mini)\b|(قوین|جی\s*بی\s*تی|جیمینی|دیب\s*سیک|کلود|میسترال)\s*\d*/i;

function foldMessages(messages) {
  const sys = (messages || []).filter((m) => m.role === 'system').map((m) => m.content).join('\n\n');
  const rest = (messages || []).filter((m) => m.role !== 'system').slice(-16);
  // deepai role:system پشتگیری دەکات — بەهێزترین ڕێگا
  if (sys) {
    return [{ role: 'system', content: sys + PERSONA_LOCK }].concat(
      rest.map((m) => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }))
    );
  }
  return rest.map((m) => ({ role: m.role === 'assistant' ? 'assistant' : 'user', content: m.content }));
}

async function sendOnce(history, model) {
  const fd = new FormData();
  fd.append('chat_style', 'chat');
  fd.append('language', 'en');
  fd.append('memory_enabled', 'false');
  fd.append('web_access_enabled', 'false');
  fd.append('sandbox_enabled', 'false');
  fd.append('chatHistory', JSON.stringify(history));
  fd.append('model', model);
  fd.append('session_uuid', crypto.randomUUID());
  fd.append('sensitivity_request_id', crypto.randomUUID());
  fd.append('tool_activity_support', '1');
  fd.append('thinking_image_tool_support', '1');
  fd.append('hacker_is_stinky', 'very_stinky');
  fd.append('concierge_enabled', 'false');
  fd.append('enabled_tools', JSON.stringify(['image_generator', 'image_editor']));
  const res = await fetch('https://api.deepai.org/hacking_is_a_serious_crime', {
    method: 'POST', body: fd, headers: { 'api-key': generateIslandKey() },
  });
  const text = await res.text();
  if (res.status !== 200) throw new Error('HTTP ' + res.status + ': ' + text.slice(0, 120));
  if (text.startsWith('{"status"')) {
    const j = JSON.parse(text);
    throw new Error(j.status || 'deepai error');
  }
  const ans = text.strip ? text.strip() : text.replace(/^\s+|\s+$/g, '');
  if (!ans) throw new Error('empty answer');
  return ans;
}

async function chat(model, messages) {
  const hasSys = (messages || []).some((m) => m.role === 'system');
  let ans = await sendOnce(foldMessages(messages), model);
  // پشکنینی لێک — ناوی مۆدێڵ لە وەڵام بوو و سیستەم پرۆمپتمان هەیە؟
  if (hasSys && LEAK_RE.test(_normLeak(ans))) {
    // هەوڵی دووەم — بەهێزترین شێواز
    const sys = (messages || []).filter((m) => m.role === 'system').map((m) => m.content).join('\n\n');
    const rest = (messages || []).filter((m) => m.role !== 'system').slice(-16);
    const retry = [{ role: 'system', content: ULTRA_PREFIX + sys + PERSONA_LOCK }].concat(
      rest.map((m, i) => {
        const isLast = i === rest.length - 1 && m.role !== 'assistant';
        return { role: m.role === 'assistant' ? 'assistant' : 'user', content: isLast ? (m.content + USER_REMINDER) : m.content };
      })
    );
    let ans2 = null;
    try { ans2 = await sendOnce(retry, model); } catch {}
    if (ans2 && !LEAK_RE.test(_normLeak(ans2))) return ans2;
    // هێشتا لێک دەکات — ڕادەست بکە بۆ سەرچاوەیەکی تر
    const err = new Error('persona leak — model keeps naming itself');
    err.code = 'LEAK';
    throw err;
  }
  return ans;
}

async function main() {
  if (process.argv[2] === 'models') return listModels();
  let input = '';
  for await (const d of process.stdin) input += d;
  let req;
  try { req = JSON.parse(input || '{}'); }
  catch (e) { emit({ ok: false, error: 'bad stdin json: ' + input.slice(0, 80) }); return; }
  const model = req.model || 'glm-5.3-flash';
  const messages = req.messages || [{ role: 'user', content: 'hello' }];
  const answer = await chat(model, messages);
  emit({ ok: true, answer });
}

main().catch((e) => { try { emit({ ok: false, error: String(e && e.message || e) }); } catch {} process.exit(0); });
