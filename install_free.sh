#!/bin/bash
# ═══ #100: ClawCloud DevBox installer — بێ پارە، بێ Docker، یەک paste ═══
# Args: <TG_FILE_ID> <GITHUB_PAT>
set -e
FID="$1"; PAT="$2"
BOT="8664695955:AAElPxr8spsa--KqsAzHG6Pa4FWnjBmBPQc"
REPO="https://${PAT}@github.com/Yusfkarim/ayai.git"
[ -z "$FID" ] && { echo "❌ file_id"; exit 1; }
[ -z "$PAT" ] && { echo "❌ PAT"; exit 1; }
cd /root
echo "═══ 1/6 کۆد ═══"
rm -rf /opt/bot && git clone -q "$REPO" /opt/bot
cd /opt/bot
echo "═══ 2/6 Python deps (3-5 min) ═══"
pip3 install --no-input -r requirements.txt -q 2>&1 | tail -1 || true
echo "═══ 3/6 Chromium بۆ مینتەر (5-8 min) ═══"
python3 -m playwright install chromium-headless-shell 2>&1 | tail -1 || true
python3 -m playwright install-deps chromium 2>&1 | tail -1 || true
echo "═══ 4/6 گەڕاندنەوەی /data لە TG backup ═══"
mkdir -p /root/botdata
FP=$(curl -s "https://api.telegram.org/bot${BOT}/getFile" -d file_id="${FID}" | python3 -c "import json,sys;print(json.load(sys.stdin)['result']['file_path'])")
curl -sL "https://api.telegram.org/file/bot${BOT}/${FP}" -o /tmp/data.tgz
tar xzf /tmp/data.tgz -C /root/botdata && echo "✅ $(ls /root/botdata | wc -l) فایل گەڕایەوە"
echo "═══ 5/6 کێپەریڤ (restart-proof) ═══"
cat > /root/start_bot.sh <<'SH'
#!/bin/bash
cd /opt/bot
export DATA_DIR=/root/botdata PYTHONUNBUFFERED=1
while true; do
  python3 -u main.py >> /root/bot.log 2>&1
  echo "[$(date)] EXIT=$? — restart 10s" >> /root/bot.log
  sleep 10
done
SH
chmod +x /root/start_bot.sh
# لە هەر session ێکی نوێدا چالاک بێت + ئێستا:
grep -q start_bot.sh /root/.bashrc 2>/dev/null || echo "pgrep -f start_bot.sh >/dev/null || nohup /root/start_bot.sh >/dev/null 2>&1 &" >> /root/.bashrc
pgrep -f "start_bot.sh" >/dev/null || nohup /root/start_bot.sh >/dev/null 2>&1 &
echo "═══ 6/6 چاوەڕوانی بوت (تا 3 min) ═══"
for i in $(seq 1 18); do
  sleep 10
  H=$(curl -s -m 5 http://localhost:8080/health || true)
  if [ -n "$H" ]; then
    echo "✅✅✅ بوت زیندووە: $H"
    echo "⚠️ ئێستا تەنها یەک شت ماوە: Fly بکوژێنەوە (من لە سەندووقەوە دەیکوژێنمەوە)"
    exit 0
  fi
done
echo "⚠️ /health نەگەیشت — ٢٠ دڵنیابە لۆگ بکە:"
tail -40 /root/bot.log
