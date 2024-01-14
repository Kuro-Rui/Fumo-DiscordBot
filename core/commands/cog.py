import inspect
import logging
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from ..bot import FumoBot

__all__ = ("Cog",)


class Cog(commands.Cog):
    """A custom subclass of `commands.Cog`."""

    def __init__(self, bot: "FumoBot") -> None:
        self._log = logging.getLogger(f"fumo.cogs.{self.qualified_name.lower()}")
        self.bot = bot
        super().__init__()

    @property
    def display_emoji(self) -> str | discord.Emoji | discord.PartialEmoji:
        raise NotImplementedError()

    def cog_load(self) -> None:
        self._log.info("Loaded %s", self.qualified_name)

    def cog_unload(self) -> None:
        self._log.info("Unloaded %s", self.qualified_name)

    @property
    def help(self) -> str | None:
        doc = self.__doc__
        if doc:
            return inspect.cleandoc(doc)

    @property
    def all_commands(self) -> dict[str, commands.Command]:
        return {cmd.name: cmd for cmd in self.__cog_commands__}
