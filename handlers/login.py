import time
from pyrogram import Client, filters
from pyrogram.errors import (PhoneNumberInvalid, PhoneCodeInvalid,
    PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid, FloodWait)
from database import q, u
from utils import API_ID, API_HASH, ADMIN_ID, save_account, set_step, clear_step
from keyboards import back_kb, main_menu_kb

pending_clients = {}

def register(app):

    @app.on_message(filters.private & filters.command("start"))
    async def cmd_start(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        u("INSERT INTO admins (id) VALUES(%s) ON DUPLICATE KEY UPDATE step='idle'", (ADMIN_ID,))
        await message.reply(
            "👋 **به تبچی پرسونال خوش آمدید**\n\nیک گزینه را انتخاب کنید:",
            reply_markup=main_menu_kb()
        )

    @app.on_message(filters.private & filters.command("add_account"))
    async def cmd_add(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        set_step(ADMIN_ID, "login_phone")
        await message.reply(
            "📱 **افزودن اکانت جدید**\n\n"
            "شماره تلفن را با کد کشور وارد کنید:\n"
            "مثال: `+989123456789`",
            reply_markup=back_kb("back_main")
        )

    @app.on_message(filters.private & filters.command("list_account"))
    async def cmd_list(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        accs = q("SELECT id,phone,name FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
        if not accs:
            await message.reply("هیچ اکانتی ثبت نشده.\n\nبرای افزودن: /add_account")
            return
        txt = f"📌 **لیست تبچی‌های شما ({len(accs)} اکانت)**\n\n"
        for a in accs:
            txt += f"👤 {a[2]} | `{a[1]}`\n"
        await message.reply(txt)


async def send_code(phone, admin_id):
    temp = Client(f"tmp_{phone.replace('+','')}", api_id=API_ID, api_hash=API_HASH,
                  no_updates=True, in_memory=True)
    await temp.connect()
    sent = await temp.send_code(phone)
    pending_clients[phone] = temp
    u("INSERT INTO pending_logins (phone,admin_id,phone_code_hash,created_at) "
      "VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE phone_code_hash=%s,created_at=%s",
      (phone, admin_id, sent.phone_code_hash, int(time.time()),
       sent.phone_code_hash, int(time.time())))

async def sign_in(phone, code=None, password=None):
    temp = pending_clients.get(phone)
    if not temp:
        return None, "expired"
    row = q("SELECT phone_code_hash FROM pending_logins WHERE phone=%s", (phone,))
    if not row:
        return None, "no_hash"
    try:
        if password:
            await temp.check_password(password)
        else:
            await temp.sign_in(phone, row[0][0], code)
        me = await temp.get_me()
        ss = await temp.export_session_string()
        await temp.disconnect()
        del pending_clients[phone]
        u("DELETE FROM pending_logins WHERE phone=%s", (phone,))
        return (me, ss), None
    except SessionPasswordNeeded:
        return None, "2fa"
    except PhoneCodeInvalid:
        return None, "bad_code"
    except PhoneCodeExpired:
        return None, "expired_code"
    except PasswordHashInvalid:
        return None, "bad_pass"
    except FloodWait as e:
        return None, f"flood:{e.value}"
    except Exception as e:
        return None, str(e)
