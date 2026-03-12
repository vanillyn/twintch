import os

import aiohttp

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET", "")
TWITCH_WEBHOOK_SECRET = os.getenv("TWITCH_WEBHOOK_SECRET", "")
TWITCH_CALLBACK_URL = os.getenv("TWITCH_CALLBACK_URL", "")

_access_token: str = ""


async def get_app_access_token() -> str:
    global _access_token
    if _access_token:
        return _access_token
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://id.twitch.tv/oauth2/token",
            params={
                "client_id": TWITCH_CLIENT_ID,
                "client_secret": TWITCH_CLIENT_SECRET,
                "grant_type": "client_credentials",
            },
        )
        data = await resp.json()
        _access_token = data["access_token"]
        return _access_token


async def get_user_id(username: str) -> tuple[str, str] | None:
    token = await get_app_access_token()
    async with aiohttp.ClientSession() as session:
        resp = await session.get(
            "https://api.twitch.tv/helix/users",
            params={"login": username},
            headers={"Client-Id": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"},
        )
        data = await resp.json()
        if not data.get("data"):
            return None
        user = data["data"][0]
        return user["id"], user["display_name"]


async def subscribe_to_stream_online(broadcaster_user_id: str) -> str | None:
    token = await get_app_access_token()
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://api.twitch.tv/helix/eventsub/subscriptions",
            headers={
                "Client-Id": TWITCH_CLIENT_ID,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "type": "stream.online",
                "version": "1",
                "condition": {"broadcaster_user_id": broadcaster_user_id},
                "transport": {
                    "method": "webhook",
                    "callback": TWITCH_CALLBACK_URL,
                    "secret": TWITCH_WEBHOOK_SECRET,
                },
            },
        )
        if resp.status != 202:
            print(f"eventsub subscribe failed: {resp.status} {await resp.text()}")
            return None
        data = await resp.json()
        return data["data"][0]["id"]


async def unsubscribe(subscription_id: str):
    token = await get_app_access_token()
    async with aiohttp.ClientSession() as session:
        await session.delete(
            "https://api.twitch.tv/helix/eventsub/subscriptions",
            params={"id": subscription_id},
            headers={"Client-Id": TWITCH_CLIENT_ID, "Authorization": f"Bearer {token}"},
        )
