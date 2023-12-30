"""
This is a derivative work from PyLav project:
https://github.com/PyLav/PyLav/blob/develop/pylav/constants/misc.py#L5-L14
https://github.com/PyLav/PyLav/blob/develop/pylav/helpers/format/ascii.py

The original copy was distributed under GNU Affero GPL Version 3 and
this derivative work is distributed under GNU GPL Version 3.

PyLav - A Lavalink wrapper library to be used by discord-py bots.
Copyright (C) 2022-Present  Draper (draper@draper.wtf)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import math

__all__ = ("EightBitANSI",)


# https://github.com/PyLav/PyLav/blob/develop/pylav/constants/misc.py#L5-L14
ASCII_COLOURS = {
    "black": (71, 78, 78),
    "red": (209, 50, 47),
    "green": (110, 149, 11),
    "yellow": (176, 117, 28),
    "blue": (42, 102, 195),
    "magenta": (195, 52, 96),
    "cyan": (42, 157, 132),
    "white": (255, 255, 255),
}


# https://github.com/PyLav/PyLav/blob/develop/pylav/helpers/format/ascii.py
class _BackgroundColourCodes:
    """Background colour codes for ANSI escape sequences."""

    dark_blue = "40"
    orange = "41"
    blue = "42"
    turquoise = "43"
    gray = "44"
    indigo = "45"
    light_gray = "46"
    white = "47"


class EightBitANSI:
    """Eight-bit ANSI escape sequences."""

    escape = "\u001b["
    background = _BackgroundColourCodes

    black = "30"
    red = "31"
    green = "32"
    yellow = "33"
    blue = "34"
    magenta = "35"
    cyan = "36"
    white = "37"

    normal = reset = "0"
    bold = "1"
    italic = "3"
    underline = "4"
    default = "39"

    @classmethod
    def colorize(
        cls,
        text: str,
        color: str = "default",
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Colorize a string with ANSI escape sequences."""
        color = [getattr(cls, color, cls.default)]
        if background and (background := getattr(cls.background, background, None)):
            color.append(background)
        if bold:
            color.append(cls.bold)
        if italic:
            color.append(cls.italic)
        if underline:
            color.append(cls.underline)

        color_code = f"{cls.escape}{';'.join(color)}m"
        color_reset = f"{cls.escape}{cls.reset}m"
        text = f"{text}".replace("\n", f"{color_reset}\n{color_code}")

        return f"{color_code}{text}{color_reset}"

    @classmethod
    def paint_black(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string black."""
        return cls.colorize(text, "black", bold, underline, background, italic)

    @classmethod
    def paint_red(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string red."""
        return cls.colorize(text, "red", bold, underline, background, italic)

    @classmethod
    def paint_green(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string green."""
        return cls.colorize(text, "green", bold, underline, background, italic)

    @classmethod
    def paint_yellow(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string yellow."""
        return cls.colorize(text, "yellow", bold, underline, background, italic)

    @classmethod
    def paint_blue(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string blue."""
        return cls.colorize(text, "blue", bold, underline, background, italic)

    @classmethod
    def paint_magenta(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string magenta."""
        return cls.colorize(text, "magenta", bold, underline, background, italic)

    @classmethod
    def paint_cyan(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string cyan."""
        return cls.colorize(text, "cyan", bold, underline, background, italic)

    @classmethod
    def paint_white(
        cls,
        text: str,
        bold: bool = False,
        underline: bool = False,
        background: str = None,
        italic: bool = False,
    ) -> str:
        """Paint a string white."""
        return cls.colorize(text, "white", bold, underline, background, italic)

    @classmethod
    def closest_from_rgb(cls, r: int, g: int, b: int) -> str:
        """Get the closest 4-bit ANSI colour from a given RGB value."""
        return cls.closest_color(r, g, b)

    @classmethod
    def closest_from_hex(cls, value: str) -> str:
        """Get the closest 4-bit ANSI colour from a given hex value."""
        value = value.lstrip("#")
        lv = len(value)
        return cls.closest_color(
            *tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))
        )

    @classmethod
    def closest_color(cls, red: int, green: int, blue: int) -> str:
        """Get the closest 4-bit ANSI colour from a given RGB value."""
        color_diffs = []
        for name, color in ASCII_COLOURS.items():
            cr, cg, cb = color
            color_diff = math.sqrt((red - cr) ** 2 + (green - cg) ** 2 + (blue - cb) ** 2)
            color_diffs.append((color_diff, name))
        return min(color_diffs)[1]
