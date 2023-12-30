"""
This is a derivative work from Red-DiscordBot project:
https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/logging.py

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

import contextlib
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import rich
from rich import console
from rich._log_render import LogRender
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.style import Style
from rich.text import Text
from rich.theme import Theme
from rich.traceback import PathHighlighter, Traceback

__all__ = ("setup_logging",)


# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/logging.py#L160-L197
class RichLogRender(LogRender):
    def __call__(
        self,
        console,
        renderables,
        log_time=None,
        time_format=None,
        level="",
        path=None,
        line_no=None,
        link_path=None,
        logger_name=None,
    ):
        output = Text()
        if self.show_time:
            log_time = log_time or console.get_datetime()
            log_time_display = log_time.strftime(time_format or self.time_format)
            if log_time_display == self._last_time:
                output.append(" " * (len(log_time_display) + 1))
            else:
                output.append(f"{log_time_display} ", style="log.time")
                self._last_time = log_time_display
        if self.show_level:
            # The space needs to be added separately so that log level is colored by rich.
            output.append(level)
            output.append(" ")
        if logger_name:
            output.append(f"[{logger_name}] ", style="bright_black")

        output.append(*renderables)
        if self.show_path and path:
            path_text = Text()
            path_text.append(path, style=f"link file://{link_path}" if link_path else "")
            if line_no:
                path_text.append(f":{line_no}")
            output.append(path_text)
        return output


# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/logging.py#L151-L157
class RichTraceback(Traceback):
    # DEP-WARN
    @console.group()
    def _render_stack(self, stack):
        for obj in super()._render_stack.__wrapped__(self, stack):
            if obj != "":
                yield obj


# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/logging.py#L200-L279
class RichLoggerHandler(RichHandler):
    """Adaptation of Rich's RichHandler to manually adjust the path to a logger name"""

    def __init__(self):
        super().__init__(show_path=False, highlighter=NullHighlighter(), rich_tracebacks=True)
        self._log_render = RichLogRender(
            show_time=self._log_render.show_time,
            show_level=self._log_render.show_level,
            show_path=self._log_render.show_path,
            level_width=self._log_render.level_width,
        )

    def get_level_text(self, record: logging.LogRecord) -> Text:
        level_text = super().get_level_text(record)
        level_text.stylize("bold")
        return level_text

    def emit(self, record: logging.LogRecord) -> None:
        """Invoked by logging."""
        path = Path(record.pathname).name
        level = self.get_level_text(record)
        message = self.format(record)
        time_format = None if self.formatter is None else self.formatter.datefmt
        log_time = datetime.fromtimestamp(record.created)

        traceback = None
        if self.rich_tracebacks and record.exc_info and record.exc_info != (None, None, None):
            exc_type, exc_value, exc_traceback = record.exc_info
            assert exc_type is not None
            assert exc_value is not None
            traceback = RichTraceback.from_exception(
                exc_type,
                exc_value,
                exc_traceback,
                width=self.tracebacks_width,
                extra_lines=self.tracebacks_extra_lines,
                theme=self.tracebacks_theme,
                word_wrap=self.tracebacks_word_wrap,
                show_locals=self.tracebacks_show_locals,
                locals_max_length=self.locals_max_length,
                locals_max_string=self.locals_max_string,
                indent_guides=False,
            )
            message = record.getMessage()

        use_markup = getattr(record, "markup", self.markup)
        if use_markup:
            text = Text.from_markup(message)
        else:
            text = Text(message)

        if self.highlighter:
            text = self.highlighter(text)
        if self.KEYWORDS:
            text.highlight_words(self.KEYWORDS, "logging.keyword")

        self.console.print(
            self._log_render(
                self.console,
                [text],
                log_time=log_time,
                time_format=time_format,
                level=level,
                path=path,
                line_no=record.lineno,
                link_path=record.pathname if self.enable_link_path else None,
                logger_name=record.name,
            ),
            soft_wrap=True,
        )
        if traceback:
            self.console.print(traceback)


# https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/logging.py#L282-L381
@contextlib.contextmanager
def setup_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    logging.captureWarnings(True)
    logging.getLogger("discord").setLevel(logging.INFO)
    logging.getLogger("discord.http").setLevel(logging.WARNING)

    try:
        rich_console = rich.get_console()
        rich.reconfigure(tab_size=4)
        rich_console.push_theme(
            Theme(
                {
                    "log.time": Style(dim=True),
                    "logging.level.warning": Style(color="white", bgcolor="yellow"),
                    "logging.level.critical": Style(color="white", bgcolor="red"),
                    "logging.level.verbose": Style(color="magenta", italic=True, dim=True),
                    "logging.level.trace": Style(color="white", italic=True, dim=True),
                    "repr.number": Style(color="cyan"),
                    "repr.url": Style(underline=True, italic=True, bold=False, color="cyan"),
                }
            )
        )
        rich_console.file = sys.stdout

        # This is a terrible solution, but it's the best we can do to make the paths in tracebacks to be visible.
        # Rich uses `pygments.string` style  which is fine, but it also uses this highlighter
        # which dims most of the path and therefore makes it unreadable on Mac.
        PathHighlighter.highlights = []

        stdout_handler = RichLoggerHandler()
        rich_formatter = logging.Formatter("{message}", datefmt="[%Y-%m-%d %X]", style="{")
        stdout_handler.setFormatter(rich_formatter)
        root_logger.addHandler(stdout_handler)

        max_bytes = 16 * 1024 * 1024  # 16 MiB
        file_handler = RotatingFileHandler(
            filename="fumo.log",
            mode="w",
            maxBytes=max_bytes,
            backupCount=5,
            encoding="utf-8",
        )
        file_formatter = logging.Formatter(
            "[{asctime}] [{levelname}] {name}: {message}",
            datefmt="%Y-%m-%d %X",
            style="{",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        yield
    finally:
        handlers = root_logger.handlers[:]
        for hdlr in handlers:
            hdlr.close()
            root_logger.removeHandler(hdlr)
