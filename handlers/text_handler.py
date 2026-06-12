import asyncio, random, re, time
from pyrogram import Client, filters
from pyrogram.errors import (FloodWait, UserAlreadyParticipant,
    InviteHashExpired, InviteHashInvalid, ChannelsTooMuch, UsernameOccupied, UsernameInvalid)
from database import q, u
from utils import ADMIN_ID, get_step, get_step_data, set_step, clear_step, get_user_client, save_account
from keyboards import (main_menu_kb, manage_kb, back_kb, confirm_kb, global_kb)
from handlers.login import send_code, sign_in

def register(app):

    @app.on_message(filters.private & filters.text
                    & ~filters.command(["start","add_account","list_account"]))
    async def on_text(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        step = get_step(ADMIN_ID)
        text = message.text.strip()

        # ══ لاگین: شماره ══
        if step == "login_phone":
            if not text.startswith("+"):
                await message.reply("❌ شماره باید با + شروع شود.\nمثال: `+989123456789`")
                return
            msg = await message.reply("⏳ در حال ارسال کد...")
            try:
                await send_code(text, ADMIN_ID)
                set_step(ADMIN_ID, "login_code", text)
                await msg.edit_text(f"✅ کد به `{text}` ارسال شد.\n\nکد دریافتی را وارد کنید:")
            except FloodWait as e:
                await msg.edit_text(f"❌ محدودیت تلگرام. {e.value} ثانیه صبر کنید.")
                clear_step(ADMIN_ID)
            except Exception as e:
                await msg.edit_text(f"❌ خطا: `{e}`")
                clear_step(ADMIN_ID)

        # ══ لاگین: کد ══
        elif step == "login_code":
            phone = get_step_data(ADMIN_ID)
            result, err = await sign_in(phone, code=text)
            if err == "2fa":
                set_step(ADMIN_ID, "login_2fa", phone)
                await message.reply("🔐 رمز دو مرحله‌ای را وارد کنید:")
                return
            await _handle_login_result(message, result, err, phone)

        # ══ لاگین: رمز ۲FA ══
        elif step == "login_2fa":
            phone = get_step_data(ADMIN_ID)
            result, err = await sign_in(phone, password=text)
            await _handle_login_result(message, result, err, phone)

        # ══ بیو ══
        elif step.startswith("set_bio_"):
            acc_id = step[8:]
            await _profile_action(message, acc_id, "bio", text)

        # ══ نام ══
        elif step.startswith("set_fname_"):
            acc_id = step[10:]
            await _profile_action(message, acc_id, "fname", text)

        # ══ فامیلی ══
        elif step.startswith("set_lname_"):
            acc_id = step[10:]
            await _profile_action(message, acc_id, "lname", text)

        # ══ آیدی ══
        elif step.startswith("set_uname_"):
            acc_id = step[10:]
            uname = text.lstrip("@")
            uc = await get_user_client(acc_id)
            if not uc:
                await message.reply("❌ اکانت در دسترس نیست.", reply_markup=manage_kb(acc_id))
                clear_step(ADMIN_ID); return
            try:
                await uc.start()
                await uc.set_username(uname)
                await uc.stop()
                u("UPDATE accounts SET username=%s WHERE id=%s", (uname, acc_id))
                await message.reply("✅ نام کاربری تنظیم شد.", reply_markup=manage_kb(acc_id))
            except (UsernameOccupied, UsernameInvalid) as e:
                await message.reply(f"❌ {e}", reply_markup=manage_kb(acc_id))
            except Exception as e:
                await message.reply(f"❌ خطا: {e}", reply_markup=manage_kb(acc_id))
            clear_step(ADMIN_ID)

        # ══ متن بنر ══
        elif step.startswith("bn_text_"):
            parts = step.split("_")
            # bn_text_{acc_id}_{slot}_{ctx}
            acc_id, slot, ctx = parts[2], int(parts[3]), parts[4]
            set_step(ADMIN_ID, f"bn_file_{acc_id}_{slot}_{ctx}", text)
            # ذخیره موقت
            u("INSERT INTO banners (account_id,admin_id,slot,text,context) "
              "VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE text=%s",
              (acc_id, ADMIN_ID, slot, text, ctx, text))
            await message.reply(
                "📎 حالا فایل پیوست (عکس/ویدیو) را بفرستید یا بدون فایل ادامه دهید:",
                reply_markup=back_kb(f"bn_back_{acc_id}_{ctx}")
            )

        # ══ ارسال پیام به گروه‌ها ══
        elif step.startswith("sgrp_"):
            acc_id = step[5:]
            await message.reply(
                f"📢 متن پیام:\n\n{text}\n\nارسال به همه گروه‌ها؟",
                reply_markup=confirm_kb(f"sgrp_go_{acc_id}_{_enc(text)}", f"acc_manage_{acc_id}")
            )
            set_step(ADMIN_ID, f"sgrp_confirm_{acc_id}", text)

        # ══ ارسال پیام به پیوی‌ها ══
        elif step.startswith("spv_"):
            acc_id = step[4:]
            await message.reply(
                f"💬 متن پیام:\n\n{text}\n\nارسال به همه پیوی‌ها؟",
                reply_markup=confirm_kb(f"spv_go_{acc_id}", f"acc_manage_{acc_id}")
            )
            set_step(ADMIN_ID, f"spv_confirm_{acc_id}", text)

        # ══ استخراج لینک - کانال ══
        elif step.startswith("ext_ch_"):
            acc_id = step[7:]
            ch = text.lstrip("@")
            set_step(ADMIN_ID, f"ext_cnt_{acc_id}", ch)
            await message.reply(
                "لطفاً انتخاب کنید در چند پیام اخیر دنبال لینک بگردم:\n\n"
                "📩 حداقل ۱ و حداکثر ۱۰۰۰ پیام\n\nعدد مورد نظر را ارسال کنید:",
                reply_markup=back_kb(f"m_ext_{acc_id}")
            )

        # ══ استخراج لینک - تعداد ══
        elif step.startswith("ext_cnt_"):
            acc_id = step[8:]
            ch = get_step_data(ADMIN_ID)
            if not text.isdigit() or not (1 <= int(text) <= 1000):
                await message.reply("❌ عدد باید بین ۱ تا ۱۰۰۰ باشد.")
                return
            msg = await message.reply("⏳ در حال استخراج لینک‌ها...")
            links = await _extract_links(acc_id, ch, int(text))
            if not links:
                await msg.edit_text("🔍 لینکی یافت نشد.")
            else:
                out = "\n".join(links)
                # اگه طولانی بود تقسیم کن
                if len(out) > 4000:
                    chunks = [out[i:i+4000] for i in range(0, len(out), 4000)]
                    for ch_txt in chunks:
                        await message.reply(ch_txt)
                    await msg.delete()
                else:
                    await msg.edit_text(out)
            clear_step(ADMIN_ID)

        # ══ عضویت در لینک‌ها ══
        elif step.startswith("join_"):
            acc_id = step[5:]
            links = [l.strip() for l in text.splitlines() if l.strip()]
            if not links:
                await message.reply("❌ لینکی وارد نشد.")
                return
            if len(links) > 10:
                await message.reply(
                    "⚠️ برای جلوگیری از محدودیت، پیشنهاد می‌شود کمتر از ۱۰ لینک وارد کنید.\n"
                    f"شما {len(links)} لینک وارد کردید. ادامه می‌دهید؟",
                    reply_markup=confirm_kb(f"join_go_{acc_id}", f"acc_manage_{acc_id}")
                )
                set_step(ADMIN_ID, f"join_confirm_{acc_id}", "\n".join(links))
                return
            row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
            mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
            await message.reply(
                f"✅ **{len(links)} لینک دریافت شد**\n\n"
                f"⏱ فاصله بین هر عضویت: {mn//60}–{mx//60} دقیقه\n\n🚀 عملیات شروع شد..."
            )
            asyncio.create_task(_join_links(client, acc_id, links, mn, mx))
            clear_step(ADMIN_ID)

        # ══ تنظیم تاخیر عضویت ══
        elif step.startswith("joindelay_"):
            acc_id = step[10:]
            parts = text.split()
            if len(parts) != 2 or not all(p.isdigit() for p in parts):
                await message.reply("❌ فرمت: MIN MAX (دقیقه)\nمثال: `3 7`")
                return
            mn, mx = int(parts[0])*60, int(parts[1])*60
            u("INSERT INTO join_settings (account_id,admin_id,min_delay,max_delay) "
              "VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE min_delay=%s,max_delay=%s",
              (acc_id, ADMIN_ID, mn, mx, mn, mx))
            await message.reply(f"✅ فاصله: {parts[0]}–{parts[1]} دقیقه تنظیم شد.",
                                 reply_markup=manage_kb(acc_id))
            clear_step(ADMIN_ID)

        # ══ زمان‌بند: interval ══
        elif step.startswith("sch_int_"):
            acc_id = step[8:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید. مثال: `10`")
                return
            u("INSERT INTO scheduler (account_id,admin_id,interval_minutes) "
              "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE interval_minutes=%s",
              (acc_id, ADMIN_ID, int(text), int(text)))
            await message.reply(f"✅ هر {text} دقیقه ارسال می‌شود.",
                                 reply_markup=back_kb(f"m_sch_{acc_id}"))
            clear_step(ADMIN_ID)

        # ══ global: بیو ══
        elif step == "g_bio":
            await _global_profile(message, "bio", text)
        elif step == "g_fname":
            await _global_profile(message, "fname", text)
        elif step == "g_lname":
            await _global_profile(message, "lname", text)

        # ══ global: پیام به گروه‌ها ══
        elif step == "g_sgrp":
            set_step(ADMIN_ID, "g_sgrp_confirm", text)
            await message.reply(
                f"📢 ارسال به گروه‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_sgrp_go", "menu_global")
            )

        # ══ global: پیام به پیوی‌ها ══
        elif step == "g_spv":
            set_step(ADMIN_ID, "g_spv_confirm", text)
            await message.reply(
                f"💬 ارسال به پیوی‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_spv_go", "menu_global")
            )

        # ══ global: لینک عضویت ══
        elif step == "g_join":
            links = [l.strip() for l in text.splitlines() if l.strip()]
            set_step(ADMIN_ID, "g_join_links", "\n".join(links))
            from keyboards import global_join_kb
            await message.reply(
                f"✅ {len(links)} لینک دریافت شد.\nنوع عضویت را انتخاب کنید:",
                reply_markup=global_join_kb()
            )


    @app.on_message(filters.private & (filters.photo | filters.video | filters.document))
    async def on_media(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        step = get_step(ADMIN_ID)
        if not step.startswith("bn_file_"):
            return
        parts = step.split("_")
        acc_id, slot, ctx = parts[2], int(parts[3]), parts[4]
        if message.photo:
            fid, ftype = message.photo.file_id, "photo"
        elif message.video:
            fid, ftype = message.video.file_id, "video"
        elif message.document:
            fid, ftype = message.document.file_id, "document"
        else:
            return
        u("UPDATE banners SET file_id=%s, file_type=%s "
          "WHERE account_id=%s AND slot=%s AND context=%s",
          (fid, ftype, acc_id, slot, ctx))
        await message.reply("✅ بنر با فایل پیوست ذخیره شد.",
                             reply_markup=back_kb(f"bn_back_{acc_id}_{ctx}"))
        clear_step(ADMIN_ID)


# ─── helpers ───────────────────────────────────────────────────

async def _handle_login_result(message, result, err, phone):
    if err:
        errs = {
            "bad_code": "❌ کد اشتباه است.",
            "expired_code": "❌ کد منقضی شده. دوباره /add_account بزنید.",
            "expired": "❌ جلسه منقضی شد. دوباره /add_account بزنید.",
            "bad_pass": "❌ پسورد اشتباه است.",
        }
        if err.startswith("flood:"):
            secs = err.split(":")[1]
            await message.reply(f"❌ محدودیت تلگرام. {secs} ثانیه صبر کنید.")
        else:
            await message.reply(errs.get(err, f"❌ خطا: {err}"))
        if err in ("expired_code", "expired"):
            clear_step(ADMIN_ID)
        return
    me, ss = result
    save_account(me, ss, phone)
    cnt = q("SELECT COUNT(*) FROM accounts WHERE admin_id=%s", (ADMIN_ID,))[0][0]
    await message.reply(
        f"✅ **اکانت با موفقیت اضافه شد!**\n\n"
        f"👤 نام: {me.first_name or ''} {me.last_name or ''}\n"
        f"📱 شماره: `{phone}`\n"
        f"🤖 تعداد تبچی‌های فعال: `{cnt}`",
        reply_markup=main_menu_kb()
    )
    clear_step(ADMIN_ID)

async def _profile_action(message, acc_id, action, value):
    uc = await get_user_client(acc_id)
    if not uc:
        await message.reply("❌ اکانت در دسترس نیست.", reply_markup=manage_kb(acc_id))
        clear_step(ADMIN_ID); return
    try:
        await uc.start()
        me = await uc.get_me()
        if action == "bio":
            await uc.update_profile(bio=value)
        elif action == "fname":
            await uc.update_profile(first_name=value, last_name=me.last_name or "")
            u("UPDATE accounts SET name=%s WHERE id=%s", (value, acc_id))
        elif action == "lname":
            await uc.update_profile(first_name=me.first_name or "", last_name=value)
        await uc.stop()
        await message.reply("✅ با موفقیت تنظیم شد.", reply_markup=manage_kb(acc_id))
    except Exception as e:
        await message.reply(f"❌ خطا: {e}", reply_markup=manage_kb(acc_id))
    clear_step(ADMIN_ID)

async def _extract_links(acc_id, channel, limit):
    uc = await get_user_client(acc_id)
    if not uc:
        return []
    pattern = re.compile(r'(https?://t\.me/\S+|@[\w]{4,})')
    links = []
    try:
        await uc.start()
        async for msg in uc.get_chat_history(channel, limit=limit):
            txt = (msg.text or "") + " " + (msg.caption or "")
            links += pattern.findall(txt)
        await uc.stop()
    except Exception:
        pass
    return list(dict.fromkeys(links))

async def _join_links(bot_client, acc_id, links, min_d, max_d):
    uc = await get_user_client(acc_id)
    if not uc:
        return
    await uc.start()
    me = await uc.get_me()
    acc_display = me.phone_number or str(me.id)
    ok_links, fail_links = [], []

    for i, link in enumerate(links, 1):
        target = link.lstrip("@") if link.startswith("@") else link
        try:
            await uc.join_chat(target)
            ok_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"✅ [{i}/{len(links)}] عضو شد: `{link}`")

        except FloodWait as e:
            wait_s  = e.value
            safe_s  = int(wait_s * 3.5)
            await bot_client.send_message(
                ADMIN_ID,
                f"❗️ عملیات عضو شدن در کانال یا گروه متوقف شد "
                f"شما به محدودیت تلگرام خورده اید به مدت {wait_s} ثانیه\n\n"
                f"جهت جلوگیری از مسدود شدن اکانت ربات پس از {safe_s} ثانیه "
                f"دیگر به عملیات خود ادامه می دهد\n"
                f"👤 اکانت : {acc_display}"
            )
            await asyncio.sleep(safe_s)
            try:
                await uc.join_chat(target)
                ok_links.append(link)
                await bot_client.send_message(ADMIN_ID, f"✅ [{i}/{len(links)}] بعد از محدودیت عضو شد: `{link}`")
            except Exception as e2:
                fail_links.append(link)
                await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(links)}] ناموفق بعد از محدودیت: `{link}`\n{e2}")

        except UserAlreadyParticipant:
            ok_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"ℹ️ [{i}/{len(links)}] قبلاً عضو بود: `{link}`")

        except (InviteHashExpired, InviteHashInvalid):
            fail_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(links)}] لینک منقضی: `{link}`")

        except ChannelsTooMuch:
            fail_links.append(link)
            await bot_client.send_message(
                ADMIN_ID,
                f"⛔️ اکانت به حداکثر تعداد کانال رسیده. عملیات متوقف شد.\n👤 اکانت: {acc_display}"
            )
            break

        except Exception as e:
            fail_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(links)}] خطا: `{link}`\n{e}")

        if i < len(links):
            delay = random.randint(min_d, max_d)
            await bot_client.send_message(
                ADMIN_ID, f"⏳ صبر {delay//60} دقیقه و {delay%60} ثانیه تا عضویت بعدی...")
            await asyncio.sleep(delay)

    await uc.stop()
    total = len(ok_links) + len(fail_links)
    report = (f"✅ عملیات عضو شدن در {total} گروه یا کانال با موفقیت انجام شد\n"
              f"👤 اکانت {acc_display}\n"
              f"موفق ها : {len(ok_links)}\nناموفق ها : {len(fail_links)}")
    if fail_links:
        report += "\n\n❗️ لیست ناموفق ها :\n" + "\n".join(fail_links)
    await bot_client.send_message(ADMIN_ID, report)

async def _global_profile(message, action, value):
    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
    ok = fail = 0
    for (aid,) in accs:
        uc = await get_user_client(aid)
        if not uc:
            fail += 1; continue
        try:
            await uc.start()
            me = await uc.get_me()
            if action == "bio":
                await uc.update_profile(bio=value)
            elif action == "fname":
                await uc.update_profile(first_name=value, last_name=me.last_name or "")
            elif action == "lname":
                await uc.update_profile(first_name=me.first_name or "", last_name=value)
            await uc.stop()
            ok += 1
        except Exception:
            fail += 1
    await message.reply(
        f"✅ عملیات کامل شد:\n✔️ موفق: {ok}\n❌ ناموفق: {fail}",
        reply_markup=global_kb()
    )
    clear_step(ADMIN_ID)

def _enc(text):
    """کوتاه‌سازی متن برای callback_data"""
    return text[:20].replace(" ", "_")
