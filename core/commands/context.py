from typing import TYPE_CHECKING, Any, List

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from core.bot import FumoBot
from core.utils.views import MenuView


class Context(commands.Context):
    """A custom context class that extends the default one."""

    bot: "FumoBot"

    @property
    def embed_colour(self):
        return self.bot.config.embed_colour

    embed_color = embed_colour

    async def send(self, content: str = None, **kwargs) -> discord.Message:
        """
        This acts the same as `discord.ext.commands.Context.send`, with additional keyword argument.

        filter : `Callable[str]` -> `str`, optional
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
        The difference is that it will send a new message if the reference is not found.

        filter : `Callable[str]` -> `str`, optional
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
        try:
            return await self.send(content, reference=self.message, **kwargs)
        except discord.HTTPException:
            return await self.send(content, **kwargs)

    async def send_menu(
        self,
        pages: List[Any],
        page_start: int = 0,
        timeout: float = 180.0,
        reply: bool = False,
        ephemeral: bool = False,
    ):
        """Sends a menu."""
        view = MenuView(pages, page_start, timeout)
        await view.start(self, reply=reply, ephemeral=ephemeral)

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
