import asyncio
import importlib
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Coroutine

import aiohttp
import discord
from discord.gateway import DiscordWebSocket
from discord.message import Message
from redis.asyncio import Redis

from . import commands
from .config import Config
from .events import init_events
from .utils.formatting import format_perms
from .utils.websocket import MobileWebSocket

log = logging.getLogger("fumo.core.bot")


class FumoBot(commands.AutoShardedBot):
    """A custom subclass of `commands.AutoShardedBot`."""

    def __init__(self) -> None:
        self._config = Config.from_json()
        super().__init__(
            command_prefix=commands.when_mentioned_or(self._config.prefix),
            description=self._config.description,
            intents=discord.Intents(
                guilds=True,
                members=True,
                emojis=True,
                messages=True,
                message_content=True,
            ),
            allowed_mentions=discord.AllowedMentions(everyone=False, users=True, roles=False),
        )

        self._checked_time_accuracy: datetime | None = None
        self._last_exception: str | None = None
        self._old_identify: Coroutine[Any, Any, None] | None = None
        self._uptime: datetime | None = None

        self._blacklist: set[int] = set()
        self._cooldown = commands.CooldownMapping.from_cooldown(10, 15, commands.BucketType.user)
        self._spam_count = Counter()

        self.lock = asyncio.Lock()
        self.before_invoke(self.before_invoke_hook)
        init_events(self)

    @property
    def config(self) -> Config:
        return self._config

    @config.setter
    def config(self, value: Any) -> None:
        raise RuntimeError("Please don't set the config directly.")

    @property
    def uptime(self) -> datetime:
        return self._uptime

    @uptime.setter
    def uptime(self, value: Any) -> None:
        raise RuntimeError("Please don't set the uptime directly.")

    # Total mess lmfao
    async def monkeypatch_ws(self, *, mobile: bool, reconnect: bool = False):
        if mobile:
            if not self._old_identify:
                self._old_identify = DiscordWebSocket.identify
            DiscordWebSocket.identify = MobileWebSocket.identify
            log.info("DiscordWebSocket has been monkeypatched to mobile.")
        else:
            if self._old_identify:
                DiscordWebSocket.identify = self._old_identify
                self._old_identify = None
                log.info("DiscordWebSocket mobile monkeypatch has been removed.")

        if reconnect:
            log.info("Reconnecting shards...")
            for shard in self.shards.values():
                await shard.reconnect()

    async def start(self) -> None:
        """|coro|

        A shorthand coroutine for :meth:`login` + :meth:`connect`.
        """
        if self._config.mobile:
            await self.monkeypatch_ws(mobile=True)
        await super().start(self._config.token, reconnect=True)

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        self.redis = Redis.from_url(self._config.redis_uri)

        self._blacklist = {int(user_id) for user_id in await self.redis.smembers("blacklist")}

        for file in Path(__file__).parent.parent.glob("cogs/*.py"):
            try:
                await self.load_extension(f"cogs.{file.stem}")
            except Exception as e:
                log.exception("Failed to load %s", file.stem, exc_info=e)

    def add_to_blacklist(self, user: discord.User) -> None:
        self._blacklist.add(user.id)

    def remove_from_blacklist(self, user: discord.User) -> None:
        self._blacklist.remove(user.id)

    @property
    def blacklist(self) -> frozenset[int]:
        return frozenset(self._blacklist)

    def is_blacklisted(self, user: discord.User) -> bool:
        return user.id in self._blacklist

    async def get_context(
        self, origin: discord.Interaction | discord.Message, /, *, cls=commands.Context
    ) -> commands.Context:
        return await super().get_context(origin, cls=cls)

    async def before_invoke_hook(self, ctx: commands.Context) -> None:
        if await self.is_owner(ctx.author):
            return
        if not ctx.guild:
            return
        if ctx.guild.me == ctx.guild.owner:
            return
        required_perms = self._config.permissions
        current_perms = ctx.channel.permissions_for(ctx.guild.me)
        if current_perms.is_superset(required_perms):
            return
        missing_perms = format_perms(
            discord.Permissions(
                (current_perms.value ^ required_perms.value) & required_perms.value
            ),
            True,
        )
        await ctx.send(
            f"Hello there! I'm missing the {missing_perms} permission(s) to function properly.\n"
            "Please check your guild and channel permissions and try again.",
            delete_after=60,
        )

    async def process_commands(self, message: Message) -> None:
        author = message.author
        if not await self.is_owner(author):
            bucket = self._cooldown.get_bucket(message)
            current = message.created_at.timestamp()
            retry_after = bucket and bucket.update_rate_limit(current)
            if retry_after:
                self._spam_count[author.id] += 1
                if self._spam_count[author.id] >= 5:
                    self.add_to_blacklist(author.id)
                    del self._spam_count[author.id]
                    log.warning("Blacklisted %s (%d) for spamming commands.", author, author.id)
                else:
                    guild = message.guild
                    msg = "%s (%d) is spamming in %s (%d). Waiting for %.2f seconds."
                    log.warning(msg, author, author.id, guild, guild.id, retry_after)
                return
            else:
                self._spam_count.pop(author.id, None)

        ctx = await self.get_context(message)
        if ctx.command:
            await self.invoke(ctx)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.is_blacklisted(message.author.id):
            return
        await self.process_commands(message)

    async def _reload_help(self):
        """Reload the help command."""
        importlib.reload(sys.modules["core.commands.help"])
        await self.reload_extension("cogs.info")

    @property
    def invite_url(self) -> str:
        return discord.utils.oauth_url(self.application_id, permissions=self._config.permissions)

    async def _redis_save(self) -> None:
        """Save needed data to Redis."""
        await self.redis.delete("blacklist")
        if self._blacklist:
            await self.redis.sadd("blacklist", *self._blacklist)

        await self.redis.save()
        await self.redis.close()

    async def close(self) -> None:
        log.info("Saving config...")
        self._config.save()

        async with self.lock:
            log.info("Saving data to Redis...")
            await self._redis_save()

        log.info("Shutting down...")
        await self.session.close()
        await super().close()
