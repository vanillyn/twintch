#!/usr/bin/env bash

set -e

if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

if ! command -v ngrok &>/dev/null; then
    echo "no ngrok."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "no python."
    exit 1
fi

ngrok http 3000 --log=stdout --log-format=json > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

echo "waiting for ngrok..."
for i in $(seq 1 20); do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    tunnels = data.get('tunnels', [])
    for t in tunnels:
        if t.get('proto') == 'https':
            print(t['public_url'])
            break
except:
    pass
" 2>/dev/null)
    if [ -n "$NGROK_URL" ]; then
        break
    fi
    sleep 0.5
done

if [ -z "$NGROK_URL" ]; then
    echo "failed to get ngrok url. check /tmp/ngrok.log"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

export TWITCH_CALLBACK_URL="${NGROK_URL}/webhook/twitch"
echo "ngrok tunnel: $NGROK_URL"
echo "callback url: $TWITCH_CALLBACK_URL"

cleanup() {
    echo "shutting down..."
    kill $NGROK_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

python3 bot.py
