import traceback
from io import StringIO
from typing import Iterable, List

import discord
from discord.app_commands import Command, ContextMenu, Group
from rich.console import Console
from rich.tree import Tree

from core import commands
from core.bot import FumoBot
from core.utils.formatting import code, format_items, format_perms, pagify, wrap
from core.utils.views import ConfirmView


class Owner(commands.Cog):
    """Owner-only commands."""

    def __init__(self, bot: FumoBot):
        super().__init__(bot)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="RemiliaSmile", id=1189592920379105330)

    @commands.is_owner()
    @commands.group(aliases=["bl"], invoke_without_command=True)
    async def blacklist(self, ctx: commands.Context):
        """List all blacklisted users."""
        if not self.bot.blacklist:
            await ctx.send("No users are blacklisted.")
            return

        embeds = []
        embed = discord.Embed(color=ctx.embed_color, title="Blacklisted Users")
        users = []
        unknown = []
        for user_id in self.bot.blacklist:
            if user := self.bot.get_user(user_id):
                users.append(user)
                continue
            unknown.append(user_id)
        pages = []
        if users:
            pages.extend([f"- `{user}` ({user.mention})" for user in users])
        if unknown:
            pages.extend([f"- `{user_id}` (Unknown)" for user_id in unknown])

        for page in pagify("\n".join(pages), page_length=4096):
            embed = embed.copy()
            embed.description = page
            embeds.append(embed)
        await ctx.send_menu(embeds)

    @blacklist.command(name="add")
    async def blacklist_add(self, ctx: commands.Context, *users: discord.User):
        """Blacklist users from using the bot."""
        success = []
        for user in users:
            if user in self.bot.blacklist:
                continue
            self.bot.add_to_blacklist(user.id)
            success.append(user)
        if not success:
            await ctx.cross()
            await ctx.send("Provided users are already blacklisted.")
            return
        await ctx.tick()

    @blacklist.command(name="remove")
    @commands.is_owner()
    async def blacklist_remove(self, ctx: commands.Context, *users: discord.User):
        """Unblacklist users from using the bot."""
        success = []
        for user in users:
            if user not in self.bot.blacklist:
                continue
            self.bot.remove_from_blacklist(user.id)
            success.append(user)
        if not success:
            await ctx.cross()
            await ctx.send("Provided users aren't blacklisted.")
            return
        await ctx.tick()

    @commands.is_owner()
    @commands.group(
        name="commands", aliases=["command", "cmds", "cmd"], invoke_without_command=True
    )
    async def _commands(self, ctx: commands.Context):
        """Commands management."""
        pass

    @_commands.command(name="list")
    async def commands_list(self, ctx: commands.Context):
        """List all commands."""
        tree = Tree("Commands", style="underline green")
        for cog in self.bot.cogs.values():
            branch = tree.add(cog.qualified_name, style="not underline bold red")
            self._rich_walk_commands(sorted(cog.get_commands(), key=lambda c: c.name), branch)
        self._rich_walk_commands(self.bot.commands, tree)
        console = Console(
            color_system="standard",
            file=StringIO(),
            force_terminal=True,
            force_interactive=False,
            width=50,
        )
        console.print(tree)
        embed = discord.Embed(
            color=ctx.embed_color, description=code(console.file.getvalue(), "ansi")
        )
        embed.set_author(name=ctx.me.name, icon_url=ctx.me.avatar.url)
        await ctx.send(embed=embed)

    @commands.is_owner()
    @_commands.group(name="slash", invoke_without_command=True)
    async def commands_slash(self, ctx: commands.Context):
        """Slash commands management."""
        pass

    @commands_slash.command(name="list")
    async def commands_slash_list(self, ctx: commands.Context):
        """List all slash commands and context menus."""
        app_commands = self.bot.tree.get_commands(type=discord.AppCommandType.chat_input)
        message_contexts = self.bot.tree.get_commands(type=discord.AppCommandType.message)
        user_contexts = self.bot.tree.get_commands(type=discord.AppCommandType.user)
        sorted_app_commands = (
            sorted(app_commands, key=lambda c: c.name)
            + sorted(message_contexts, key=lambda c: c.name)
            + sorted(user_contexts, key=lambda c: c.name)
        )
        tree = Tree("Slash Commands and Context Menus", style="underline green")
        self._rich_walk_app_commands(sorted_app_commands, tree)
        console = Console(
            color_system="standard",
            file=StringIO(),
            force_terminal=True,
            force_interactive=False,
            width=50,
        )
        console.print(tree)
        embed = discord.Embed(
            color=ctx.embed_color, description=code(console.file.getvalue(), "ansi")
        )
        embed.set_author(name=ctx.me.name, icon_url=ctx.me.avatar.url)
        await ctx.send(embed=embed)

    def _rich_walk_commands(
        self, cmds: Iterable[commands.Command | commands.Group], tree: Tree
    ) -> None:
        for cmd in cmds:
            if isinstance(cmd, commands.Group):
                branch = tree.add(cmd.name, style="not underline bold yellow")
                self._rich_walk_commands(sorted(cmd.commands, key=lambda c: c.name), branch)
            elif isinstance(cmd, commands.Command):
                tree.add(cmd.name, style="not underline bold white")

    def _rich_walk_app_commands(
        self, app_commands: List[Command | Group | ContextMenu], tree: Tree
    ) -> None:
        for app_command in app_commands:
            if isinstance(app_command, discord.app_commands.Group):
                branch = tree.add(app_command.name, style="not underline bold yellow")
                self._rich_walk_app_commands(
                    sorted(app_command.commands, key=lambda c: c.name), branch
                )
            elif isinstance(app_command, discord.app_commands.Command):
                tree.add(app_command.name, style="not bold white")
            elif isinstance(app_command, discord.app_commands.ContextMenu):
                if app_command.type == discord.AppCommandType.user:
                    tree.add(f"{app_command.name} (User)", style="not underline bold magenta")
                elif app_command.type == discord.AppCommandType.message:
                    tree.add(f"{app_command.name} (Message)", style="not underline bold blue")

    @commands_slash.command(name="sync")
    async def commands_slash_sync(self, ctx: commands.Context, *, guild: discord.Guild = None):
        """Syncs all app commands to Discord."""
        commands = []
        async with ctx.typing():
            commands = await self.bot.tree.sync(guild=guild)
        await ctx.send(f"Synced {len(commands)} app commands.")

    @commands.is_owner()
    @commands.group(aliases=["set", "settings"], invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        """Show the bot's config."""
        config = self.bot.config
        config_dict = {
            "Description": config.description,
            "Embed Colour": "#" + hex(config.embed_colour.value)[2:],
            "Mobile": "Yes" if config.mobile else "No",
            "Permissions": format_perms(config.permissions, True),
            "Prefix": config.prefix,
        }
        embed = discord.Embed(color=ctx.embed_color, title="Bot Configuration")
        for name, value in config_dict.items():
            embed.add_field(name=name, value=value)
        await ctx.send(embed=embed)

    @config.command(name="description")
    async def config_description(self, ctx: commands.Context, *, value: str):
        """Set the bot's config."""
        self.bot.description = value
        self.bot._config.description = value
        await ctx.tick()

    @config.command(name="embedcolour", aliases=["embedcolor", "colour", "color"])
    async def config_embed_colour(self, ctx: commands.Context, *, value: discord.Colour):
        """Set the bot's embed colour."""
        self.bot._config.embed_colour = value
        await ctx.tick()

    @config.command(name="mobile")
    async def config_mobile(self, ctx: commands.Context, *, value: bool):
        """Set whether the bot should be on mobile status or not."""
        if value == self.bot._config.mobile:
            await ctx.tick()
            return
        self.bot._config.mobile = value
        await self.bot.monkeypatch_ws(mobile=value, reconnect=True)
        await ctx.tick()

    @config.command(name="permissions", aliases=["perms"])
    async def config_permissions(self, ctx: commands.Context, *, value: int):
        """Set the bot's permissions."""
        self.bot._config.permissions = discord.Permissions(value)
        await ctx.tick()

    @config.command(name="prefix")
    async def config_prefix(self, ctx: commands.Context, *, value: str):
        """Set the bot's prefix."""
        self.bot._config.prefix = value
        await ctx.tick()

    @commands.is_owner()
    @commands.command(name="load", aliases=["reload"])
    async def load(self, ctx: commands.Context, *cogs: str):
        """Load or reload cogs."""
        cmd = ctx.invoked_with
        methods = {
            "load": self.bot.load_extension,
            "reload": self.bot.reload_extension,
        }
        errors = commands.Paginator(prefix="```py", max_size=1900)
        success = []
        failed = []
        for cog in cogs:
            try:
                await methods[cmd](f"cogs.{cog}")
            except Exception as e:
                failed.append(cog)
                cause = e.__cause__ if e.__cause__ else e
                errors.add_line(
                    "".join(traceback.format_exception(type(cause), cause, cause.__traceback__))
                )
            else:
                success.append(cog)

        pages = []
        if success:
            pages.append(f"Successfully {cmd}ed {format_items([wrap(c, '`') for c in success])}\n")
        if failed:
            pages.append(f"Failed to {cmd} {format_items([wrap(c, '`') for c in failed])}\n")
            pages.extend(errors.pages)
        if len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await ctx.send_menu(pages)

    @commands.is_owner()
    @commands.command(name="unload")
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unload cogs."""
        errors = commands.Paginator(prefix="```py", max_size=1900)
        success = []
        failed = []
        for cog in cogs:
            try:
                await self.bot.unload_extension(f"cogs.{cog}")
            except Exception as e:
                failed.append(cog)
                cause = e.__cause__ if e.__cause__ else e
                errors.add_line(
                    "".join(traceback.format_exception(type(cause), cause, cause.__traceback__))
                )
            else:
                success.append(cog)

        pages = []
        if success:
            pages.append(
                f"Successfully unloaded {format_items([wrap(c, '`') for c in success])}.\n"
            )
        if failed:
            pages.append(f"Failed to unload {format_items([wrap(c, '`') for c in failed])}\n")
            pages.extend(errors.pages)
        if len(pages) == 1:
            await ctx.send(pages[0])
        else:
            await ctx.send_menu(pages)

    @commands.is_owner()
    @commands.command(aliases=["die", "suicide"])
    async def shutdown(self, ctx: commands.Context):
        """Shuts the bot down."""
        embed = discord.Embed(color=ctx.embed_color, title="Are you sure you want to shut down?")
        view = ConfirmView()
        await view.start(ctx, embed=embed)
        await view.wait()
        if view.result:
            embed.title = "Shutting Down..."
            await view.message.edit(embed=embed)
            await self.bot.close()
        else:
            embed.title = "Cancelling..."
            await view.message.edit(embed=embed)


async def setup(bot: FumoBot):
    await bot.add_cog(Owner(bot))
