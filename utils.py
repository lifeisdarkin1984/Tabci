import os, time
from pyrogram import Client
from database import q, u
from dotenv import load_dotenv
load_dotenv()

API_ID   = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

def get_step(uid):
    r = q("SELECT step FROM admins WHERE id=%s", (uid,))
    return r[0][0] if r else "idle"

def get_step_data(uid):
    r = q("SELECT step_data FROM admins WHERE id=%s", (uid,))
    return r[0][0] if r else ""

def set_step(uid, step, data=""):
    u("INSERT INTO admins (id,step,step_data) VALUES(%s,%s,%s) "
      "ON DUPLICATE KEY UPDATE step=%s, step_data=%s",
      (uid, step, data, step, data))

def clear_step(uid):
    set_step(uid, "idle", "")

async def get_user_client(acc_id):
    r = q("SELECT session_string FROM accounts WHERE id=%s", (acc_id,))
    if not r or not r[0][0]:
        return None
    return Client(
        name=f"uc_{acc_id}",
        session_string=r[0][0],
        api_id=API_ID,
        api_hash=API_HASH,
        no_updates=True,
        in_memory=True
    )

def save_account(me, session_string, phone):
    u("INSERT INTO accounts (id,phone,name,username,session_string,admin_id,added_at) "
      "VALUES(%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
      "name=%s, session_string=%s, status='active'",
      (str(me.id), phone, me.first_name or str(me.id), me.username or "",
       session_string, ADMIN_ID, int(time.time()),
       me.first_name or str(me.id), session_string))

async def clear_chat_history(uc, chat_id):
    """
    حذف کامل تاریخچه یک چت (پیوی/ربات).
    توجه: پایروگرام متد delete_history ندارد (فقط raw API messages.DeleteHistory
    و بات‌متد delete_messages وجود دارد)، پس پیام‌ها را می‌خوانیم و دسته‌دسته
    با delete_messages حذف می‌کنیم.
    """
    msg_ids = []
    async for msg in uc.get_chat_history(chat_id):
        msg_ids.append(msg.id)
    for i in range(0, len(msg_ids), 100):
        await uc.delete_messages(chat_id, msg_ids[i:i + 100], revoke=True)
    return len(msg_ids)

# ─── توقف عملیات ──────────────────────────────
stop_all = False

def set_stop(val: bool):
    global stop_all
    stop_all = val

def is_stopped():
    return stop_all


# ─── تشخیص عضویت اجباری بات‌محور (نه از طرف Telegram، بلکه ربات داخل گروه) ──
import re, asyncio as _asyncio

_FORCED_JOIN_LINK_PATTERN = re.compile(r'https?://t\.me/[^\s\]\)\"\']+|@[\w]{4,}')
_FORCED_JOIN_KEYWORDS = ["عضو شو", "عضویت", "join", "membership", "عضو شوید", "عضو کانال"]

async def detect_and_handle_bot_forced_join(uc, chat_id, original_text=None):
    """
    بعد از ارسال پیام به یک گروه، چک می‌کند آیا ربات داخل گروه با درخواست
    عضویت اجباری در یک کانال دیگر پاسخ داده. اگر بله، عضو آن کانال می‌شود
    و در صورت داده‌شدن original_text، پیام اصلی را دوباره ارسال می‌کند.

    خروجی: {"forced_join_detected": bool, "channel": str|None,
            "joined": bool, "resent": bool, "error": str|None}
    """
    result = {"forced_join_detected": False, "channel": None,
              "joined": False, "resent": False, "error": None}
    try:
        sent_time = time.time()
        await _asyncio.sleep(2.5)

        target_msg = None
        async for msg in uc.get_chat_history(chat_id, limit=5):
            if msg.date and msg.date.timestamp() <= sent_time:
                continue
            if msg.from_user and msg.from_user.is_self:
                continue
            if not msg.reply_markup:
                continue
            rows = getattr(msg.reply_markup, 'inline_keyboard', None)
            if not rows:
                continue

            link = None
            for row in rows:
                for btn in row:
                    url = getattr(btn, 'url', None)
                    if url and ("t.me/" in url or url.startswith("@")):
                        link = url
                        break
                if link:
                    break
            if not link:
                continue

            # برای کاهش false-positive، حضور کلمات کلیدی را هم چک می‌کنیم
            msg_text = (msg.text or msg.caption or "").lower()
            if not any(kw in msg_text for kw in _FORCED_JOIN_KEYWORDS):
                continue

            target_msg = msg
            result["channel"] = link
            break

        if not target_msg:
            return result

        result["forced_join_detected"] = True
        found = _FORCED_JOIN_LINK_PATTERN.findall(result["channel"])
        channel = found[0] if found else result["channel"]
        channel_clean = channel.split("t.me/")[-1].lstrip("@") if "t.me/" in channel else channel.lstrip("@")

        try:
            await uc.join_chat(channel_clean)
            result["joined"] = True
        except Exception as e:
            result["error"] = f"join failed: {e}"
            return result

        await _asyncio.sleep(2)

        if original_text:
            try:
                await uc.send_message(chat_id, original_text)
                result["resent"] = True
            except Exception as e:
                result["error"] = f"resend failed: {e}"

    except Exception as e:
        print(f"[ForcedJoinDetect] خطا: {e}")
        result["error"] = str(e)

    return result

