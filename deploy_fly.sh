#!/bin/bash
# دیپلۆی یەک-فەرمان: ./deploy_fly.sh "<FLY_TOKEN>"
[ -z "$1" ] && { echo "بەکارهێنان: ./deploy_fly.sh <FLY_API_TOKEN>"; exit 1; }
export FLY_API_TOKEN="$1"
export FLY_NO_AGENT=1
cd "$(dirname "$0")"
/home/user/.fly/bin/flyctl deploy --app syuhjsbot-yf --now --strategy immediate 2>&1 | tail -6
echo "── پشکنین ──"
sleep 8
curl -s --max-time 20 https://syuhjsbot-yf.fly.dev/health
