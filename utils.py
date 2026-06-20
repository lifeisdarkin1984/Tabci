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

