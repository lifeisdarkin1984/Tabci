import asyncio
import os
import json
import urllib.request
import urllib.error
from database import q
from utils import ADMIN_ID, get_user_client, get_step, set_step, clear_step

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """تو دستیار هوشمند مدیریت تبچی هستی.
اطلاعات اکانت‌ها و وضعیت سرویس‌ها رو داری.
قوانین:
- سوال‌های آماری رو مستقیم و کوتاه جواب بده
- جواب‌ها کوتاه، مفید و به فارسی باشن
- اگه اطلاعات کافی نداری صادقانه بگو"""


async def _build_context():
    accs = q("SELECT id,phone,name,status FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
    lines = [f"تعداد اکانت‌ها: {len(accs)}"]
    for a in accs:
        aid, phone, name, status = a
        sec = q("SELECT is_active FROM secretary WHERE account_id=%s", (aid,))
        sch = q("SELECT is_active,interval_minutes FROM scheduler WHERE account_id=%s", (aid,))
        sec_active = sec[0][0] if sec else 0
        sch_active = sch[0][0] if sch else 0
        sch_interval = sch[0][1] if sch else 0
        lines.append(
            f"اکانت: {name} | {phone} | وضعیت: {status} | "
            f"منشی: {'فعال' if sec_active else 'غیرفعال'} | "
            f"زمان‌بند: {'فعال هر '+str(sch_interval)+' دقیقه' if sch_active else 'غیرفعال'}"
        )
    return "\n".join(lines)


async def _read_pvs(acc_id, limit=10):
    from pyrogram import enums as en
    uc = await get_user_client(acc_id)
    if not uc:
        return "اکانت در دسترس نیست"
    results = []
    try:
        await uc.start()
        async for dlg in uc.get_dialogs():
            if dlg.chat.type == en.ChatType.PRIVATE:
                name = dlg.chat.first_name or str(dlg.chat.id)
                last = dlg.top_message.text[:50] if dlg.top_message and dlg.top_message.text else "..."
                results.append(f"{name}: {last}")
                if len(results) >= limit:
                    break
        await uc.stop()
    except Exception as e:
        return f"خطا: {e}"
    return "\n".join(results) if results else "پیوی‌ای یافت نشد"


async def _call_ai(user_msg: str, context: str) -> str:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        return "❌ OPENROUTER_API_KEY تنظیم نشده در Railway."

    payload = json.dumps({
        "model": "google/gemma-3-4b-it:free",
        "messages": [
            {"role": "system", "content": f"{SYSTEM_PROMPT}\n\nاطلاعات فعلی:\n{context}"},
            {"role": "user", "content": user_msg}
        ],
        "max_tokens": 500,
        "temperature": 0.3
    }).encode()

    req = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://tabchi.app",
            "X-Title": "Tabchi Assistant"
        },
        method="POST"
    )
    try:
        loop = asyncio.get_event_loop()
        def do_request():
            with urllib.request.urlopen(req, timeout=20) as resp:
                return json.loads(resp.read())
        data = await loop.run_in_executor(None, do_request)
        return data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"❌ خطا {e.code}: {body[:300]}"
    except Exception as e:
        return f"❌ خطا: {type(e).__name__}: {e}"


def register(app):
    from pyrogram import filters

    @app.on_message(
        filters.text
        & filters.private
        & filters.user(ADMIN_ID)
    )
    async def on_assistant_msg(client, message):
        step = get_step(ADMIN_ID)
        if step != "assistant":
            return

        user_text = message.text.strip()

        if user_text in ("/start", "خروج", "exit", "بازگشت"):
            clear_step(ADMIN_ID)
            from keyboards import main_menu_kb
            await message.reply("🔙 بازگشت به منو.", reply_markup=main_menu_kb())
            return

        await message.reply("⏳ در حال بررسی...")

        pvs_text = ""
        if "پیوی" in user_text and ("بخون" in user_text or "بخوان" in user_text or "نشون" in user_text):
            accs = q("SELECT id,name FROM accounts WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
            if accs:
                pvs_text = await _read_pvs(accs[0][0])
                pvs_text = f"\n\nآخرین پیوی‌ها:\n{pvs_text}"

        try:
            context = await _build_context()
            answer = await _call_ai(user_text, context + pvs_text)
            await message.reply(f"🤖 {answer}")
        except Exception as e:
            await message.reply(f"❌ خطای کلی: {type(e).__name__}: {e}")
