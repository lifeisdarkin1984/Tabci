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

# ─── توقف عملیات ──────────────────────────────
stop_all = False

def set_stop(val: bool):
    global stop_all
    stop_all = val

def is_stopped():
    return stop_all

# ─── سیستم تشخیص خطر بن ──────────────────────
# {acc_id: {"count": N, "cooldown_until": timestamp}}
_flood_counters: dict = {}

FLOOD_THRESHOLD = 5      # تعداد FloodWait پشت سر هم برای کنار گذاشتن
COOLDOWN_HOURS  = 2      # مدت کنار گذاشتن (ساعت)

def record_flood(acc_id: str) -> bool:
    """
    ثبت یک FloodWait برای اکانت.
    اگر True برگرداند یعنی اکانت وارد cooldown شد.
    """
    now = int(time.time())
    entry = _flood_counters.get(acc_id, {"count": 0, "cooldown_until": 0})

    # اگه cooldown فعاله، چیزی تغییر نمیده
    if entry["cooldown_until"] > now:
        return True

    entry["count"] += 1
    if entry["count"] >= FLOOD_THRESHOLD:
        entry["cooldown_until"] = now + COOLDOWN_HOURS * 3600
        entry["count"] = 0
        _flood_counters[acc_id] = entry
        print(f"[BanGuard] اکانت {acc_id} وارد cooldown {COOLDOWN_HOURS} ساعته شد")
        return True

    _flood_counters[acc_id] = entry
    return False

def is_in_cooldown(acc_id: str) -> bool:
    """True اگر اکانت الان در cooldown باشد"""
    entry = _flood_counters.get(acc_id)
    if not entry:
        return False
    if entry["cooldown_until"] > int(time.time()):
        return True
    # cooldown تموم شده، reset کن
    _flood_counters.pop(acc_id, None)
    return False

def reset_flood(acc_id: str):
    """بعد از عملیات موفق، counter رو reset کن"""
    _flood_counters.pop(acc_id, None)

def cooldown_remaining(acc_id: str) -> int:
    """چند ثانیه تا پایان cooldown مانده"""
    entry = _flood_counters.get(acc_id)
    if not entry:
        return 0
    remaining = entry["cooldown_until"] - int(time.time())
    return max(0, remaining)

