import nest_asyncio
nest_asyncio.apply()

import asyncio
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
        self.keepalive_task = None

    async def keepalive_ping(self):
        """Periodic keepalive to prevent connection timeout during long operations"""
        while True:
            try:
                await asyncio.sleep(600)
                if self.is_connected:
                    try:
                        await self.get_me()
                    except Exception as e:
                        print(f"Keepalive ping failed: {e}")
                        try:
                            await self.start()
                            print("Reconnected after keepalive failure")
                        except Exception as reconnect_error:
                            print(f"Reconnection failed: {reconnect_error}")
                if TechVJUser is not None:
                    try:
                        if TechVJUser.is_connected:
                            await TechVJUser.get_me()
                        else:
                            print("TechVJUser disconnected, attempting to reconnect...")
                            await TechVJUser.start()
                            print("TechVJUser reconnected successfully")
                    except Exception as e:
                        print(f"TechVJUser keepalive ping failed: {e}")
                        try:
                            if not TechVJUser.is_connected:
                                await TechVJUser.start()
                                print("TechVJUser reconnected after failure")
                        except Exception as reconnect_error:
                            print(f"TechVJUser reconnection failed: {reconnect_error}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Keepalive task error: {e}")
                await asyncio.sleep(60)

    async def start(self):
            
        await super().start()
        if TechVJUser is not None:
            await TechVJUser.start()
        
        if self.keepalive_task is None or self.keepalive_task.done():
            self.keepalive_task = asyncio.create_task(self.keepalive_ping())
        
        print('Bot Started Powered By @VJ_Botz')

    async def stop(self, *args):
        if self.keepalive_task is not None and not self.keepalive_task.done():
            self.keepalive_task.cancel()
            try:
                await self.keepalive_task
            except asyncio.CancelledError:
                pass
        
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
