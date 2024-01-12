import asyncio
import base64
from io import BytesIO
from typing import Literal, Optional, Tuple

import discord

from core.bot import FumoBot
from core.utils.views import FumoView

from .converters import NemusonaFlags


class RegenerateButton(discord.ui.Button):
    def __init__(
        self,
        bot: FumoBot,
        author: discord.abc.User,
        model: Literal["anything", "aom", "nemu"],
        prompt: str,
        flags: NemusonaFlags,
    ):
        self.author = author
        self.bot = bot
        self.flags = flags
        self.model = model
        self.prompt = prompt
        super().__init__(
            style=discord.ButtonStyle.green,
            label="Regenerate",
            emoji="\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
        )

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        ephemeral = not (isinstance(channel, discord.DMChannel) or channel.is_nsfw())
        await interaction.response.defer(ephemeral=ephemeral, thinking=True)
        # Disable button to prevent spam
        self.disabled = True
        await interaction.followup.edit_message(interaction.message.id, view=self.view)

        result = await self.regenerate_ai_image(interaction)
        if not result:
            return
        embed = discord.Embed(colour=self.bot.config.embed_colour, title=f"Seed: {result[0]}")
        # Not recommended, but this is the only way since the interaction doesn't have command data
        view = FumoView(timeout=60.0)
        view.author = self.author
        view.message = interaction.message
        view.add_item(RegenerateButton(self.bot, self.author, self.model, self.prompt, self.flags))
        view.add_item(
            discord.ui.Button(label="Nemu's Waifu Generator", url="https://waifus.nemusona.com")
        )
        await interaction.followup.send(file=result[1], embed=embed, view=view)

    async def regenerate_ai_image(
        self, interaction: discord.Interaction
    ) -> Optional[Tuple[int, discord.File]]:
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
