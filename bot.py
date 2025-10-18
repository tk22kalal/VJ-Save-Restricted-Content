import nest_asyncio
nest_asyncio.apply()

from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

if STRING_SESSION is not None and LOGIN_SYSTEM == False:
        TechVJUser = Client("TechVJ" ,api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
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
        if TechVJUser is not None:
            await TechVJUser.start()
        print('Bot Started Powered By @VJ_Botz')

    async def stop(self, *args):
        if TechVJUser is not None:
            await TechVJUser.stop()
        await super().stop()
        print('Bot Stopped Bye')

if __name__ == "__main__":
    try:
        print("Initializing bot...")
        bot = Bot()
        print("Starting bot...")
        bot.run()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed with error: {e}")
        import traceback
        traceback.print_exc()
        raise

# Don't Remove Credit Tg - @VJ_Botz
# Subscribe YouTube Channel For Amazing Bot https://youtube.com/@Tech_VJ
# Ask Doubt on telegram @KingVJ01
