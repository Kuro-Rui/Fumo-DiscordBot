from typing import Sequence

import discord

__all__ = ("code", "format_items", "format_perms", "shorten", "wrap")


def shorten(text: str, length: int) -> str:
    """Shortens the given text to the given length."""
    text = text.rstrip()
    return text if len(text) <= length else text[: length - 3].rstrip() + "..."


def format_items(items: Sequence[str], *, conjunction: str = "and") -> str:
    """Format the given items into a string."""
    if len(items) == 0:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return ", ".join(items[:-1]) + f", {conjunction} {items[-1]}"


def code(text: str, lang: str = "") -> str:
    """Get the given text in a code block."""
    return f"```{lang}\n{text}\n```"


def wrap(text: str, wrapper: str) -> str:
    """
    Wraps the given text. This is good for markdowns.

    Examples
    --------
        - `wrap("hello", "*")` -> `*hello*`.
        - `wrap("hello", "**__")` -> `**__hello__**`.
    """
    if len(wrapper) == 0:
        return text
    if len(wrapper) == 1:
        return wrapper + text + wrapper
    return wrapper + text + "".join(reversed(wrapper))  # To support markdown formatting


def format_perms(permissions: discord.Permissions, check: bool) -> str:
    perms = dict(permissions)
    perms_list = []
    for key, value in perms.items():
        if value != check:
            continue
        key = key.replace("_", "").capitalize()
        perms_list.append(key.capitalize())
    return format_items(perms_list)
