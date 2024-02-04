"""
This is a derivative work from Red-DiscordBot project:
https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/_events.py

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

import logging
import sys
import traceback
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
import rich
from discord.ext.commands.errors import *
from rich.text import Text

from . import commands
from .utils.formatting import format_perms

if TYPE_CHECKING:
    from .bot import FumoBot

log = logging.getLogger("fumo.core.events")

INTRO = r"""
 _____                                    ____   _                              _   ____          _
|  ___| _   _  _ __ ___    ___           |  _ \ (_) ___   ___   ___   _ __   __| | | __ )   ___  | |_
| |_   | | | || '_ ` _ \  / _ \   _____  | | | || |/ __| / __| / _ \ | '__| / _` | |  _ \  / _ \ | __|
|  _|  | |_| || | | | | || (_) | |_____| | |_| || |\__ \| (__ | (_) || |   | (_| | | |_) || (_) || |_
|_|     \__,_||_| |_| |_| \___/          |____/ |_||___/ \___| \___/ |_|    \__,_| |____/  \___/  \__|
"""


def init_events(bot: "FumoBot"):
    @bot.event
    async def on_connect():
        if bot._uptime is None:
            log.info("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        try:
            if bot._uptime is not None:
                return
            bot._uptime = datetime.now(tz=timezone.utc)
            log.info("Loaded %d cogs with %d commands", len(bot.cogs), len(bot.commands))
            rich_console = rich.get_console()
            rich_console.print(INTRO, style="bright_red", markup=False, highlight=False)
            if bot.invite_url:
                invite = Text(bot.invite_url, style="link")
                rich_console.print(f"Invite URL: {invite}")
        except Exception as exc_info:
            log.critical("The bot failed to get ready!", exc_info=exc_info)
            sys.exit(1)

    @bot.event
    async def on_message(message: discord.Message):
        await bot.process_commands(message)
        discord_now = message.created_at
        if (
            not bot._checked_time_accuracy
            or (discord_now - timedelta(minutes=60)) > bot._checked_time_accuracy
        ):
            system_now = datetime.now(tz=timezone.utc)
            diff = abs((discord_now - system_now).total_seconds())
            if diff > 60:
                log.warning(
                    "Detected significant difference (%d seconds) in system clock to discord's clock. "
                    "Any time sensitive code may fail.",
                    diff,
                )
            bot._checked_time_accuracy = discord_now

    @bot.event
    async def on_command_error(ctx: commands.Context, exception: CommandError):
        if hasattr(ctx.command, "on_error"):
            return
        if ctx.cog and ctx.cog.has_error_handler():
            return
        converter = getattr(ctx.current_parameter, "converter", None)
        argument = ctx.current_argument
        if isinstance(exception, CommandNotFound):
            return
        elif isinstance(exception, DisabledCommand):
            await ctx.reply("That command is disabled.")
        elif isinstance(exception, NSFWChannelRequired):
            await ctx.reply("That command is only available in NSFW channels.")
        elif isinstance(exception, NoPrivateMessage):
            await ctx.reply("That command is not available in DMs.")
        elif isinstance(exception, PrivateMessageOnly):
            await ctx.reply("That command is only available in DMs.")
        elif isinstance(exception, BotMissingPermissions):
            embed = discord.Embed(color=discord.Color.red(), title="Missing Permissions")
            embed.description = (
                "I require the {missing} permission{s} to run that command.".format(
                    missing=format_perms(exception.missing, True),
                    s="" if bin(exception.missing.value).count("1") == 1 else "s",
                )
            )
            await ctx.reply(embed=embed)
        elif isinstance(exception, CommandOnCooldown):
            if ctx.author.id in bot.owner_ids:
                ctx.command.reset_cooldown(ctx)
                new_ctx = await bot.get_context(ctx.message)
                await bot.invoke(new_ctx)
                return
            delay = discord.utils.format_dt(
                datetime.utcnow() + timedelta(seconds=exception.retry_after), "R"
            )
            await ctx.reply(
                f"This command is on cooldown. Try again {delay}.",
                delete_after=exception.retry_after,
                mention_author=False,
            )
        elif isinstance(exception, MaxConcurrencyReached):
            if exception.per is commands.BucketType.default:
                if exception.number > 1:
                    message = (
                        "Too many people using this command.\n"
                        "It can only be used **__{number} times__** concurrently."
                    ).format(number=exception.number)
                else:
                    message = (
                        "Too many people using this command.\n"
                        "It can only be used once concurrently."
                    )
            elif exception.per in (commands.BucketType.user, commands.BucketType.member):
                if exception.number > 1:
                    message = (
                        "That command is still completing.\n"
                        "It can only be used **__{number} times per {type}__** concurrently."
                    ).format(number=exception.number, type=exception.per.name)
                else:
                    message = (
                        "That command is still completing.\n"
                        "It can only be used **__once per {type}__** concurrently."
                    ).format(type=exception.per.name)
            else:
                if exception.number > 1:
                    message = (
                        "Too many people using this command.\n"
                        "It can only be used **__{number} times per {type}__** concurrently."
                    ).format(number=exception.number, type=exception.per.name)
                else:
                    message = (
                        "Too many people using this command.\n"
                        "It can only be used **__once per {type}__** concurrently."
                    ).format(type=exception.per.name)
            await ctx.reply(message)
        elif isinstance(exception, (MissingRequiredArgument, TooManyArguments)):
            await ctx.send_help(ctx.command)
        elif isinstance(exception, MissingRequiredAttachment):
            await ctx.reply("You are missing a required attachment.")
        elif isinstance(error, commands.UserInputError):
            await ctx.send_help()
        elif isinstance(exception, BadArgument):
            if isinstance(exception.__cause__, ValueError):
                if converter not in (int, float):
                    return
                await ctx.reply(f'"{argument}" is not a number.')
            if isinstance(converter, commands.Range):
                if converter.annotation is int:
                    if converter.min == 0 and converter.max is None:
                        message = "Argument `{parameter_name}` must be a positive integer."
                    elif converter.min is None and converter.max is not None:
                        message = "Argument `{parameter_name}` must be an integer no more than {maximum}."
                    elif converter.min is not None and converter.max is None:
                        message = "Argument `{parameter_name}` must be an integer no less than {minimum}."
                    elif converter.max is not None and converter.min is not None:
                        message = "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
                elif converter.annotation is float:
                    if converter.min == 0 and converter.max is None:
                        message = "Argument `{parameter_name}` must be a positive number."
                    elif converter.min is None and converter.max is not None:
                        message = (
                            "Argument `{parameter_name}` must be a number no more than {maximum}."
                        )
                    elif converter.min is not None and converter.max is None:
                        message = (
                            "Argument `{parameter_name}` must be a number no less than {minimum}."
                        )
                    elif converter.max is not None and converter.min is not None:
                        message = "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
                elif converter.annotation is str:
                    if exception.minimum is None and exception.maximum is not None:
                        message = "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                    elif exception.minimum is not None and exception.maximum is None:
                        message = "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                    elif exception.maximum is not None and exception.minimum is not None:
                        message = "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
                message = message.format(
                    maximum=converter.max,
                    minimum=converter.min,
                    parameter_name=ctx.current_parameter.name,
                )
                await ctx.reply(message)
                return
            if exception.args:
                await ctx.send_help(ctx.command, exception.args[0])
                return
            await ctx.send_help(ctx.command)
        elif isinstance(exception, RangeError):
            if isinstance(exception.value, int):
                if exception.minimum == 0 and exception.maximum is None:
                    message = "Argument `{parameter_name}` must be a positive integer."
                elif exception.minimum is None and exception.maximum is not None:
                    message = (
                        "Argument `{parameter_name}` must be an integer no more than {maximum}."
                    )
                elif exception.minimum is not None and exception.maximum is None:
                    message = (
                        "Argument `{parameter_name}` must be an integer no less than {minimum}."
                    )
                elif exception.maximum is not None and exception.minimum is not None:
                    message = "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
            elif isinstance(exception.value, float):
                if exception.minimum == 0 and exception.maximum is None:
                    message = "Argument `{parameter_name}` must be a positive number."
                elif exception.minimum is None and exception.maximum is not None:
                    message = (
                        "Argument `{parameter_name}` must be a number no more than {maximum}."
                    )
                elif exception.minimum is not None and exception.maximum is None:
                    message = (
                        "Argument `{parameter_name}` must be a number no less than {maximum}."
                    )
                elif exception.maximum is not None and exception.minimum is not None:
                    message = "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
            elif isinstance(exception.value, str):
                if exception.minimum is None and exception.maximum is not None:
                    message = "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                elif exception.minimum is not None and exception.maximum is None:
                    message = "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                elif exception.maximum is not None and exception.minimum is not None:
                    message = "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
            message = message.format(
                maximum=exception.maximum,
                minimum=exception.minimum,
                parameter_name=ctx.current_parameter.name,
            )
            await ctx.reply(message)
            return
        elif isinstance(exception, CommandInvokeError):
            exc_info = exception.original
            cmd = ctx.command.qualified_name
            log.exception('Exception in command "%s"', cmd, exc_info=exc_info)
            error = f'Exception in command "{cmd}"\n'
            error += "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
            bot._last_exception = error
        else:
            log.exception(type(exception).__name__, exc_info=exception)
