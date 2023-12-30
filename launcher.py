import asyncio
import logging

import uvloop

from core.bot import FumoBot
from core.utils.logging import setup_logging

log = logging.getLogger("fumo.launcher")

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

if __name__ == "__main__":
    bot = FumoBot()
    with setup_logging():
        asyncio.run(bot.start())
