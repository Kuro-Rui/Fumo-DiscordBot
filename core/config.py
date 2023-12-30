from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import discord

__all__ = ("Config",)


@dataclass
class Config:
    """
    A class to store settings for the bot.

    Attributes
    ----------
    description: str
        The bot's description.
    embed_colour: discord.Colour
        The bot's embed colour.
    mobile: bool
        Whether to use mobile status.
    permissions: discord.Permissions
        The bot's permissions.
    prefix: str
        The bot's prefix.
    redis_uri: str
        The Redis URI.
    token: str
        The bot's token.
    """

    description: str
    embed_colour: discord.Colour = field(metadata={"alias": "embed_color"})
    mobile: bool
    permissions: discord.Permissions
    prefix: str
    redis_uri: str
    token: str

    @classmethod
    def from_json(cls) -> Config:
        """
        Load settings from config.json.

        Please use this instead of initializing the class directly.
        """
        with open(Path(__file__).parent.parent / "config.json") as fp:
            data = json.load(fp)
        decimal = int(data["embed_colour"].lstrip("#"), 16)
        data["embed_colour"] = discord.Colour(decimal)
        permissions = discord.Permissions(data["permissions"])
        data["permissions"] = permissions
        return cls(**data)

    def to_dict(self) -> dict:
        """Turns the Config object to a dict."""
        return {
            "description": self.description,
            "embed_colour": self.embed_colour,
            "mobile": self.mobile,
            "permissions": self.permissions,
            "prefix": self.prefix,
            "redis_uri": self.redis_uri,
            "token": self.token,
        }

    def save(self) -> None:
        """Save settings to config.json"""
        with open(Path(__file__).parent.parent / "config.json", "w") as fp:
            data = self.to_dict()
            data["embed_colour"] = hex(data["embed_colour"].value)[2:]
            data["permissions"] = data["permissions"].value
            json.dump(data, fp, indent=4)
