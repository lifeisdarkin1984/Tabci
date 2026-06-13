import asyncio, os
from pyrogram import Client, idle
from dotenv import load_dotenv
from database import init_db

load_dotenv()

API_ID    = int(os.environ["API_ID"])
API_HASH  = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

from handlers import login, text_handler, callbacks
from workers import secretary, scheduler, global_scheduler

async def main():
    init_db()
    app = Client(
        "tabchi_bot",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN
    )

    login.register(app)
    text_handler.register(app)
    callbacks.register(app)

    await app.start()
    print("✅ Tabchi Personal bot is running...")

    await asyncio.gather(
        secretary.run(),
        scheduler.run(),
        global_scheduler.run(app),
        idle(),
    )

    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
