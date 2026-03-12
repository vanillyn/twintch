import discord

from bot import bot


@bot.tree.command(
    name="add_streamer", description="add a streamer to the notification list"
)
async def add_streamer(interaction: discord.Interaction, twitch_username: str):
    await interaction.response.send_message(
        f"now tracking {twitch_username}!", ephemeral=True
    )
