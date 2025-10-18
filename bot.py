# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01

import asyncio
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

# If the repo's original code used lowercase names this would raise NameError.
# Use the uppercase names imported from config (API_ID, API_HASH).
if STRING_SESSION is not None and LOGIN_SYSTEM == False:
    TechVJUser = Client(
        "TechVJ",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=STRING_SESSION
    )
else:
    TechVJUser = None


class Bot(Client):

    def __init__(self):
        super().__init__(
            "techvj login",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="TechVJ"),
            workers=150,
            sleep_threshold=5
        )

    async def start(self):
        await super().start()
        print('Bot Started Powered By @VJ_Botz')

    async def stop(self, *args):
        await super().stop()
        print('Bot Stopped Bye')


async def _main():
    """
    Start optional user client (STRING_SESSION) then start the bot client
    and wait forever. On shutdown, stop the clients cleanly.
    """
    # Start user client if provided
    if TechVJUser is not None:
        await TechVJUser.start()
        print("User session started (STRING_SESSION)")

    # Start bot
    bot = Bot()
    await bot.start()

    # Keep running until cancelled (SIGINT/SIGTERM)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        # Stop bot and user clients in reverse order
        await bot.stop()
        if TechVJUser is not None:
            await TechVJUser.stop()


if __name__ == "__main__":
    # Safely run _main() whether there's an existing running loop or not.
    # This avoids "RuntimeError: This event loop is already running".
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # In environments where an event loop is already running (interactive
        # shells or some hosting environments), schedule the coroutine instead
        # of calling asyncio.run(), which raises the RuntimeError seen in the logs.
        asyncio.create_task(_main())
    else:
        # Normal blocking run for scripts/processes
        asyncio.run(_main())

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
