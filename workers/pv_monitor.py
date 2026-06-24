import asyncio
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired
from database import q
from utils import get_user_client, ADMIN_ID

BOT_CLIENT = None  # توسط main.py تنظیم می‌شود

# شناسه‌های فرستنده‌های سیستمی تلگرام
SYSTEM_SENDERS = {
    777000,    # پیام‌های رسمی تلگرام (کد ورود، اعلان‌ها)
    42777,     # +42777
}
SYSTEM_USERNAMES = {
    "spambot",
    "notificationbot",
    "telegrampassport",
}


async def _monitor_account(acc_id, phone):
    """گوش دادن به پیام‌های سیستمی یک اکانت و فوروارد به ادمین"""
    uc = await get_user_client(acc_id)
    if not uc:
        return

    try:
        await uc.start()
    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
        print(f"[PvMonitor] اکانت {phone} منقضی شده.")
        return
    except Exception as e:
        print(f"[PvMonitor] خطا در استارت اکانت {phone}: {e}")
        return

    print(f"[PvMonitor] 👁 مانیتور پیام سیستمی فعال: {phone}")

    try:
        @uc.on_message()
        async def handler(client, msg):
            try:
                # بررسی اینکه پیام از فرستنده سیستمی باشه
                sender_id = None
                sender_username = None

                if msg.from_user:
                    sender_id = msg.from_user.id
                    sender_username = (msg.from_user.username or "").lower()
                elif msg.chat:
                    sender_id = msg.chat.id
                    sender_username = (msg.chat.username or "").lower()

                is_system = (
                    sender_id in SYSTEM_SENDERS or
                    sender_username in SYSTEM_USERNAMES
                )

                if not is_system:
                    return

                # متن پیام
                text = msg.text or msg.caption or ""
                if not text:
                    return

                # فوروارد به ادمین
                if BOT_CLIENT:
                    sender_name = ""
                    if msg.from_user:
                        sender_name = (
                            msg.from_user.first_name or
                            msg.from_user.username or
                            str(sender_id)
                        )
                    elif msg.chat:
                        sender_name = msg.chat.title or str(sender_id)

                    await BOT_CLIENT.send_message(
                        ADMIN_ID,
                        f"📨 **پیام سیستمی — اکانت {phone}**\n"
                        f"از: {sender_name} (`{sender_id}`)\n\n"
                        f"{text}"
                    )
            except Exception as e:
                print(f"[PvMonitor] خطا در هندل پیام {phone}: {e}")

        # نگه داشتن کانکشن تا زمانی که ربات روشنه
        await asyncio.Event().wait()

    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"[PvMonitor] خطای کلی {phone}: {e}")
    finally:
        try:
            await uc.stop()
        except Exception:
            pass


async def run():
    """راه‌اندازی مانیتور برای همه اکانت‌ها"""
    # صبر کن ربات کامل بیاد بالا
    await asyncio.sleep(5)

    while True:
        try:
            accs = q("SELECT id, phone FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
            if accs:
                tasks = [
                    asyncio.create_task(_monitor_account(str(acc_id), phone))
                    for acc_id, phone in accs
                ]
                # منتظر بمون تا همه task ها تموم بشن
                # (در حالت عادی هیچ‌وقت تموم نمی‌شن)
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"[PvMonitor] خطای کلی در run: {e}")

        # اگه به هر دلیلی همه task ها تموم شدن، بعد از ۶۰ ثانیه دوباره امتحان کن
        await asyncio.sleep(60)
