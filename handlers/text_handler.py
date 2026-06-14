import asyncio, random, re, time
from pyrogram import Client, filters
from pyrogram.errors import (FloodWait, UserAlreadyParticipant,
    InviteHashExpired, InviteHashInvalid, ChannelsTooMuch,
    UsernameOccupied, UsernameInvalid, ChatWriteForbidden,
    UserBannedInChannel, ChatAdminRequired, ChatRestricted,
    SlowmodeWait, UserBlocked, ChatSendMediaForbidden,
    ChatSendPlainForbidden, RPCError)
from database import q, u
from utils import (ADMIN_ID, get_step, get_step_data, set_step,
                   clear_step, get_user_client, save_account, is_stopped, set_stop)
from keyboards import manage_kb, back_kb, confirm_kb, global_kb, reply_rand_kb, react_rand_kb
from handlers.login import send_code, sign_in

def register(app):

    @app.on_message(filters.private & filters.text
                    & ~filters.command(["start","add_account","list_account"]))
    async def on_text(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        step = get_step(ADMIN_ID)
        text = message.text.strip()

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
                await msg.edit_text(f"❌ محدودیت. {e.value} ثانیه صبر کنید.")
                clear_step(ADMIN_ID)
            except Exception as e:
                await msg.edit_text(f"❌ خطا: `{e}`")
                clear_step(ADMIN_ID)

        elif step == "login_code":
            phone = get_step_data(ADMIN_ID)
            result, err = await sign_in(phone, code=text)
            if err == "2fa":
                set_step(ADMIN_ID, "login_2fa", phone)
                await message.reply("🔐 رمز دو مرحله‌ای را وارد کنید:")
                return
            await _handle_login_result(message, result, err, phone)

        elif step == "login_2fa":
            phone = get_step_data(ADMIN_ID)
            result, err = await sign_in(phone, password=text)
            await _handle_login_result(message, result, err, phone)

        elif step.startswith("set_bio_"):
            await _profile_action(message, step[8:], "bio", text)

        elif step.startswith("set_fname_"):
            await _profile_action(message, step[10:], "fname", text)

        elif step.startswith("set_lname_"):
            await _profile_action(message, step[10:], "lname", text)

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

        elif step.startswith("bn_text_"):
            _, _, acc_id, slot, ctx = step.split("_", 4)
            slot = int(slot)
            set_step(ADMIN_ID, f"bn_file_{acc_id}_{slot}_{ctx}", text)
            u("INSERT INTO banners (account_id,admin_id,slot,text,context) "
              "VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE text=%s",
              (acc_id, ADMIN_ID, slot, text, ctx, text))
            await message.reply(
                "📎 فایل پیوست بفرستید یا بدون فایل ادامه دهید:",
                reply_markup=back_kb(f"bn_back_{acc_id}_{ctx}")
            )

        elif step.startswith("gbn_text_"):
            _, _, target, slot = step.split("_", 3)
            slot = int(slot)
            set_step(ADMIN_ID, f"gbn_file_{target}_{slot}", text)
            u("INSERT INTO global_banners (admin_id,target,slot,text) VALUES(%s,%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE text=%s", (ADMIN_ID, target, slot, text, text))
            await message.reply(
                "📎 فایل پیوست بفرستید یا بدون فایل ادامه دهید:",
                reply_markup=back_kb(f"gbn_back_{target}")
            )

        elif step.startswith("sgrp_"):
            acc_id = step[5:]
            set_step(ADMIN_ID, f"sgrp_confirm_{acc_id}", text)
            await message.reply(
                f"📢 متن:\n\n{text}\n\nارسال به همه گروه‌ها؟",
                reply_markup=confirm_kb(f"sgrp_go_{acc_id}", f"acc_manage_{acc_id}")
            )

        elif step.startswith("spv_"):
            acc_id = step[4:]
            set_step(ADMIN_ID, f"spv_confirm_{acc_id}", text)
            await message.reply(
                f"💬 متن:\n\n{text}\n\nارسال به همه پیوی‌ها؟",
                reply_markup=confirm_kb(f"spv_go_{acc_id}", f"acc_manage_{acc_id}")
            )

        elif step.startswith("ext_ch_"):
            # استخراج از یک لینکدونی
            acc_id = step[7:]
            ch = text.lstrip("@")
            set_step(ADMIN_ID, f"ext_cnt_{acc_id}", ch)
            await message.reply(
                "📩 چند پیام آخر بررسی شود؟ (۱ تا ۱۰۰۰):",
                reply_markup=back_kb(f"m_ext_{acc_id}")
            )

        elif step.startswith("ext_cnt_"):
            acc_id = step[8:]
            ch = get_step_data(ADMIN_ID)
            if not text.isdigit() or not (1 <= int(text) <= 1000):
                await message.reply("❌ عدد بین ۱ تا ۱۰۰۰ وارد کنید.")
                return
            msg = await message.reply("⏳ در حال استخراج...")
            links = await _extract_links(acc_id, ch, int(text))
            if not links:
                await msg.edit_text("🔍 لینکی یافت نشد.")
            else:
                out = "\n".join(links)
                if len(out) > 4000:
                    chunks = [out[i:i+4000] for i in range(0, len(out), 4000)]
                    await msg.delete()
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    await msg.edit_text(out)
            clear_step(ADMIN_ID)

        elif step.startswith("ext_multi_ch_"):
            # استخراج از چند لینکدونی - دریافت آیدی‌ها
            acc_id = step[13:]
            channels = [c.strip().lstrip("@") for c in text.splitlines() if c.strip()]
            if not channels:
                await message.reply("❌ هیچ کانالی وارد نشد.")
                return
            set_step(ADMIN_ID, f"ext_multi_cnt_{acc_id}", "\n".join(channels))
            await message.reply(
                f"✅ {len(channels)} لینکدونی دریافت شد.\n\nچند لینک آخر از هر لینکدونی استخراج شود؟",
                reply_markup=back_kb(f"m_ext_{acc_id}")
            )

        elif step.startswith("ext_multi_cnt_"):
            acc_id = step[14:]
            channels = get_step_data(ADMIN_ID).splitlines()
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد معتبر وارد کنید.")
                return
            limit = int(text)
            msg = await message.reply(f"⏳ استخراج {limit} لینک از {len(channels)} لینکدونی...")
            all_links = []
            for ch in channels:
                links = await _extract_links(acc_id, ch, limit)
                all_links.extend(links)
            # حذف تکراری
            all_links = list(dict.fromkeys(all_links))
            if not all_links:
                await msg.edit_text("🔍 لینکی یافت نشد.")
            else:
                out = "\n".join(all_links)
                if len(out) > 4000:
                    chunks = [out[i:i+4000] for i in range(0, len(out), 4000)]
                    await msg.delete()
                    for chunk in chunks:
                        await message.reply(chunk)
                else:
                    await msg.edit_text(out)
            clear_step(ADMIN_ID)

        elif step.startswith("join_"):
            acc_id = step[5:]
            links = [l.strip() for l in text.splitlines() if l.strip()]
            if not links:
                await message.reply("❌ لینکی وارد نشد.")
                return
            row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
            mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
            await message.reply(
                f"✅ **{len(links)} لینک دریافت شد**\n"
                f"⏱ فاصله: {mn//60}–{mx//60} دقیقه\n🚀 شروع شد..."
            )
            asyncio.create_task(_join_links(client, acc_id, links, mn, mx))
            clear_step(ADMIN_ID)

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
            await message.reply(f"✅ فاصله: {parts[0]}–{parts[1]} دقیقه", reply_markup=manage_kb(acc_id))
            clear_step(ADMIN_ID)

        elif step.startswith("sch_int_"):
            acc_id = step[8:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO scheduler (account_id,admin_id,interval_minutes) "
              "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE interval_minutes=%s",
              (acc_id, ADMIN_ID, int(text), int(text)))
            await message.reply(f"✅ هر {text} دقیقه.", reply_markup=back_kb(f"m_sch_{acc_id}"))
            clear_step(ADMIN_ID)

        elif step.startswith("gsch_int_"):
            target = step[9:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO global_scheduler (admin_id,target,interval_minutes) "
              "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE interval_minutes=%s",
              (ADMIN_ID, target, int(text), int(text)))
            from keyboards import global_sch_panel_kb
            row = q("SELECT is_active FROM global_scheduler WHERE admin_id=%s AND target=%s",
                    (ADMIN_ID, target))
            active = row[0][0] if row else 0
            await message.reply(f"✅ هر {text} دقیقه ارسال می‌شود.",
                                 reply_markup=global_sch_panel_kb(target, active))
            clear_step(ADMIN_ID)

        elif step == "g_bio":
            await _global_profile(message, "bio", text)
        elif step == "g_fname":
            await _global_profile(message, "fname", text)
        elif step == "g_lname":
            await _global_profile(message, "lname", text)

        elif step == "g_sgrp":
            set_step(ADMIN_ID, "g_sgrp_confirm", text)
            await message.reply(
                f"📢 ارسال به گروه‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_sgrp_go", "menu_global")
            )

        elif step == "g_spv":
            set_step(ADMIN_ID, "g_spv_confirm", text)
            await message.reply(
                f"💬 ارسال به پیوی‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_spv_go", "menu_global")
            )

        elif step == "g_join":
            links = [l.strip() for l in text.splitlines() if l.strip()]
            set_step(ADMIN_ID, "g_join_links", "\n".join(links))
            from keyboards import global_join_kb
            await message.reply(
                f"✅ {len(links)} لینک دریافت شد.\nنوع عضویت را انتخاب کنید:",
                reply_markup=global_join_kb()
            )

        elif step.startswith("rr_msg_"):
            acc_id = step[7:]
            u("INSERT INTO reply_rand (account_id,admin_id,message_text) VALUES(%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE message_text=%s", (acc_id, ADMIN_ID, text, text))
            row = q("SELECT is_active FROM reply_rand WHERE account_id=%s", (acc_id,))
            active = row[0][0] if row else 0
            await message.reply("✅ متن ریپلای تنظیم شد.", reply_markup=reply_rand_kb(acc_id, active))
            clear_step(ADMIN_ID)

        elif step.startswith("rr_int_"):
            acc_id = step[7:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO reply_rand (account_id,admin_id,interval_minutes) VALUES(%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE interval_minutes=%s", (acc_id, ADMIN_ID, int(text), int(text)))
            row = q("SELECT is_active FROM reply_rand WHERE account_id=%s", (acc_id,))
            active = row[0][0] if row else 0
            await message.reply(f"✅ هر {text} دقیقه ریپلای.", reply_markup=reply_rand_kb(acc_id, active))
            clear_step(ADMIN_ID)

        elif step.startswith("rc_int_"):
            acc_id = step[7:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO react_rand (account_id,admin_id,interval_minutes) VALUES(%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE interval_minutes=%s", (acc_id, ADMIN_ID, int(text), int(text)))
            row = q("SELECT is_active FROM react_rand WHERE account_id=%s", (acc_id,))
            active = row[0][0] if row else 0
            await message.reply(f"✅ هر {text} دقیقه ری‌اکت.", reply_markup=react_rand_kb(acc_id, active))
            clear_step(ADMIN_ID)


    @app.on_message(filters.private & (filters.photo | filters.video | filters.document))
    async def on_media(client, message):
        if message.from_user.id != ADMIN_ID:
            return
        step = get_step(ADMIN_ID)

        if step.startswith("gbn_file_"):
            _, _, target, slot = step.split("_", 3)
            slot = int(slot)
            if message.photo:
                fid, ftype = message.photo.file_id, "photo"
            elif message.video:
                fid, ftype = message.video.file_id, "video"
            elif message.document:
                fid, ftype = message.document.file_id, "document"
            else:
                return
            u("UPDATE global_banners SET file_id=%s, file_type=%s "
              "WHERE admin_id=%s AND target=%s AND slot=%s",
              (fid, ftype, ADMIN_ID, target, slot))
            await message.reply("✅ پیام با فایل ذخیره شد.", reply_markup=back_kb(f"gbn_back_{target}"))
            clear_step(ADMIN_ID)
            return

        if not step.startswith("bn_file_"):
            return
        _, _, acc_id, slot, ctx = step.split("_", 4)
        slot = int(slot)
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
        await message.reply("✅ بنر با فایل ذخیره شد.", reply_markup=back_kb(f"bn_back_{acc_id}_{ctx}"))
        clear_step(ADMIN_ID)


# ─── helpers ───────────────────────────────────────────────────

async def _handle_login_result(message, result, err, phone):
    if err:
        errs = {
            "bad_code": "❌ کد اشتباه است.",
            "expired_code": "❌ کد منقضی شد. دوباره /add_account بزنید.",
            "expired": "❌ جلسه منقضی شد. دوباره /add_account بزنید.",
            "bad_pass": "❌ پسورد اشتباه است.",
        }
        if err.startswith("flood:"):
            await message.reply(f"❌ محدودیت. {err.split(':')[1]} ثانیه صبر کنید.")
        else:
            await message.reply(errs.get(err, f"❌ خطا: {err}"))
        if err in ("expired_code", "expired"):
            clear_step(ADMIN_ID)
        return
    me, ss = result
    save_account(me, ss, phone)
    cnt = q("SELECT COUNT(*) FROM accounts WHERE admin_id=%s", (ADMIN_ID,))[0][0]
    from keyboards import main_menu_kb
    await message.reply(
        f"✅ **اکانت اضافه شد!**\n\n"
        f"👤 {me.first_name or ''} {me.last_name or ''}\n"
        f"📱 `{phone}`\n🤖 تعداد تبچی‌ها: `{cnt}`",
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
        await message.reply("✅ تنظیم شد.", reply_markup=manage_kb(acc_id))
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
    """عضویت در لینک‌ها با هندل کامل خطاها"""
    uc = await get_user_client(acc_id)
    if not uc:
        return
    await uc.start()
    me = await uc.get_me()
    acc_display = me.phone_number or str(me.id)
    ok_links, fail_links = [], []
    # چک auto_leave
    row = q("SELECT auto_leave_limited FROM accounts WHERE id=%s", (acc_id,))
    auto_leave = row[0][0] if row else 0

    for i, link in enumerate(links, 1):
        if is_stopped():
            await bot_client.send_message(ADMIN_ID, "🛑 عملیات توسط کاربر متوقف شد.")
            break
        target = link.lstrip("@") if link.startswith("@") else link
        try:
            await uc.join_chat(target)
            ok_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"✅ [{i}/{len(links)}] عضو شد: `{link}`")

        except FloodWait as e:
            wait_s = e.value
            safe_s = int(wait_s * 3.5)
            await bot_client.send_message(
                ADMIN_ID,
                f"❗️ محدودیت تلگرام {wait_s} ثانیه\n"
                f"پس از {safe_s} ثانیه ادامه می‌دهد\n👤 {acc_display}"
            )
            await asyncio.sleep(safe_s)
            try:
                await uc.join_chat(target)
                ok_links.append(link)
            except Exception as e2:
                fail_links.append(link)

        except UserAlreadyParticipant:
            ok_links.append(link)

        except (InviteHashExpired, InviteHashInvalid):
            fail_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(links)}] لینک منقضی: `{link}`")

        except ChannelsTooMuch:
            fail_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"⛔️ اکانت پر شده. متوقف شد.")
            break

        except Exception as e:
            fail_links.append(link)
            await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(links)}] خطا: `{link}`\n{e}")

        if i < len(links) and not is_stopped():
            delay = random.randint(min_d, max_d)
            await bot_client.send_message(
                ADMIN_ID, f"⏳ صبر {delay//60}دقیقه {delay%60}ثانیه...")
            await asyncio.sleep(delay)

    await uc.stop()
    total = len(ok_links) + len(fail_links)
    report = (f"✅ عملیات عضویت تمام شد\n👤 {acc_display}\n"
              f"موفق: {len(ok_links)}\nناموفق: {len(fail_links)}")
    if fail_links:
        report += "\n\n❗️ ناموفق‌ها:\n" + "\n".join(fail_links)
    await bot_client.send_message(ADMIN_ID, report)


async def send_to_groups_smart(bot_client, acc_id, text, force_join=False):
    """ارسال پیام هوشمند با تشخیص محدودیت و عضویت اجبار"""
    from pyrogram import enums as en
    uc = await get_user_client(acc_id)
    if not uc:
        return {"ok": 0, "fail": 0, "limited": 0, "force_joined": 0, "left": 0}
    me_info = q("SELECT phone, auto_leave_limited FROM accounts WHERE id=%s", (acc_id,))
    display = me_info[0][0] if me_info else acc_id
    auto_leave = me_info[0][1] if me_info else 0
    row_fj = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
    do_force_join = row_fj[0][0] if row_fj else 0

    ok = fail = limited = force_joined = left = 0
    await uc.start()

    async for dlg in uc.get_dialogs():
        if is_stopped():
            break
        if dlg.chat.type not in (en.ChatType.GROUP, en.ChatType.SUPERGROUP):
            continue
        try:
            await uc.send_message(dlg.chat.id, text)
            ok += 1
            await asyncio.sleep(2)

        except (ChatWriteForbidden, UserBannedInChannel, ChatRestricted,
                ChatSendMediaForbidden, ChatSendPlainForbidden) as e:
            err_str = str(e)
            # تشخیص عضویت اجبار
            fj_match = re.search(r'@([\w]+)|t\.me/([\w+]+)', err_str)
            if do_force_join and fj_match:
                ch = fj_match.group(1) or fj_match.group(2)
                try:
                    await uc.join_chat(ch)
                    force_joined += 1
                    await asyncio.sleep(2)
                    await uc.send_message(dlg.chat.id, text)
                    ok += 1
                except Exception:
                    fail += 1
                    if auto_leave:
                        try:
                            await uc.leave_chat(dlg.chat.id)
                            left += 1
                        except Exception:
                            pass
                        limited += 1
            elif auto_leave:
                try:
                    await uc.leave_chat(dlg.chat.id)
                    left += 1
                except Exception:
                    pass
                limited += 1
            else:
                limited += 1

        except SlowmodeWait as e:
            # محدودیت موقت - گروه را خارج نکن، فقط رد کن
            limited += 1

        except FloodWait as e:
            await bot_client.send_message(
                ADMIN_ID,
                f"❗️ محدودیت {e.value} ثانیه\n👤 {display}"
            )
            await asyncio.sleep(e.value * 2)
            try:
                await uc.send_message(dlg.chat.id, text)
                ok += 1
            except Exception:
                fail += 1

        except RPCError as e:
            # هر خطای دیگه‌ی تلگرام که نشون‌دهنده محدودیت ارسال است
            err_str = str(e).lower()
            restriction_keywords = ["forbidden", "banned", "restricted", "not_muted", "rights"]
            if any(k in err_str for k in restriction_keywords):
                if auto_leave:
                    try:
                        await uc.leave_chat(dlg.chat.id)
                        left += 1
                    except Exception:
                        pass
                limited += 1
            else:
                fail += 1

        except Exception:
            fail += 1

    await uc.stop()
    return {"ok": ok, "fail": fail, "limited": limited,
            "force_joined": force_joined, "left": left, "display": display}


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
        f"✅ کامل شد:\n✔️ موفق: {ok}\n❌ ناموفق: {fail}",
        reply_markup=global_kb()
    )
    clear_step(ADMIN_ID)
