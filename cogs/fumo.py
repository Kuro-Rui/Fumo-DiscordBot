import json
import random
from datetime import datetime
from typing import Literal

import aiohttp
import discord

from core import commands
from core.bot import FumoBot


class Fumo(commands.Cog):
    """Get random Fumos."""

    def __init__(self, bot: FumoBot):
        self.fumos: dict[str, list[str]] = {}
        self.is_friday = lambda: datetime.today().weekday() == 4
        super().__init__(bot)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="Cirno", id=935836292653146123)

    async def fetch_fumos(self) -> None:
        async with self.bot.session.get(
            "https://raw.githubusercontent.com/Kuro-Rui/Kuro-Cogs/main/fumo/data/fumos.json"
        ) as response:
            try:
                response.raise_for_status()
            except aiohttp.ClientResponseError as exc_info:
                self._log.exception("Failed to fetch Fumos", exc_info=exc_info)
            self.fumos = json.loads(await response.text())
        self._log.info("Successfully fetched %d Fumos.", sum(len(l) for l in self.fumos.values()))

    async def cog_load(self) -> None:
        super().cog_load()
        await self.fetch_fumos()

    @commands.command()
    async def random(self, ctx: commands.Context):
        """Get a random Fumo"""

        await self.summon_fumo(ctx)

    @commands.command()
    async def image(self, ctx: commands.Context):
        """Get a random Fumo image"""

        await self.summon_fumo(ctx, "Image")

    @commands.command()
    async def gif(self, ctx: commands.Context):
        """Get a random Fumo GIF"""

        await self.summon_fumo(ctx, "GIF")

    @commands.command()
    async def video(self, ctx: commands.Context):
        """Get a random Fumo video"""

        await self.summon_fumo(ctx, "Video")

    @commands.check(lambda ctx: datetime.today().weekday() == 4)
    @commands.command()
    async def friday(self, ctx: commands.Context):
        """Get a random Fumo Friday video"""

        await self.summon_fumo(ctx, "FUMO FRIDAY")

    async def get_fumos(
        self, content_type: Literal["Image", "GIF", "Video", "FUMO FRIDAY"] = None
    ) -> list[str]:
        if not self.fumos:
            await self.fetch_fumos()
        if not content_type:
            fumos = self.fumos["Image"] + self.fumos["GIF"] + self.fumos["Video"]
            if self.is_friday():
                fumos.extend(self.fumos["FUMO FRIDAY"])
            return fumos
        fumos = self.fumos[content_type]
        if content_type == "Video" and self.is_friday():
            fumos.extend(self.fumos["FUMO FRIDAY"])
        return fumos

    async def summon_fumo(
        self,
        ctx: commands.Context,
        content_type: Literal["Image", "GIF", "Video", "FUMO FRIDAY"] = None,
    ) -> None:
        all_fumos = await self.get_fumos(content_type)
        url = random.choice(all_fumos)
        title = f"Here's a Random Fumo! ᗜˬᗜ"
        if content_type:
            title = f"Here's a Random Fumo {content_type}! ᗜˬᗜ"
            if content_type == "FUMO FRIDAY":
                title = "Happy Fumo Friday! ᗜˬᗜ"
        types = {
            "jpg": "Image",
            "png": "Image",
            "gif": "GIF",
            "mp4": "Video",
            "mov": "Video",
        }
        if types[url[-3:]] != "Video":
            embed = discord.Embed(color=ctx.embed_color, title=title)
            embed.set_image(url=url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"**{title}**\n{url}")


async def setup(bot: FumoBot):
    await bot.add_cog(Fumo(bot))
