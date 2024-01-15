import asyncio
import base64
from io import BytesIO
from typing import Literal

import discord

from core.bot import FumoBot
from core.utils.views import FumoView

from .converters import NemusonaFlags

NEMU_BUTTON = discord.ui.Button(label="Nemu's Waifu Generator", url="https://waifus.nemusona.com")


class RegenerateButton(discord.ui.Button):
    def __init__(
        self,
        bot: FumoBot,
        model: Literal["anything", "aom", "nemu"],
        prompt: str,
        flags: NemusonaFlags,
    ):
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Regenerate",
            emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
        )
        self.bot = bot
        self.flags = flags
        self.model = model
        self.prompt = prompt

    async def callback(self, interaction: discord.Interaction):
        # Disable button to prevent spam
        self.disabled = True
        ephemeral = interaction.message.flags.ephemeral
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        await interaction.followup.edit_message(interaction.message.id, view=self.view)

        result = await self.regenerate_ai_image(interaction)
        if not result:
            return
        seed, file = result
        embed = discord.Embed(colour=self.bot.config.embed_colour, title=f"Seed: {seed}")
        view = FumoView(timeout=60.0)
        view.add_item(RegenerateButton(self.bot, self.model, self.prompt, self.flags))
        view.add_item(NEMU_BUTTON)
        view.author = self.view.author
        view.message = await interaction.followup.send(file=file, embed=embed, view=view)

    async def regenerate_ai_image(
        self, interaction: discord.Interaction
    ) -> tuple[int, discord.File] | None:
        data = {
            "prompt": self.prompt,
            "negative_prompt": self.flags.negative,
            "cfg_scale": self.flags.cfg_scale,
            "denoising_strength": self.flags.denoise_strength,
            "seed": self.flags.seed,
        }
        async with self.bot.session.post(
            f"https://waifus-api.nemusona.com/job/submit/{self.model}", json=data
        ) as response:
            if response.status == 429:
                await interaction.followup.send("Hit the rate limit. Please try again later.")
                return
            if response.status == 503:
                await interaction.followup.send("Queue is full. Please try again later.")
                return
            if response.status != 201:
                await interaction.followup.send("Something went wrong. Please try again later.")
                return
            job_id = await response.text()

        for x in range(1, 301):
            async with self.bot.session.get(
                f"https://waifus-api.nemusona.com/job/status/{self.model}/{job_id}"
            ) as response:
                if response.status == 429:
                    await interaction.followup.send("Hit the rate limit. Please try again later.")
                    return
                if response.status != 200:
                    await interaction.followup.send(
                        "Something went wrong. Please try again later."
                    )
                    return
                status = await response.text()
                if status == "failed":
                    await interaction.followup.send(
                        "Something went wrong. Please try again later."
                    )
                    return
                if status == "completed":
                    break

                # 5 minutes ig
                if x == 300:
                    await interaction.followup.send("Timed out. Please try again later.")
                    return
                await asyncio.sleep(1)

        async with self.bot.session.get(
            f"https://waifus-api.nemusona.com/job/result/{self.model}/{job_id}",
        ) as response:
            if response.status == 429:
                await interaction.followup.send("Hit the rate limit. Please try again later.")
                return
            if response.status != 200:
                await interaction.followup.send("Something went wrong. Please try again later.")
                return
            result = await response.json()
            image = base64.b64decode(result["base64"])
        file = discord.File(BytesIO(image), filename="image.png")
        return result["seed"], file
