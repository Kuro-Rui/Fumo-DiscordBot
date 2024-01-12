import sys
import time
from datetime import datetime, timezone

import discord
import humanize
import jishaku
from discord import app_commands

from core import commands
from core.bot import FumoBot
from core.commands.help import FumoHelp
from core.utils.formatting import code


class Info(commands.Cog):
    """Information related commands."""

    def __init__(self, bot: FumoBot):
        super().__init__(bot)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="KokoroThink", id=1174520928768638996)

    def cog_load(self) -> None:
        super().cog_load()
        self.old_help_command = self.bot.help_command
        self.bot.help_command = FumoHelp()
        self.bot.help_command.cog = self

    def cog_unload(self) -> None:
        super().cog_unload()
        self.bot.help_command = self.old_help_command
        self.bot.help_command.cog = None
        self.bot.tree.remove_command("help")

    @app_commands.command(name="help")
    @app_commands.describe(category_or_command="The category or command to get help for.")
    async def _help(self, interaction: discord.Interaction, category_or_command: str | None):
        """Shows help about the bot, a category, or a command."""
        ctx = await self.bot.get_context(interaction, cls=commands.Context)
        if category_or_command:
            await ctx.send_help(category_or_command)
            return
        await ctx.send_help()

    @_help.autocomplete("category_or_command")
    async def _help_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if self.bot.is_blacklisted(interaction.user.id):
            return []

        assert self.bot.help_command
        help_command = self.bot.help_command.copy()
        help_command.context = await self.bot.get_context(interaction, cls=commands.Context)

        if current == "":
            return [
                app_commands.Choice(name=cog.qualified_name, value=cog.qualified_name)
                for cog in await help_command.filter_cogs(self.bot.cogs.values(), sort=True)
            ]
        current = current.lower()
        current.replace("jsk", "jishaku")
        return [
            app_commands.Choice(name=command.qualified_name, value=command.qualified_name)
            for command in await help_command.filter_commands(self.bot.walk_commands(), sort=True)
            if current in command.qualified_name
        ][:25]

    @commands.hybrid_command(aliases=["about"])
    async def info(self, ctx: commands.Context):
        """Get information about the bot."""
        embed = discord.Embed(color=ctx.embed_color)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.description = (
            "Fumos are a line of high-quality plush character figures. "
            "Fumos exist for multiple franchises, but most notably the "
            "**[Touhou Project](https://en.touhouwiki.net/wiki/Touhou_Wiki)**.\n\n"
            "Fumo bot itself is a bot with a lot of fun Fumo related commands ᗜˬᗜ"
        )
        if owner := self.bot.get_user(self.bot.owner_id):
            embed.add_field(name="Developer", value=f"{owner.name} ({owner.mention})")

        python_emoji = discord.PartialEmoji(name="Python", id=917079498636279868)
        python_url = "https://www.python.org/downloads/release/python-{}{}{}".format(
            *sys.version_info[:3]
        )
        python_version = "[`{}.{}.{}`]({})".format(*sys.version_info[:3], python_url)
        dpy_emoji = discord.PartialEmoji(name="discordpy", id=917079482148458557)
        dpy_repo = "https://github.com/Rapptz/discord.py"
        dpy_version = "[`{}`]({})".format(discord.__version__, dpy_repo)
        jishaku_emoji = discord.PartialEmoji(name="Jishaku", id=1174195607997521960)
        jishaku_repo = "https://github.com/Gorialis/jishaku"
        jishaku_version = "[`{}`]({})".format(jishaku.__version__, jishaku_repo)
        embed.add_field(
            name="Libraries",
            value=(
                f"{python_emoji} Python {python_version}\n"
                f"{dpy_emoji} discord.py {dpy_version}\n"
                f"{jishaku_emoji} jishaku {jishaku_version}"
            ),
            inline=False,
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command()
    async def invite(self, ctx: commands.Context):
        """Get the bot's invite link."""
        invite = discord.utils.oauth_url(
            self.bot.application_id, permissions=self.bot.config.permissions
        )
        await ctx.reply(f"[Click here to invite me!]({invite})", ephemeral=True)

    @commands.hybrid_command()
    @app_commands.describe(show_shards="Whether to show the bot's shards latency.")
    async def ping(self, ctx: commands.Context, show_shards: bool = False):
        """
        Get the bot's latency.

        **Description**
        - `Discord WS`: WebSocket latency. This is how fast bot will receive events from Discord.
        - `Typing`: Time taken to send message.
        - `Message`: Difference between your command message and message with ping.
        """
        show_shards = len(self.bot.latencies) > 1 and show_shards
        pings = {"Discord WS": "", "Typing": "", "Message": ""}
        # This is better for the first scenario since the bot isn't big yet :p
        if not show_shards:
            pings["Discord WS"] = f"{round(self.bot.latency * 1000, 2)} ms"
        else:
            pings["Discord WS"] = "\n".join(
                [f"Shard {shard}: {ping} ms" for shard, ping in self.bot.latencies]
            )

        embed = discord.Embed(title="Pinging...", color=discord.Color.red())
        before = time.monotonic()
        message = await ctx.reply(embed=embed)
        after = time.monotonic()
        pings["Typing"] = f"{round((after - before) * 1000, 2)} ms"

        diff = (message.created_at - ctx.message.created_at).total_seconds()
        pings["Message"] = f"{round(diff * 1000, 2)} ms"
        embed = discord.Embed(title="Pong!", color=ctx.embed_color)
        for name, value in pings.items():
            embed.add_field(name=name, value=code(value, "py"))
        await message.edit(embed=embed)

    @commands.hybrid_command()
    async def uptime(self, ctx: commands.Context):
        """Shows the bot's uptime."""
        timedelta = datetime.now(tz=timezone.utc) - self.bot.uptime
        uptime = humanize.precisedelta(timedelta, format="%d")
        since = discord.utils.format_dt(self.bot.uptime, "F")
        embed = discord.Embed(color=ctx.embed_color, title=f"{ctx.me.name} has been up for:")
        embed.description = f"{uptime}\nSince {since}"
        await ctx.reply(embed=embed)


async def setup(bot: FumoBot):
    await bot.add_cog(Info(bot))
