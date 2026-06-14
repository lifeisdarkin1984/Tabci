import asyncio
import os
import json
import urllib.request
import urllib.error
from database import q
from utils import ADMIN_ID, get_user_client, get_step, set_step, clear_step

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY
)

SYSTEM_PROMPT = """تو دستیار هوشمند مدیریت تبچی هستی.
اطلاعات اکانت‌ها و وضعیت سرویس‌ها رو داری.
قوانین:
- سوال‌های آماری رو مستقیم و کوتاه جواب بده
- برای عملیات مهم (ارسال پیام، خاموش کردن سرویس) بگو "تایید کنید: [عملیات]"
- پیام‌های پیوی رو فقط خلاصه کن، عین متن رو نقل نکن
- جواب‌ها کوتاه، مفید و به فارسی باشن
- اگه اطلاعات کافی نداری صادقانه بگو"""


async def _build_context(acc_id=None):
    """ساخت context از دیتابیس برای ارسال به Gemini"""
    accs = q("SELECT id,phone,name,status FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
    lines = [f"تعداد اکانت‌ها: {len(accs)}"]
    for a in accs:
        aid, phone, name, status = a
        sec = q("SELECT is_active FROM secretary WHERE account_id=%s", (aid,))
        sch = q("SELECT is_active,interval_minutes FROM scheduler WHERE account_id=%s", (aid,))
        sec_active = sec[0][0] if sec else 0
        sch_active = sch[0][0] if sch else 0
        sch_interval = sch[0][1] if sch else 0
        replied = q("SELECT COUNT(*) FROM secretary WHERE account_id=%s", (aid,))
        lines.append(
            f"اکانت: {name} | {phone} | وضعیت: {status} | "
            f"منشی: {'فعال' if sec_active else 'غیرفعال'} | "
            f"زمان‌بند: {'فعال هر '+str(sch_interval)+' دقیقه' if sch_active else 'غیرفعال'}"
        )
    return "\n".join(lines)


async def _read_pvs(acc_id, limit=10):
    """خواندن آخرین پیوی‌ها"""
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


async def _call_gemini(user_msg: str, context: str) -> str:
    """ارسال به Gemini و دریافت جواب"""
    if not GEMINI_API_KEY:
        return "❌ GEMINI_API_KEY تنظیم نشده. آن را در Railway environment variables اضافه کنید."

    payload = json.dumps({
        "contents": [
            {
                "parts": [
                    {"text": f"{SYSTEM_PROMPT}\n\nاطلاعات فعلی:\n{context}\n\nسوال: {user_msg}"}
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.3}
    }).encode()

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        loop = asyncio.get_event_loop()
        def do_request():
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        data = await loop.run_in_executor(None, do_request)
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return f"❌ خطای Gemini: {e.code}\n{body[:200]}"
    except Exception as e:
        return f"❌ خطا: {e}"


def register(app):

    @app.on_message(
        __import__("pyrogram.filters", fromlist=["filters"]).filters.text
        & __import__("pyrogram.filters", fromlist=["filters"]).filters.private
        & __import__("pyrogram.filters", fromlist=["filters"]).filters.user(ADMIN_ID)
    )
    async def on_assistant_msg(client, message):
        step = get_step(ADMIN_ID)
        if step != "assistant":
            return

        user_text = message.text.strip()

        # خروج از حالت دستیار
        if user_text in ("/start", "خروج", "exit", "بازگشت"):
            clear_step(ADMIN_ID)
            from keyboards import main_menu_kb
            await message.reply("🔙 بازگشت به منو.", reply_markup=main_menu_kb())
            return

        await message.reply("⏳ در حال بررسی...")

        # بررسی درخواست خواندن پیوی
        pvs_text = ""
        if "پیوی" in user_text and ("بخون" in user_text or "بخوان" in user_text or "نشون" in user_text):
            accs = q("SELECT id,name FROM accounts WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
            if accs:
                pvs_text = await _read_pvs(accs[0][0])
                pvs_text = f"\n\nآخرین پیوی‌ها:\n{pvs_text}"

        context = await _build_context()
        answer = await _call_gemini(user_text, context + pvs_text)
        await message.reply(f"🤖 {answer}")
