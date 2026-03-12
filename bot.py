import asyncio
import os

import discord
from discord.ext import commands

from src.webserver import app

bot = commands.Bot(command_prefix=">>", intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"logged in as {bot.user}")


async def main():
    config = {"port": 3000, "host": "0.0.0.0"}
    await asyncio.gather(
        bot.start(os.getenv("DISCORD_TOKEN", "none")), app.run_task(**config)
    )


if __name__ == "__main__":
    asyncio.run(main())
