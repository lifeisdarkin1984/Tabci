import asyncio, aiohttp
from datetime import date
from pyrogram import enums
from pyrogram.errors import (AuthKeyUnregistered, UserDeactivated,
                              SessionExpired, FloodWait)
from database import q, u
from utils import get_user_client, ADMIN_ID

BOT_CLIENT = None

DEFAULT_SYSTEM_PROMPT = (
    "تو یه دوست صمیمی و خوش‌مشرب هستی که به فارسی روان صحبت می‌کنی. "
    "طبیعی و دوستانه جواب بده."
)

AVAILABLE_MODELS = [
    "mimo-v2.5-free",
    "mimo-v2.5-pro-free",
    "mistral-large",
    "mistral-medium-3-5",
    "mimo-v2.5-hermes",
    "mimo-v2.5-pro-hermes",
]

# ─── تنظیمات ─────────────────────────────────────────────────

async def _get_settings():
    r = q(
        "SELECT api_key, model, system_prompt, pv_active, pv_daily_limit, "
        "group_active, group_tag_filter, memory_count, daily_limit "
        "FROM ai_settings WHERE admin_id=%s",
        (ADMIN_ID,)
    )
    if not r:
        return None
    return {
        "api_key":          r[0][0] or "",
        "model":            r[0][1] or "mimo-v2.5-pro-free",
        "system_prompt":    r[0][2] or DEFAULT_SYSTEM_PROMPT,
        "pv_active":        r[0][3],
        "pv_daily_limit":   r[0][4],
        "group_active":     r[0][5],
        "group_tag_filter": r[0][6] or "ALL",
        "memory_count":     r[0][7],
        "daily_limit":      r[0][8],
    }

# ─── تاریخچه ─────────────────────────────────────────────────

async def _get_history(account_id, user_id, context, memory_count):
    rows = q(
        "SELECT role, message FROM ai_conversations "
        "WHERE admin_id=%s AND account_id=%s AND user_id=%s AND context=%s "
        "ORDER BY created_at DESC LIMIT %s",
        (ADMIN_ID, account_id, user_id, context, memory_count)
    )
    if not rows:
        return []
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def _save_message(account_id, user_id, context, role, message):
    try:
        u(
            "INSERT INTO ai_conversations "
            "(admin_id, account_id, user_id, context, role, message) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (ADMIN_ID, account_id, user_id, context, role, message)
        )
    except Exception as e:
        print(f"[AIWorker] خطا در ذخیره پیام: {e}")

# ─── آمار ────────────────────────────────────────────────────

def _check_daily_limit(account_id, limit):
    r = q(
        "SELECT requests FROM ai_stats "
        "WHERE admin_id=%s AND account_id=%s AND stat_date=%s",
        (ADMIN_ID, account_id, date.today())
    )
    count = r[0][0] if r else 0
    return count < limit

def _increment_stats(account_id, tokens=0):
    try:
        u(
            "INSERT INTO ai_stats (admin_id, account_id, stat_date, requests, tokens_used) "
            "VALUES (%s,%s,%s,1,%s) "
            "ON DUPLICATE KEY UPDATE requests=requests+1, tokens_used=tokens_used+%s",
            (ADMIN_ID, account_id, date.today(), tokens, tokens)
        )
    except Exception as e:
        print(f"[AIWorker] خطا در آمار: {e}")

# ─── جلوگیری از تداخل با منشی ────────────────────────────────

def _is_secretary_replied(acc_id, user_id):
    r = q(
        "SELECT replied_users FROM secretary WHERE account_id=%s",
        (f"g_{ADMIN_ID}",)
    )
    if not r or not r[0][0]:
        return False
    return str(user_id) in r[0][0].split(",")

# ─── ردیابی آخرین پیام پردازش‌شده ───────────────────────────

def _get_ai_last_msg(acc_id, user_id):
    r = q(
        "SELECT id FROM ai_conversations "
        "WHERE admin_id=%s AND account_id=%s AND user_id=%s AND role='user' "
        "ORDER BY created_at DESC LIMIT 1",
        (ADMIN_ID, str(acc_id), user_id)
    )
    return r[0][0] if r else 0

# ─── API Call ─────────────────────────────────────────────────

async def ask_ai(api_key, model, system_prompt, history, user_message):
    messages = [{"role": "system", "content": system_prompt}]
    messages += history
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.7
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://router.bynara.id/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    print(f"[AIWorker] API status {resp.status}: {body[:200]}")
                    return None, 0
                data = await resp.json()
                reply = data["choices"][0]["message"]["content"].strip()
                tokens = data.get("usage", {}).get("total_tokens", 0)
                return reply, tokens
    except Exception as e:
        print(f"[AIWorker] خطا در API: {e}")
        return None, 0

# ─── دستیار اطلاعاتی ادمین ───────────────────────────────────

async def handle_admin_question(question):
    settings = await _get_settings()
    if not settings or not settings["api_key"]:
        return "❌ API Key تنظیم نشده."

    today = date.today()
    stats = q(
        "SELECT SUM(requests), SUM(tokens_used) FROM ai_stats "
        "WHERE admin_id=%s AND stat_date=%s",
        (ADMIN_ID, today)
    )
    total_req = (stats[0][0] or 0) if stats else 0
    total_tok = (stats[0][1] or 0) if stats else 0

    accs = q("SELECT COUNT(*) FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
    acc_count = accs[0][0] if accs else 0

    pv_today = q(
        "SELECT COUNT(*) FROM ai_conversations "
        "WHERE admin_id=%s AND context='pv' AND DATE(created_at)=%s AND role='user'",
        (ADMIN_ID, today)
    )
    pv_count = pv_today[0][0] if pv_today else 0

    db_context = (
        f"\nاطلاعات سیستم Tabci:\n"
        f"- تعداد اکانت‌ها: {acc_count}\n"
        f"- پیوی‌های پردازش‌شده امروز توسط AI: {pv_count}\n"
        f"- درخواست‌های AI امروز: {total_req}\n"
        f"- توکن مصرفی امروز: {total_tok}\n"
        f"- تاریخ امروز: {today}\n"
    )
    system = (
        "تو دستیار هوشمند سیستم مدیریت Tabci هستی. "
        "اطلاعات سیستم رو داری و به فارسی روان جواب می‌دی."
        + db_context
    )
    reply, _ = await ask_ai(
        settings["api_key"], settings["model"],
        system, [], question
    )
    return reply or "❌ خطا در دریافت جواب."

# ─── پردازش پیوی‌های یه اکانت (polling) ─────────────────────

async def _process_account_pvs(acc_id, settings):
    """
    آخرین پیام‌های پیوی رو poll می‌کنه و به پیام‌های جدید جواب می‌ده.
    مثل pv_monitor — start/stop می‌کنه و بعد تموم می‌شه.
    """
    uc = await get_user_client(str(acc_id))
    if not uc:
        return

    try:
        await uc.start()
        me = await uc.get_me()
        my_id = me.id

        # گرفتن لیست پیوی‌ها
        pvs = []
        async for dlg in uc.get_dialogs():
            if dlg.chat.type == enums.ChatType.PRIVATE:
                # پیام‌های سیستمی و خود اکانت رو رد کن
                if dlg.chat.id in (777000, 42777, my_id):
                    continue
                pvs.append(dlg)

        for dlg in pvs:
            if not _check_daily_limit(str(acc_id), settings["pv_daily_limit"]):
                break

            user_id = dlg.chat.id
            # آخرین پیام رو بخون
            last_msg = None
            async for msg in uc.get_chat_history(user_id, limit=1):
                last_msg = msg

            if not last_msg:
                continue
            # فقط پیام‌های incoming
            if last_msg.outgoing:
                continue
            # چک کن قبلاً جواب دادیم یا نه
            # اگه آخرین پیام ما outgoing بود (قبل از این پیام)، جواب دادیم
            already = False
            count = 0
            async for msg in uc.get_chat_history(user_id, limit=3):
                count += 1
                if count == 1:
                    continue  # اولی همون last_msg هست
                if msg.outgoing:
                    already = True
                break
            if already:
                continue

            # چک تداخل با منشی
            if _is_secretary_replied(acc_id, user_id):
                continue

            text = last_msg.text or last_msg.caption or ""
            if not text.strip():
                continue

            history = await _get_history(str(acc_id), user_id, "pv", settings["memory_count"])
            reply, tokens = await ask_ai(
                settings["api_key"], settings["model"],
                settings["system_prompt"], history, text
            )
            if not reply:
                continue

            try:
                await uc.send_message(user_id, reply)
                _save_message(str(acc_id), user_id, "pv", "user", text)
                _save_message(str(acc_id), user_id, "pv", "assistant", reply)
                _increment_stats(str(acc_id), tokens)
                await asyncio.sleep(2)
            except FloodWait as e:
                await asyncio.sleep(min(e.value, 60))
            except Exception as e:
                print(f"[AIWorker] خطا در ارسال به {user_id}: {e}")

        await uc.stop()

    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
        print(f"[AIWorker] اکانت {acc_id} منقضی.")
        try: await uc.stop()
        except Exception: pass
    except Exception as e:
        print(f"[AIWorker] خطا در اکانت {acc_id}: {e}")
        try: await uc.stop()
        except Exception: pass

# ─── حلقه اصلی ───────────────────────────────────────────────

async def run():
    print("🤖 AI worker started")
    await asyncio.sleep(15)  # صبر می‌کنه بقیه worker‌ها بیان بالا

    while True:
        try:
            settings = await _get_settings()
            if settings and settings["api_key"] and settings["pv_active"]:
                accs = q(
                    "SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
                    (ADMIN_ID,)
                )
                for (acc_id,) in (accs or []):
                    await _process_account_pvs(acc_id, settings)
                    await asyncio.sleep(3)  # فاصله بین اکانت‌ها
        except Exception as e:
            print(f"[AIWorker] خطای کلی: {e}")

        await asyncio.sleep(120)  # هر ۲ دقیقه poll می‌کنه
