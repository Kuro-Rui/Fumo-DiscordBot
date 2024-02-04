from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .help import FumoHelp
    from ..bot import FumoBot
from ..utils.views import MenuView


class Context(commands.Context):
    """A custom context class that extends the default one."""

    bot: "FumoBot"

    @property
    def embed_colour(self) -> discord.Colour:
        return self.bot.config.embed_colour

    embed_color = embed_colour

    async def send(self, content: str = None, **kwargs) -> discord.Message:
        """
        This acts the same as `discord.ext.commands.Context.send`, with additional keyword argument.

        filter: `Callable[str]` -> `str`, optional
            A function which is used to filter the ``content`` before it is sent.
            This must take a single `str` as an argument, and return the processed `str`.
            When `None` is passed, ``content`` won't be touched. Defaults to `None`.
        """
        if content:
            _filter = kwargs.pop("filter", None)
            if _filter:
                content = _filter(str(content))
        mention_author = kwargs.pop("mention_author", False)
        return await super().send(content, mention_author=mention_author, **kwargs)

    async def reply(self, content: str = None, **kwargs) -> discord.Message:
        """
        This acts almost the same as `discord.ext.commands.Context.reply`.
        The difference is this will send a new message if the reference is not found.

        filter: `Callable[str]` -> `str`, optional
            A function which is used to filter the ``content`` before it is sent.
            This must take a single `str` as an argument, and return the processed `str`.
            When `None` is passed, ``content`` won't be touched. Defaults to `None`.
        """
        if content:
            _filter = kwargs.pop("filter", None)
            if _filter:
                content = _filter(str(content))
        if self.interaction:
            return await self.send(content, **kwargs)
        kwargs.update({"reference": self.message})
        try:
            return await self.send(content, **kwargs)
        except discord.HTTPException:
            del kwargs["reference"]
            return await self.send(content, **kwargs)

    async def send_menu(
        self,
        pages: list[Any],
        page_start: int = 0,
        *,
        timeout: float = 180.0,
        ephemeral: bool = False,
    ):
        """Sends a menu."""
        view = MenuView(pages, page_start, timeout=timeout)
        await view.start(self, ephemeral=ephemeral)

    async def edit(self, message: discord.Message, **kwargs) -> discord.Message | None:
        """
        Edits a message, ignoring any exceptions. See `discord.Message.edit` method for kwargs.

        Returns the message if it was successful, `None` otherwise.
        """
        try:
            new = await message.edit(**kwargs)
        except discord.NotFound:
            return None
        except discord.HTTPException:
            return None
        return new

    async def delete(self, message: discord.Message, *, delay: float | None = None) -> bool:
        """
        Deletes a message after a delay, ignoring any exceptions.

        Returns `True` if it was successful, `False` otherwise.
        """
        try:
            await message.delete(delay=delay)
        except discord.NotFound:
            return True
        except discord.HTTPException:
            return False
        return True

    async def react(
        self, emoji: discord.Emoji | discord.PartialEmoji | discord.Reaction | str
    ) -> bool:
        """
        Adds a reaction to the command message.

        Returns `True` if it was successful, `False` otherwise.
        """
        try:
            await self.message.add_reaction(emoji)
        except (discord.HTTPException, discord.Forbidden):
            return False
        else:
            return True

    async def tick(self) -> bool:
        """
        Adds a tick reaction to the command message.

        Returns `True` if it was successful, `False` otherwise.
        """
        return await self.react("\N{WHITE HEAVY CHECK MARK}")

    async def cross(self) -> bool:
        """
        Adds a cross reaction to the command message.

        Returns `True` if it was successful, `False` otherwise.
        """
        return await self.react("\N{CROSS MARK}")

    async def send_help(
        self,
        help_for: commands.Command | commands.Group | commands.Cog | str | None = None,
        details: str | None = None,
    ) -> None:
        """Sends help for a command or a cog with details, if any."""
        hc: "FumoHelp" = self.bot.help_command.copy()
        hc.context = self
        if not help_for:
            await hc.prepare_help_command(self)
            try:
                await hc.send_bot_help(hc.get_bot_mapping(), details=details)
            except commands.CommandError as error:
                await hc.on_help_command_error(self, error)
                return

        cog_or_command = help_for
        if isinstance(help_for, str):
            cog_or_command = self.bot.get_cog(help_for) or self.bot.get_command(help_for)
        if not cog_or_command:
            return
        await hc.prepare_help_command(self, cog_or_command.qualified_name)
        try:
            if hasattr(cog_or_command, "__cog_commands__"):
                await hc.send_cog_help(cog_or_command, details=details)
            elif isinstance(cog_or_command, commands.Group):
                await hc.send_group_help(cog_or_command, details=details)
            elif isinstance(cog_or_command, commands.Command):
                await hc.send_command_help(cog_or_command, details=details)
            else:
                return
        except commands.CommandError as error:
            await hc.on_help_command_error(self, error)
