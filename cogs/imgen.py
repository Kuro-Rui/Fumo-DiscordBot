import asyncio
import base64
import functools
from io import BytesIO
from pathlib import Path
from typing import List, Literal, Optional, Tuple

import discord
from discord import app_commands
from PIL import Image

from cogs.utils.imgen.converters import Model, NemusonaFlags, Prompt
from core import commands
from core.bot import FumoBot
from core.commands import Greedy


class Imgen(commands.Cog):
    """Generate images."""

    def __init__(self, bot: FumoBot):
        super().__init__(bot, discord.PartialEmoji(name="Sakuya", id=935836224483115048))

    @commands.bot_has_permissions(attach_files=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.hybrid_command(usage="<model> <prompt> [flags...]")
    @app_commands.describe(model="The model to use.", prompt="Your prompt.")
    async def generate(
        self,
        ctx: commands.Context,
        model: Model,
        prompt: Greedy[Prompt],
        *,
        flags: NemusonaFlags,
    ):
        """
        Generate a waifu.

        The model can be either `Anything`, `AOM`, or `Nemu`.

        **Flags**
        - `--negative` - What you don't want the bot to include, defaults to nothing.
        - `--cfgscale` - The CFG scale (0 - 20), defaults to 10.
        - `--denoisestrength` - The denoise strength (0.0 - 1.0), defaults to 0.5.
        - `--seed` - The seed to use.

        Powered by [Nemu's Waifu Generator](https://waifus.nemusona.com)
        """
        if not prompt:
            await ctx.reply("You need to provide a prompt.")
            return
        result = await self.generate_ai_image(ctx, model, " ".join(prompt), flags)
        if not result:
            await ctx.reply(
                "An error occurred while generating the image. Please try again later."
            )
            return
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.blurple, label=f"Seed: {result[1]}", disabled=True
            )
        )
        view.add_item(
            discord.ui.Button(label="Nemu's Waifu Generator", url="https://waifus.nemusona.com")
        )
        await ctx.reply(file=result[0], view=view)

    @generate.autocomplete("model")
    async def model_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        if self.bot.is_blacklisted(interaction.user.id):
            return []

        choices = [
            app_commands.Choice(name="Anything V4.5", value="anything"),
            app_commands.Choice(name="AOM3", value="aom"),
            app_commands.Choice(name="Nemu (WIP)", value="nemu"),
        ]
        if current == "":
            return choices
        current = current.lower()
        return [c for c in choices if current in c.name.lower()]

    async def generate_ai_image(
        self,
        ctx: commands.Context,
        model: Literal["anything", "aom", "nemu"],
        prompt: str,
        flags: NemusonaFlags,
    ) -> Optional[Tuple[discord.File, int]]:
        ephemeral = not ctx.channel.is_nsfw()
        async with ctx.typing(ephemeral=ephemeral):
            data = {
                "prompt": prompt,
                "negative_prompt": flags.negative,
                "cfg_scale": flags.cfg_scale,
                "denoising_strength": flags.denoise_strength,
                "seed": flags.seed,
            }
            async with self.bot.session.post(
                f"https://waifus-api.nemusona.com/job/submit/{model}", json=data
            ) as response:
                if response.status == 429:
                    await ctx.reply("Hit the rate limit. Please try again later.")
                    return
                elif response.status == 503:
                    await ctx.reply("Queue is full. Please try again later.")
                elif response.status != 201:
                    await ctx.reply("Something went wrong. Please try again later.")
                    return
                job_id = await response.text()

            for x in range(1, 301):
                async with self.bot.session.get(
                    f"https://waifus-api.nemusona.com/job/status/{model}/{job_id}"
                ) as response:
                    if response.status == 429:
                        await ctx.reply("Hit the rate limit. Please try again later.")
                        return
                    elif response.status != 200:
                        await ctx.reply("Something went wrong. Please try again later.")
                        return
                    status = await response.text()
                    if status == "failed":
                        await ctx.reply("Something went wrong. Please try again later.")
                        return
                    elif status == "completed":
                        break

                    # 5 minutes ig
                    if x == 300:
                        await ctx.reply("Timed out. Please try again later.")
                        return
                    await asyncio.sleep(1)

            async with self.bot.session.get(
                f"https://waifus-api.nemusona.com/job/result/{model}/{job_id}",
            ) as response:
                if response.status == 429:
                    await ctx.reply("Hit the rate limit. Please try again later.")
                    return
                elif response.status != 200:
                    await ctx.reply("Something went wrong. Please try again later.")
                    return
                result = await response.json()
                image = base64.b64decode(result["base64"])
            spoiler = not bool(ctx.interaction) and ephemeral
            file = discord.File(BytesIO(image), filename="image.png", spoiler=spoiler)
            return file, result["seed"]

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command(aliases=["marihat", "hat"], cooldown_after_parsing=True)
    async def marisahat(self, ctx: commands.Context, *, user: discord.User = commands.Author):
        """
        Look at yourself wearing Marisa's hat.

        Credits to dj_tomato on Discord.
        """
        async with ctx.typing():
            avatar = await self.get_avatar(user)
            task = functools.partial(self.generate_marisahat, avatar)
            file = await self.make_image(task)
        if not file:
            await ctx.reply(
                "An error occurred while generating the image. Please try again later."
            )
            return
        await ctx.reply(file=file)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command(aliases=["pic", "picture"], cooldown_after_parsing=True)
    async def polaroid(self, ctx: commands.Context, *, user: discord.User = commands.Author):
        """
        Remilia caughts you in 4K...

        Credits to dj_tomato on Discord.
        """
        async with ctx.typing():
            fp = await self.get_avatar(user)
            task = functools.partial(self.generate_polaroid, fp)
            file = await self.make_image(task)
        if not file:
            await ctx.reply(
                "An error occurred while generating the image. Please try again later."
            )
            return
        await ctx.reply(file=file)

    @commands.bot_has_permissions(attach_files=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_command(aliases=["marisafie"], cooldown_after_parsing=True)
    async def selfie(self, ctx: commands.Context, *, user: discord.User = commands.Author):
        """
        Take a selfie with Marisa!

        Credits to dj_tomato on Discord.
        """
        async with ctx.typing():
            fp = await self.get_avatar(user)
            task = functools.partial(self.generate_selfie, fp)
            file = await self.make_image(task)
        if not file:
            await ctx.reply(
                "An error occurred while generating the image. Please try again later."
            )
            return
        await ctx.reply(file=file)

    async def get_avatar(self, user: discord.User) -> BytesIO:
        avatar = BytesIO()
        display_avatar = user.display_avatar.replace(size=512, static_format="png")
        await display_avatar.save(avatar, seek_begin=True)
        return avatar

    @staticmethod
    def bytes_to_image(fp: BytesIO, size: int) -> Image.Image:
        return Image.open(fp).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)

    def generate_marisahat(self, fp: BytesIO) -> discord.File:
        avatar = self.bytes_to_image(fp, 262)
        image = Image.new("RGBA", (262, 262), None)
        mask = Image.open(Path(__file__).parent / "utils/imgen/marisahat.png").convert("RGBA")
        image.paste(avatar, (0, 0), avatar)
        avatar.close()
        image.paste(mask, (0, 0), mask)
        mask.close()

        fp = BytesIO()
        image.save(fp, "PNG")
        fp.seek(0)
        image.close()
        file = discord.File(fp, "marisahat.png")
        fp.close()
        return file

    def generate_polaroid(self, fp: BytesIO) -> discord.File:
        avatar = self.bytes_to_image(fp, 260)
        image = Image.new("RGBA", (451, 600), None)
        mask = Image.open(Path(__file__).parent / "utils/imgen/polaroid.png").convert("RGBA")
        avatar = avatar.rotate(315, Image.Resampling.NEAREST, expand=1)
        image.paste(avatar, (120, 200), avatar)
        avatar.close()
        image.paste(mask, (0, 0), mask)
        mask.close()

        fp = BytesIO()
        image.save(fp, "PNG")
        fp.seek(0)
        image.close()
        file = discord.File(fp, "polaroid.png")
        fp.close()
        return file

    def generate_selfie(self, fp: BytesIO) -> discord.File:
        avatar = self.bytes_to_image(fp, 577)
        image = Image.new("RGBA", (433, 577), None)
        mask = Image.open(Path(__file__).parent / "utils/imgen/selfie.png").convert("RGBA")
        image.rotate(120, resample=0, expand=0, center=None, translate=None, fillcolor=None)
        image.paste(avatar, (-33, 0), avatar)
        avatar.close()
        image.paste(mask, (0, 0), mask)
        mask.close()

        fp = BytesIO()
        image.save(fp, "PNG")
        fp.seek(0)
        image.close()
        file = discord.File(fp, "selfie.png")
        fp.close()
        return file

    async def make_image(self, task: functools.partial) -> Optional[discord.File]:
        task = self.bot.loop.run_in_executor(None, task)
        try:
            image = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return None
        else:
            return image


async def setup(bot: FumoBot):
    await bot.add_cog(Imgen(bot))
