import os, time, asyncio
from pyrogram import Client
from database import q, u
from dotenv import load_dotenv
load_dotenv()

API_ID   = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
ADMIN_ID = int(os.environ["ADMIN_ID"])

# ─── step helpers ──────────────────────────────────────────────
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

# ─── user client factory ───────────────────────────────────────
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

# ─── flood-wait helper ──────────────────────────────────────────
async def report_flood(bot_client, acc_display, op_name, e):
    """گزارش محدودیت تلگرام + برگرداندن مدت صبر امن"""
    wait_s = e.value
    safe_s = int(wait_s * 3.5)
    try:
        await bot_client.send_message(
            ADMIN_ID,
            f"❗️ عملیات {op_name} متوقف شد "
            f"شما به محدودیت تلگرام خورده اید به مدت {wait_s} ثانیه\n\n"
            f"جهت جلوگیری از مسدود شدن اکانت ربات پس از {safe_s} ثانیه "
            f"دیگر به عملیات خود ادامه می دهد\n"
            f"👤 اکانت : {acc_display}"
        )
    except Exception:
        pass
    await asyncio.sleep(safe_s)
    return safe_s

# ─── save account ──────────────────────────────────────────────
def save_account(me, session_string, phone):
    u("INSERT INTO accounts (id,phone,name,username,session_string,admin_id,added_at) "
      "VALUES(%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE "
      "name=%s, session_string=%s, status='active'",
      (str(me.id), phone, me.first_name or str(me.id), me.username or "",
       session_string, ADMIN_ID, int(time.time()),
       me.first_name or str(me.id), session_string))
