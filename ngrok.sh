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

cleanup() {
    echo "shutting down..."
    [ -n "$BOT_PID" ] && kill "$BOT_PID" 2>/dev/null
    [ -n "$NGROK_PID" ] && kill "$NGROK_PID" 2>/dev/null
    wait 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

ngrok http 3000 --log=stdout --log-format=json > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

echo "waiting for ngrok tunnel..."
for i in $(seq 1 20); do
    NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
        | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for t in data.get('tunnels', []):
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
    kill "$NGROK_PID" 2>/dev/null
    exit 1
fi

export TWITCH_CALLBACK_URL="${NGROK_URL}/webhook/twitch"
echo "ngrok tunnel: $NGROK_URL"
echo "callback url: $TWITCH_CALLBACK_URL"

python3 bot.py &
BOT_PID=$!

wait "$BOT_PID"
cleanup
