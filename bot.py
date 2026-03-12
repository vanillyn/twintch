import asyncio
import os

import discord
from discord.ext import commands

from src.webserver import app

bot = commands.Bot(command_prefix=">>", intents=discord.Intents.all())


@bot.event
async def on_ready() -> None:
    import src.webserver as _webserver
    from src.notifications import send_live_notification

    _webserver.notify_callback = send_live_notification
    await bot.tree.sync()
    print(f"logged in as {bot.user}")


async def main() -> None:
    from src.db import init_db

    await init_db()
    config = {"port": 3000, "host": "0.0.0.0"}
    await asyncio.gather(
        bot.start(os.getenv("DISCORD_TOKEN", "")),
        app.run_task(**config),
    )


import src.commands as _commands  # noqa: E402, F401

if __name__ == "__main__":
    asyncio.run(main())
