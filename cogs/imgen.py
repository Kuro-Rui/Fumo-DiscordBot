import asyncio
import base64
import functools
import re
from io import BytesIO
from pathlib import Path
from typing import Literal

import discord
from discord import app_commands
from PIL import Image

from cogs.utils.imgen import NEMU_BUTTON, Model, NemusonaFlags, Prompt, RegenerateButton
from core import commands
from core.bot import FumoBot
from core.utils.views import FumoView


class Imgen(commands.Cog):
    """Generate images."""

    def __init__(self, bot: FumoBot):
        super().__init__(bot)

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="Sakuya", id=935836224483115048)

    @commands.bot_has_permissions(attach_files=True)
    @commands.max_concurrency(1, commands.BucketType.user)
    @commands.hybrid_command(usage="<model> <prompt> [flags...]")
    @app_commands.describe(model="The model to use.", prompt="Your prompt.")
    async def generate(
        self,
        ctx: commands.Context,
        model: Model,
        prompt: commands.Greedy[Prompt],
        *,
        flags: NemusonaFlags,
    ):
        """
        Generate a waifu.

        The **model** can be either `Anything`, `AOM`, or `Nemu`.
        The **prompt** can either be a [Danbooru](https://danbooru.donmai.us/) post URL or you can make one yourself.

        **Flags**
        - `--negative`: What you don't want the bot to include, defaults to nothing.
        - `--cfgscale`: The CFG scale (0 - 20), defaults to 10.
        - `--denoisestrength`: The denoise strength (0.0 - 1.0), defaults to 0.5.
        - `--seed`: The seed to use.

        Powered by [Nemu's Waifu Generator](https://waifus.nemusona.com)
        """
        prompt = " ".join(prompt)
        if not prompt:
            await ctx.reply("You need to provide a prompt.")
            return
        if match := re.match(r"https://danbooru\.donmai\.us/posts/(\d+)", prompt):
            post_id = match.group(1)
            prompt, error = await self._get_danbooru_tags(post_id)
            if error:
                await ctx.send(error)
                return
        result = await self.generate_ai_image(ctx, model, prompt, flags)
        if not result:
            return
        seed, file = result
        embed = discord.Embed(color=ctx.embed_color, title=f"Seed: {seed}")
        view = FumoView(timeout=60.0)
        view.add_item(RegenerateButton(self.bot, model, prompt, flags))
        view.add_item(NEMU_BUTTON)
        view.author = ctx.author
        view.message = await ctx.reply(file=file, embed=embed, view=view)

    @generate.autocomplete("model")
    async def model_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
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

    async def _get_danbooru_tags(self, post_id: int) -> tuple[str | None, str | None]:
        """Returns the tags and the error, if there's any."""
        async with self.bot.session.get(
            f"https://danbooru.donmai.us/posts/{post_id}.json"
        ) as response:
            if response.status == 200:
                data = await response.json()
                return ", ".join(data["tag_string"].split()), None
            elif response.status == 404:
                return None, "Post not found."
            else:
                return None, "Something went wrong when extracting tags."

    async def generate_ai_image(
        self,
        ctx: commands.Context,
        model: Literal["anything", "aom", "nemu"],
        prompt: str,
        flags: NemusonaFlags,
    ) -> tuple[int, discord.File] | None:
        ephemeral = not (isinstance(ctx.channel, discord.DMChannel) or ctx.channel.is_nsfw())
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
                if response.status == 503:
                    await ctx.reply("Queue is full. Please try again later.")
                    return
                if response.status != 201:
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
                    if response.status != 200:
                        await ctx.reply("Something went wrong. Please try again later.")
                        return
                    status = await response.text()
                    if status == "failed":
                        await ctx.reply("Something went wrong. Please try again later.")
                        return
                    if status == "completed":
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
                if response.status != 200:
                    await ctx.reply("Something went wrong. Please try again later.")
                    return
                result = await response.json()
                image = base64.b64decode(result["base64"])
            spoiler = not bool(ctx.interaction) and ephemeral
            file = discord.File(BytesIO(image), filename="image.png", spoiler=spoiler)
            return result["seed"], file

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

    async def make_image(self, task: functools.partial) -> discord.File | None:
        task = self.bot.loop.run_in_executor(None, task)
        try:
            image = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return None
        else:
            return image


async def setup(bot: FumoBot):
    await bot.add_cog(Imgen(bot))
