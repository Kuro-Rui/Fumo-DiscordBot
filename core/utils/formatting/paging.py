"""
This is a derivative work from Red-DiscordBot project:
https://github.com/Cog-Creators/Red-DiscordBot/blob/3.4.19/redbot/core/utils/chat_formatting.py#L268-L338

The original copy was distributed under GNU GPL Version 3 and
this derivative work is distributed under the same license.

Red - A fully customizable Discord bot
Copyright (C) 2017-present  Cog Creators
Copyright (C) 2015-2017  Twentysix

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from typing import Iterator, Sequence

__all__ = ("pagify",)


# Originally, this method has another parameter (escape_mass_mentions), but it's not used
# since Fumo doesn't allow any mass mentions. See core/bot.py line 39 for context.
def pagify(
    text: str,
    delims: Sequence[str] = ["\n"],
    *,
    priority: bool = False,
    page_length: int = 2000,
) -> Iterator[str]:
    """Generate multiple pages from the given text. This does not respect code blocks/inline code.

    Parameters
    ----------
    text : str
        The content to pagify and send.
    delims : `sequence` of `str`, optional
        Characters where page breaks will occur. If no delimiters are found in a page,
        the page will break after ``page_length`` characters.
        By default this only contains the newline.
    priority : `bool`
        Set to :code:`True` to choose the page break delimiter based on the order of ``delims``.
        Otherwise, the page will always break at the last possible delimiter.
    page_length : `int`
        The maximum length of each page. Defaults to 2000.

    Yields
    ------
    `str`
        Pages of the given text.

    """
    in_text = text
    while len(in_text) > page_length:
        this_page_len = page_length
        closest_delim = (in_text.rfind(d, 1, this_page_len) for d in delims)
        if priority:
            closest_delim = next((x for x in closest_delim if x > 0), -1)
        else:
            closest_delim = max(closest_delim)
        closest_delim = closest_delim if closest_delim != -1 else this_page_len
        to_send = in_text[:closest_delim]
        if len(to_send.strip()) > 0:
            yield to_send
        in_text = in_text[closest_delim:]

    if len(in_text.strip()) > 0:
        yield in_text
