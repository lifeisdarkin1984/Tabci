import asyncio
import os
import json
import urllib.request
import urllib.error
from database import q
from utils import ADMIN_ID, get_user_client, get_step, set_step, clear_step

SYSTEM_PROMPT = """تو دستیار هوشمند مدیریت تبچی هستی.
اطلاعات اکانت‌ها و وضعیت سرویس‌ها رو داری.
جواب‌ها کوتاه، مفید و به فارسی باشن."""

MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-pro",
]

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


async def _call_gemini(user_msg: str, context: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "❌ GEMINI_API_KEY تنظیم نشده در Railway."

    payload = json.dumps({
        "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\nاطلاعات:\n{context}\n\nسوال: {user_msg}"}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.3}
    }).encode()

    errors = []
    for model in MODELS:
        for use_header in [True, False]:
            try:
                if use_header:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
                else:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                    headers = {"Content-Type": "application/json"}

                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                loop = asyncio.get_event_loop()
                def do_req(r=req):
                    with urllib.request.urlopen(r, timeout=15) as resp:
                        return json.loads(resp.read())
                data = await loop.run_in_executor(None, do_req)
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                body = e.read().decode()[:150]
                errors.append(f"{model}({'H' if use_header else 'Q'}): {e.code} {body}")
            except Exception as e:
                errors.append(f"{model}({'H' if use_header else 'Q'}): {type(e).__name__}: {str(e)[:80]}")

    return "❌ همه مدل‌ها ناموفق:\n" + "\n".join(errors)


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

        try:
            context = await _build_context()
            answer = await _call_gemini(user_text, context)
            await message.reply(f"🤖 {answer}")
        except Exception as e:
            await message.reply(f"❌ خطای کلی: {type(e).__name__}: {e}")
