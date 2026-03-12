import hashlib
import hmac
import json
import os
from typing import Any, Awaitable, Callable, Optional

from quart import Quart, request

from db import get_streamer_by_user_id

app = Quart(__name__)
TWITCH_WEBHOOK_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")

notify_callback: Optional[Callable[[str, str, bool], Awaitable[Any]]] = None


def verify_signature(headers, body) -> bool:
    msg_id = headers.get("Twitch-Eventsub-Message-Id", "")
    timestamp = headers.get("Twitch-Eventsub-Message-Timestamp", "")
    signature = headers.get("Twitch-Eventsub-Message-Signature", "")

    hmac_message = (msg_id + timestamp).encode() + body
    expected = (
        "sha256="
        + hmac.new(
            TWITCH_WEBHOOK_SECRET.encode(), hmac_message, hashlib.sha256
        ).hexdigest()
    )

    return hmac.compare_digest(expected, signature)


@app.route("/webhook/twitch", methods=["POST"])
async def twitch_webhook():
    body = await request.get_data()

    if not verify_signature(request.headers, body):
        return "forbidden", 403

    data = json.loads(body)
    msg_type = request.headers.get("Twitch-Eventsub-Message-Type")

    if msg_type == "webhook_callback_verification":
        return data["challenge"], 200

    if msg_type == "notification":
        sub_type = data.get("subscription", {}).get("type")
        if sub_type == "stream.online":
            event = data["event"]
            broadcaster_id = event["broadcaster_user_id"]
            broadcaster_name = event["broadcaster_user_name"]

            streamer = await get_streamer_by_user_id(broadcaster_id)
            if streamer and notify_callback:
                await notify_callback(
                    broadcaster_name,
                    streamer["discord_channel_id"],
                    bool(streamer["ping_everyone"]),
                )

    return "", 204
