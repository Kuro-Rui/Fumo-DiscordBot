import logging
from io import BytesIO

import discord
import jishaku
from jishaku.cog import OPTIONAL_FEATURES, STANDARD_FEATURES
from jishaku.features.baseclass import Feature

from core import commands
from core.bot import FumoBot
from core.utils.views import CloseButton, FumoView

jishaku.Flags.RETAIN = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.FORCE_PAGINATOR = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.USE_ANSI_ALWAYS = True


class Jishaku(*STANDARD_FEATURES, *OPTIONAL_FEATURES):
    """The Jishaku debug and diagnostic commands."""

    _log = logging.getLogger("fumo.cogs.jishaku")
    emoji = discord.PartialEmoji(name="Jishaku", id=1174195607997521960)

    def cog_load(self) -> None:
        self._log.info("Loaded %s", self.qualified_name)

    def cog_unload(self) -> None:
        self._log.info("Unloaded %s", self.qualified_name)

    @Feature.Command(parent="jsk", name="traceback", aliases=["tb"])
    async def jsk_traceback(self, ctx: commands.Context):
        """Shows the last command exception that has occured, if any."""
        exception = ctx.bot._last_exception
        if not exception:
            await ctx.reply("No exception has occurred yet.")
            return
        view = FumoView()
        view.add_item(CloseButton())
        await view.start(
            ctx, file=discord.File(BytesIO(exception.encode("utf-8")), "exception.py")
        )


async def setup(bot: FumoBot):
    await bot.add_cog(Jishaku(bot=bot))
