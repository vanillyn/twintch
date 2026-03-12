import discord
from discord.ext import commands

from bot import bot
from src.db import (
    add_streamer,
    get_streamer,
    get_streamer_by_username,
    remove_streamer,
    update_streamer,
)
from src.notifications import send_live_notification
from src.twitch import (
    get_user_id,
    get_user_info,
    subscribe_to_stream_online,
    unsubscribe,
)


async def build_config_embed(twitch_user_id: str, profile_pic: str) -> discord.Embed:
    streamer = await get_streamer(twitch_user_id)
    assert streamer is not None
    channel_val = (
        f"<#{streamer['discord_channel_id']}>"
        if int(streamer["discord_channel_id"])
        else "not set"
    )
    role_val = (
        f"<@&{streamer['ping_role_id']}>" if int(streamer["ping_role_id"]) else "none"
    )
    embed = discord.Embed(
        title=f"configuring {streamer['twitch_username']}",
        color=discord.Color(int(streamer["accent_color"])),
    )
    embed.set_thumbnail(url=profile_pic)
    embed.add_field(name="channel", value=channel_val, inline=True)
    embed.add_field(name="role", value=role_val, inline=True)
    embed.add_field(
        name="color", value=f"#{int(streamer['accent_color']):06x}", inline=True
    )
    embed.add_field(
        name="message", value=f"`{streamer['custom_message']}`", inline=False
    )
    embed.add_field(
        name="footer", value=f"`{streamer['footer_message']}`", inline=False
    )
    return embed


async def _refresh_panel(
    twitch_user_id: str,
    profile_pic: str,
    message: discord.Message,
) -> None:
    embed = await build_config_embed(twitch_user_id, profile_pic)
    view = ConfigView(twitch_user_id, profile_pic)
    await message.edit(embed=embed, view=view)


class EditMessageModal(discord.ui.Modal, title="edit message"):
    content = discord.ui.TextInput(
        label="custom message",
        placeholder="{user} is live",
        max_length=100,
    )

    def __init__(
        self,
        twitch_user_id: str,
        current: str,
        profile_pic: str,
        config_message: discord.Message,
    ) -> None:
        super().__init__()
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic
        self.config_message = config_message
        self.content.default = current

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await update_streamer(self.twitch_user_id, custom_message=self.content.value)
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)


class EditFooterModal(discord.ui.Modal, title="edit footer"):
    content = discord.ui.TextInput(
        label="footer message",
        placeholder="{followers} followers",
        max_length=100,
    )

    def __init__(
        self,
        twitch_user_id: str,
        current: str,
        profile_pic: str,
        config_message: discord.Message,
    ) -> None:
        super().__init__()
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic
        self.config_message = config_message
        self.content.default = current

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await update_streamer(self.twitch_user_id, footer_message=self.content.value)
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)


class EditColorModal(discord.ui.Modal, title="edit color"):
    content = discord.ui.TextInput(
        label="accent color (hex)",
        placeholder="#9b59b6",
        min_length=4,
        max_length=7,
    )

    def __init__(
        self,
        twitch_user_id: str,
        current_color: int,
        profile_pic: str,
        config_message: discord.Message,
    ) -> None:
        super().__init__()
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic
        self.config_message = config_message
        self.content.default = f"#{current_color:06x}"

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            color = int(self.content.value.lstrip("#"), 16)
        except ValueError:
            await interaction.response.send_message("invalid hex color", ephemeral=True)
            return
        await update_streamer(self.twitch_user_id, accent_color=color)
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)


class ChannelSelectView(discord.ui.View):
    def __init__(
        self,
        twitch_user_id: str,
        profile_pic: str,
        config_message: discord.Message,
    ) -> None:
        super().__init__(timeout=60)
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic
        self.config_message = config_message

    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text],
        placeholder="pick a channel",
    )
    async def select_channel(
        self,
        interaction: discord.Interaction,
        select: discord.ui.ChannelSelect,
    ) -> None:
        await update_streamer(
            self.twitch_user_id, discord_channel_id=select.values[0].id
        )
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)
        self.stop()


class RoleSelectView(discord.ui.View):
    def __init__(
        self,
        twitch_user_id: str,
        profile_pic: str,
        config_message: discord.Message,
    ) -> None:
        super().__init__(timeout=60)
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic
        self.config_message = config_message

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="pick a role")
    async def select_role(
        self,
        interaction: discord.Interaction,
        select: discord.ui.RoleSelect,
    ) -> None:
        await update_streamer(self.twitch_user_id, ping_role_id=select.values[0].id)
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)
        self.stop()

    @discord.ui.button(label="no role", style=discord.ButtonStyle.danger)
    async def no_role(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        await update_streamer(self.twitch_user_id, ping_role_id=0)
        await interaction.response.defer(ephemeral=True)
        await _refresh_panel(self.twitch_user_id, self.profile_pic, self.config_message)
        self.stop()


class ConfigView(discord.ui.View):
    def __init__(self, twitch_user_id: str, profile_pic: str) -> None:
        super().__init__(timeout=600)
        self.twitch_user_id = twitch_user_id
        self.profile_pic = profile_pic

    @discord.ui.button(label="set channel", style=discord.ButtonStyle.secondary, row=0)
    async def set_channel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        assert interaction.message is not None
        view = ChannelSelectView(
            self.twitch_user_id, self.profile_pic, interaction.message
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="set role", style=discord.ButtonStyle.secondary, row=0)
    async def set_role(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        assert interaction.message is not None
        view = RoleSelectView(
            self.twitch_user_id, self.profile_pic, interaction.message
        )
        await interaction.response.send_message(view=view, ephemeral=True)

    @discord.ui.button(label="edit message", style=discord.ButtonStyle.secondary, row=0)
    async def edit_message_btn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        assert interaction.message is not None
        streamer = await get_streamer(self.twitch_user_id)
        assert streamer is not None
        await interaction.response.send_modal(
            EditMessageModal(
                self.twitch_user_id,
                str(streamer["custom_message"]),
                self.profile_pic,
                interaction.message,
            )
        )

    @discord.ui.button(label="edit footer", style=discord.ButtonStyle.secondary, row=1)
    async def edit_footer_btn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        assert interaction.message is not None
        streamer = await get_streamer(self.twitch_user_id)
        assert streamer is not None
        await interaction.response.send_modal(
            EditFooterModal(
                self.twitch_user_id,
                str(streamer["footer_message"]),
                self.profile_pic,
                interaction.message,
            )
        )

    @discord.ui.button(label="edit color", style=discord.ButtonStyle.secondary, row=1)
    async def edit_color_btn(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        assert interaction.message is not None
        streamer = await get_streamer(self.twitch_user_id)
        assert streamer is not None
        await interaction.response.send_modal(
            EditColorModal(
                self.twitch_user_id,
                int(streamer["accent_color"]),
                self.profile_pic,
                interaction.message,
            )
        )

    @discord.ui.button(label="done", style=discord.ButtonStyle.success, row=1)
    async def done(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        self.stop()
        await interaction.response.edit_message(view=None)


@bot.command(name="setup")
async def setup_cmd(ctx: commands.Context, username: str) -> None:
    result = await get_user_id(username)
    if result is None:
        await ctx.send(f"couldn't find twitch user '{username}'")
        return
    user_id, display_name = result
    if await get_streamer(user_id) is not None:
        await ctx.send(f"{display_name} is already being tracked")
        return
    await add_streamer(user_id, display_name, ctx.channel.id)
    sub_id = await subscribe_to_stream_online(user_id)
    if sub_id:
        await update_streamer(user_id, subscription_id=sub_id)
    user_info = await get_user_info(user_id)
    profile_pic = str(user_info["profile_image_url"]) if user_info else ""
    embed = await build_config_embed(user_id, profile_pic)
    view = ConfigView(user_id, profile_pic)
    await ctx.send(
        f"added **{display_name}** — configure below:", embed=embed, view=view
    )


@bot.command(name="edit")
async def edit_cmd(ctx: commands.Context, username: str) -> None:
    streamer = await get_streamer_by_username(username)
    if streamer is None:
        await ctx.send(f"no streamer named '{username}' found")
        return
    user_info = await get_user_info(str(streamer["twitch_user_id"]))
    profile_pic = str(user_info["profile_image_url"]) if user_info else ""
    embed = await build_config_embed(str(streamer["twitch_user_id"]), profile_pic)
    view = ConfigView(str(streamer["twitch_user_id"]), profile_pic)
    await ctx.send(embed=embed, view=view)


@bot.command(name="remove")
async def remove_cmd(ctx: commands.Context, username: str) -> None:
    streamer = await get_streamer_by_username(username)
    if streamer is None:
        await ctx.send(f"no streamer named '{username}' found")
        return
    sub_id = str(streamer["subscription_id"])
    if sub_id:
        await unsubscribe(sub_id)
    await remove_streamer(str(streamer["twitch_user_id"]))
    await ctx.send(f"removed **{streamer['twitch_username']}**")


@bot.command(name="test")
async def test_cmd(ctx: commands.Context, username: str) -> None:
    streamer = await get_streamer_by_username(username)
    if streamer is None:
        await ctx.send(f"no streamer named '{username}' found")
        return
    if not int(streamer["discord_channel_id"]):
        await ctx.send("set a channel first with `>>edit`")
        return
    await send_live_notification(str(streamer["twitch_user_id"]))
    await ctx.send("test sent", delete_after=5)
