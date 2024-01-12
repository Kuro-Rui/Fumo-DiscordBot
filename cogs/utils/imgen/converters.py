from __future__ import annotations

from core import commands


class Model(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument = argument.lower()
        if argument in ("anything", "aom", "nemu"):
            return argument
        raise commands.BadArgument("Invalid model.")


class Prompt(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> str:
        argument = argument.replace("—", "--")  # For iOS' weird smart punctuation
        if argument.startswith("--"):
            raise commands.BadArgument("Please write a prompt first.")
        return argument


class NemusonaFlags(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    negative: str = commands.flag(
        aliases=["n"], default="", description="What you don't want the bot to include."
    )
    cfg_scale: int = commands.flag(
        name="cfgscale",
        aliases=["cfgs", "cs"],
        default=10,
        converter=commands.Range[int, 0, 20],
        description="The CFG scale.",
    )
    denoise_strength: float = commands.flag(
        name="denoisestrength",
        aliases=["denoisingstrength", "ds"],
        default=0.5,
        converter=commands.Range[float, 0.0, 1.0],
        description="The denoise strength.",
    )
    seed: int = commands.flag(default=-1, description="The seed to use.")

    async def convert(self, ctx: commands.Context, argument: str) -> NemusonaFlags:
        return await super().convert(ctx, argument.replace("—", "--"))
