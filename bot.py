import asyncio
import logging
import os

import discord
from discord.ext import commands

from src.webserver import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">>", intents=intents)


@bot.event
async def on_ready() -> None:
    import src.webserver as _webserver
    from src.notifications import send_live_notification

    _webserver.notify_callback = send_live_notification
    await bot.tree.sync()
    log.info("logged in as %s", bot.user)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    log.error("command error in %s: %s", ctx.command, error)


async def main() -> None:
    from src.db import init_db

    await init_db()
    log.info("db initialized")
    config = {"port": 3000, "host": "0.0.0.0"}
    await asyncio.gather(
        bot.start(os.getenv("DISCORD_TOKEN", "")),
        app.run_task(**config),
    )


import src.commands as _commands  # noqa: E402, F401

if __name__ == "__main__":
    asyncio.run(main())
