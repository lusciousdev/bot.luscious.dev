import os
import sys

import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

from bots.generic.commands import BotCommand
from bots.generic.twitch import TwitchBot


class LusciousTwitchBot(TwitchBot):
    pass


def main() -> None:
    async def runner() -> None:
        async with LusciousTwitchBot(bot_name = "bot.luscious.dev", verbose = False) as bot:
            await bot.create()
            await bot.start(with_adapter = False)

    try:
        asyncio.run(runner())
    except KeyboardInterrupt:
        print("Shutting down due to KeyboardInterrupt...")

if __name__ == "__main__":
    main()
