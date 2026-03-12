from datetime import datetime

import discord

from bot import bot
from src.db import get_streamer
from src.twitch import get_follower_count, get_stream, get_user_info


def build_notification_container(
    stream_url: str,
    profile_pic: str,
    custom_msg: str,
    footer_msg: str,
    stream_title: str,
    game: str,
    thumbnail_url: str,
    relative_ts: str,
    accent_color: int,
) -> discord.ui.Container:
    section = discord.ui.Section(
        discord.ui.TextDisplay(
            f"# {custom_msg}\n[{stream_title}]({stream_url})\nplaying **{game}**"
        ),
        accessory=discord.ui.Thumbnail(media=profile_pic),
    )
    gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(media=thumbnail_url))
    footer_parts = footer_msg + (f" | {relative_ts}" if relative_ts else "")
    footer = discord.ui.TextDisplay(f"-# {footer_parts}")
    action_row = discord.ui.ActionRow(
        discord.ui.Button(
            label="watch live",
            url=stream_url,
            style=discord.ButtonStyle.link,
        )
    )
    return discord.ui.Container(
        section,
        gallery,
        footer,
        action_row,
        accent_color=discord.Color(accent_color),
    )


async def send_live_notification(broadcaster_id: str) -> None:
    streamer = await get_streamer(broadcaster_id)
    if streamer is None:
        return

    channel = bot.get_channel(int(streamer["discord_channel_id"]))
    if not isinstance(channel, discord.TextChannel):
        return

    user_info = await get_user_info(broadcaster_id)
    if user_info is None:
        return

    stream_info = await get_stream(broadcaster_id)
    follower_count = await get_follower_count(broadcaster_id)

    display_name: str = user_info["display_name"]
    profile_pic: str = user_info["profile_image_url"]
    stream_url = f"https://twitch.tv/{streamer['twitch_username']}"
    stream_title = stream_info["title"] if stream_info else "untitled stream"
    game = stream_info["game_name"] if stream_info else "unknown"
    thumbnail_url = (
        stream_info["thumbnail_url"]
        .replace("{width}", "1280")
        .replace("{height}", "720")
        if stream_info
        else profile_pic
    )

    relative_ts = ""
    if stream_info and stream_info.get("started_at"):
        started_at = datetime.fromisoformat(
            stream_info["started_at"].replace("Z", "+00:00")
        )
        relative_ts = f"<t:{int(started_at.timestamp())}:R>"

    custom_msg = streamer["custom_message"].replace("{user}", display_name)
    footer_msg = streamer["footer_message"].replace(
        "{followers}", f"{follower_count:,}"
    )

    container = build_notification_container(
        stream_url=stream_url,
        profile_pic=profile_pic,
        custom_msg=custom_msg,
        footer_msg=footer_msg,
        stream_title=stream_title,
        game=game,
        thumbnail_url=thumbnail_url,
        relative_ts=relative_ts,
        accent_color=int(streamer["accent_color"]),
    )

    ping_role_id = int(streamer["ping_role_id"])
    send_kwargs: dict = {
        "components": [container],
        "flags": discord.MessageFlags(is_components_v2=True),
    }
    if ping_role_id:
        send_kwargs["content"] = f"<@&{ping_role_id}>"

    await channel.send(**send_kwargs)
