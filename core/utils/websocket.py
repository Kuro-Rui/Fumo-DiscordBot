import sys

from discord.gateway import DiscordWebSocket, _log

__all__ = ("MobileWebSocket",)


# This monkeypatch for overriding the DiscordWebSocket.identify payload later to allow mobile status
# This is actually undocumented by Discord (and maybe against their ToS, who knows)
class MobileWebSocket(DiscordWebSocket):
    async def identify(self) -> None:
        """Sends the IDENTIFY packet."""
        payload = {
            "op": self.IDENTIFY,
            "d": {
                "token": self.token,
                "properties": {
                    "os": sys.platform,
                    "browser": "Discord iOS",  # Discord Android also works, but I prefer iOS
                    "device": "discord.py",
                },
                "compress": True,
                "large_threshold": 250,
            },
        }

        if self.shard_id is not None and self.shard_count is not None:
            payload["d"]["shard"] = [self.shard_id, self.shard_count]

        state = self._connection
        if state._activity is not None or state._status is not None:
            payload["d"]["presence"] = {
                "status": state._status,
                "game": state._activity,
                "since": 0,
                "afk": False,
            }

        if state._intents is not None:
            payload["d"]["intents"] = state._intents.value

        await self.call_hooks("before_identify", self.shard_id, initial=self._initial_identify)
        await self.send_as_json(payload)
        _log.debug("Shard ID %s has sent the IDENTIFY payload.", self.shard_id)
