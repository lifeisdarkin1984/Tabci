import asyncio, random, re, time, hashlib, json
from pyrogram import Client, filters
from pyrogram.errors import (FloodWait, UserAlreadyParticipant,
    InviteHashExpired, InviteHashInvalid, ChannelsTooMuch,
    UsernameOccupied, UsernameInvalid, ChatWriteForbidden,
    UserBannedInChannel, ChatAdminRequired, ChatRestricted,
    SlowmodeWait, UserBlocked, ChatSendMediaForbidden, RPCError,
    InviteRequestSent)
from database import q, u
from utils import (ADMIN_ID, get_step, get_step_data, set_step,
                   clear_step, get_user_client, save_account, is_stopped, set_stop,
                   detect_and_handle_bot_forced_join)
from keyboards import (manage_kb, back_kb, confirm_kb, global_kb, reply_rand_kb,
                       react_rand_kb, reply_banner_list_kb, tag_select_kb,
                       main_menu_kb, global_sch_panel_kb, tags_list_kb)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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
            # ذخیره لینک‌ها و رفتن به مرحله انتخاب برچسب
            set_step(ADMIN_ID, f"join_tag_{acc_id}", "\n".join(links))
            tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
            tag_list = [t[0] for t in tags]
            await message.reply(
                f"✅ **{len(links)} لینک دریافت شد**\n\nبرچسب گروه‌ها را انتخاب کنید:",
                reply_markup=tag_select_kb(tag_list, f"jointag_{acc_id}", show_all=False)
            )

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
            row = q("SELECT is_active,group_tag_filter,acc_tag_filter,max_rounds,current_round "
                    "FROM global_scheduler WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
            active = row[0][0] if row else 0
            gtag = (row[0][1] if row else None) or "ALL"
            atag = (row[0][2] if row else None) or "ALL"
            max_r = row[0][3] if row else 0
            cur_r = row[0][4] if row else 0
            await message.reply(f"✅ هر {text} دقیقه ارسال می‌شود.",
                                 reply_markup=global_sch_panel_kb(target, active, gtag=gtag,
                                     atag=atag, max_rounds=max_r, current_round=cur_r))
            clear_step(ADMIN_ID)

        elif step.startswith("gsch_rounds_"):
            target = step[12:]
            if not text.isdigit() or int(text) < 0:
                await message.reply("❌ عدد معتبر وارد کنید (۰ = نامحدود)."); return
            rounds = int(text)
            u("INSERT INTO global_scheduler (admin_id,target,max_rounds,current_round) "
              "VALUES(%s,%s,%s,0) ON DUPLICATE KEY UPDATE max_rounds=%s, current_round=0",
              (ADMIN_ID, target, rounds, rounds))
            row = q("SELECT is_active,group_tag_filter,acc_tag_filter,max_rounds,current_round "
                    "FROM global_scheduler WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
            active = row[0][0] if row else 0
            gtag = (row[0][1] if row else None) or "ALL"
            atag = (row[0][2] if row else None) or "ALL"
            max_r = row[0][3] if row else 0
            cur_r = row[0][4] if row else 0
            lbl = "نامحدود" if rounds == 0 else f"{rounds} دور"
            await message.reply(f"✅ تعداد دور: {lbl}",
                                 reply_markup=global_sch_panel_kb(target, active, gtag=gtag,
                                     atag=atag, max_rounds=max_r, current_round=cur_r))
            clear_step(ADMIN_ID)

        elif step == "g_bio":
            await _global_profile(message, "bio", text)
        elif step == "g_fname":
            await _global_profile(message, "fname", text)
        elif step == "g_lname":
            await _global_profile(message, "lname", text)

        elif step.startswith("tag_new_"):
            context = step[8:]
            tag_name = text.strip()
            if not tag_name or len(tag_name) > 50:
                await message.reply("❌ نام برچسب باید بین ۱ تا ۵۰ کاراکتر باشد."); return
            try:
                u("INSERT INTO tags (admin_id,name) VALUES(%s,%s)", (ADMIN_ID, tag_name))
                tags = q("SELECT DISTINCT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await message.reply(f"✅ برچسب «{tag_name}» ساخته شد.",
                                     reply_markup=tags_list_kb(tag_list, context))
            except Exception:
                await message.reply(f"❌ برچسب «{tag_name}» از قبل وجود دارد.")
            clear_step(ADMIN_ID)

        elif step == "g_sgrp":
            set_step(ADMIN_ID, "g_sgrp_confirm", text)
            await message.reply(
                f"📢 ارسال به گروه‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_sgrp_go", "menu_global")
            )

        elif step == "ld_add_source":
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if not lines:
                await message.reply("❌ هیچ لینکدونی‌ای وارد نشد.")
                return
            set_stop(False)
            await message.reply(f"🚀 افزودن {len(lines)} لینکدونی شروع شد...")
            asyncio.create_task(_add_linkdoni_sources_bulk(client, lines))
            clear_step(ADMIN_ID)

        elif step == "ld_interval":
            if not text.isdigit() or not (1 <= int(text) <= 168):
                await message.reply("❌ عدد بین ۱ تا ۱۶۸ وارد کنید.")
                return
            val = int(text)
            u("INSERT INTO linkdoni_settings (admin_id, scan_interval_hours) "
              "VALUES (%s,%s) ON DUPLICATE KEY UPDATE scan_interval_hours=%s",
              (ADMIN_ID, val, val))
            row = q("SELECT auto_scan, scan_interval_hours, auto_join, join_mode, join_tag "
                    "FROM linkdoni_settings WHERE admin_id=%s", (ADMIN_ID,))
            from keyboards import ld_settings_kb
            if row:
                kb = ld_settings_kb(row[0][0], row[0][1], row[0][2],
                                    row[0][3], row[0][4] or "")
            else:
                kb = ld_settings_kb(0, val, 0, "split", "")
            await message.reply(f"✅ فاصله اسکن: هر {val} ساعت", reply_markup=kb)
            clear_step(ADMIN_ID)

        elif step == "ld_tag":
            tag_val = text.strip() if text.strip() else ""
            u("INSERT INTO linkdoni_settings (admin_id, join_tag) "
              "VALUES (%s,%s) ON DUPLICATE KEY UPDATE join_tag=%s",
              (ADMIN_ID, tag_val, tag_val))
            row = q("SELECT auto_scan, scan_interval_hours, auto_join, join_mode, join_tag "
                    "FROM linkdoni_settings WHERE admin_id=%s", (ADMIN_ID,))
            from keyboards import ld_settings_kb
            if row:
                kb = ld_settings_kb(row[0][0], row[0][1], row[0][2],
                                    row[0][3], row[0][4] or "")
            else:
                kb = ld_settings_kb(0, 6, 0, "split", tag_val)
            lbl = f"«{tag_val}»" if tag_val else "بدون برچسب"
            await message.reply(f"✅ برچسب ذخیره شد: {lbl}", reply_markup=kb)
            clear_step(ADMIN_ID)

        elif step == "g_pvjoin_interval":
            if not text.isdigit() or not (1 <= int(text) <= 24):
                await message.reply("❌ عدد بین ۱ تا ۲۴ وارد کنید.")
                return
            val = int(text)
            u(
                "INSERT INTO pv_join_settings (admin_id, scan_interval_hours) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE scan_interval_hours=%s",
                (ADMIN_ID, val, val)
            )
            st_row = q(
                "SELECT auto_scan, scan_interval_hours, daily_limit "
                "FROM pv_join_settings WHERE admin_id=%s",
                (ADMIN_ID,)
            )
            from keyboards import pv_join_settings_kb
            await message.reply(
                f"✅ فاصله اسکن خودکار: {val} ساعت",
                reply_markup=pv_join_settings_kb(
                    st_row[0][0] if st_row else 0,
                    st_row[0][1] if st_row else val,
                    st_row[0][2] if st_row else 20
                )
            )
            clear_step(ADMIN_ID)

        elif step == "g_pvjoin_limit":
            if not text.isdigit() or not (1 <= int(text) <= 100):
                await message.reply("❌ عدد بین ۱ تا ۱۰۰ وارد کنید.")
                return
            val = int(text)
            u(
                "INSERT INTO pv_join_settings (admin_id, daily_limit) VALUES (%s, %s) "
                "ON DUPLICATE KEY UPDATE daily_limit=%s",
                (ADMIN_ID, val, val)
            )
            st_row = q(
                "SELECT auto_scan, scan_interval_hours, daily_limit "
                "FROM pv_join_settings WHERE admin_id=%s",
                (ADMIN_ID,)
            )
            from keyboards import pv_join_settings_kb
            await message.reply(
                f"✅ سقف روزانه جوین: {val} لینک",
                reply_markup=pv_join_settings_kb(
                    st_row[0][0] if st_row else 0,
                    st_row[0][1] if st_row else 6,
                    st_row[0][2] if st_row else val
                )
            )
            clear_step(ADMIN_ID)

        elif step == "g_spv":
            set_step(ADMIN_ID, "g_spv_confirm", text)
            await message.reply(
                f"💬 ارسال به پیوی‌های **همه اکانت‌ها**:\n\n{text}\n\nتایید؟",
                reply_markup=confirm_kb("g_spv_go", "menu_global")
            )

        elif step == "g_join":

            links = [l.strip() for l in text.splitlines() if l.strip()]
            if not links:
                await message.reply("❌ لینکی وارد نشد.")
                return

            # بررسی تکراری بودن لینک‌ها با جدول used_links
            new_links, dup_links = _check_duplicate_links(links)

            if dup_links:
                set_step(ADMIN_ID, "g_join_dup_check", json.dumps({
                    "all": links,
                    "new": new_links,
                    "dup": dup_links
                }))
                await message.reply(
                    f"📋 **{len(links)} لینک دریافت شد**\n"
                    f"✅ جدید: {len(new_links)} لینک\n"
                    f"🔄 تکراری: {len(dup_links)} لینک (قبلاً استفاده شده)",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            f"❌ حذف تکراری‌ها و جوین با {len(new_links)} لینک",
                            callback_data="gjoin_nodup"
                        )],
                        [InlineKeyboardButton(
                            f"✅ جوین با همه {len(links)} لینک",
                            callback_data="gjoin_all"
                        )]
                    ])
                )
            else:
                set_step(ADMIN_ID, "g_join_tag", "\n".join(links))
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await message.reply(
                    f"✅ {len(links)} لینک دریافت شد.\nبرچسب گروه‌ها را انتخاب کنید:",
                    reply_markup=tag_select_kb(tag_list, "gjointag", show_all=False)
                )

        elif step.startswith("rr_badd_"):
            acc_id = step[8:]
            # پیدا کردن slot بعدی
            rows = q("SELECT MAX(slot) FROM reply_rand_banners WHERE account_id=%s", (acc_id,))
            next_slot = (rows[0][0] or 0) + 1
            u("INSERT INTO reply_rand_banners (account_id,admin_id,slot,text) VALUES(%s,%s,%s,%s)",
              (acc_id, ADMIN_ID, next_slot, text))
            bnrs = q("SELECT slot,text,file_id FROM reply_rand_banners WHERE account_id=%s ORDER BY slot", (acc_id,))
            back = "g_rr" if acc_id == "global" else f"m_reply_{acc_id}"
            await message.reply(f"✅ متن {next_slot} اضافه شد.",
                                 reply_markup=reply_banner_list_kb(acc_id, bnrs, back_to=back))
            clear_step(ADMIN_ID)

        elif step.startswith("rr_int_"):
            acc_id = step[7:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO reply_rand (account_id,admin_id,interval_minutes) VALUES(%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE interval_minutes=%s", (acc_id, ADMIN_ID, int(text), int(text)))
            row = q("SELECT is_active FROM reply_rand WHERE account_id=%s", (acc_id,))
            active = row[0][0] if row else 0
            back = "menu_global" if acc_id == "global" else None
            await message.reply(f"✅ هر {text} دقیقه ریپلای.", reply_markup=reply_rand_kb(acc_id, active, back_to=back))
            clear_step(ADMIN_ID)

        elif step.startswith("rc_int_"):
            acc_id = step[7:]
            if not text.isdigit() or int(text) < 1:
                await message.reply("❌ عدد دقیقه وارد کنید."); return
            u("INSERT INTO react_rand (account_id,admin_id,interval_minutes) VALUES(%s,%s,%s) "
              "ON DUPLICATE KEY UPDATE interval_minutes=%s", (acc_id, ADMIN_ID, int(text), int(text)))
            row = q("SELECT is_active FROM react_rand WHERE account_id=%s", (acc_id,))
            active = row[0][0] if row else 0
            back = "menu_global" if acc_id == "global" else None
            await message.reply(f"✅ هر {text} دقیقه ری‌اکت.", reply_markup=react_rand_kb(acc_id, active, back_to=back))
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

async def _add_linkdoni_sources_bulk(bot_client, lines):
    """افزودن دسته‌ای لینکدونی‌ها (مشابه عضویت گروهی)"""
    import random as _random
    accs_ld = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
    if not accs_ld:
        await bot_client.send_message(ADMIN_ID, "❌ هیچ اکانت فعالی وجود ندارد.")
        return

    acc_id_ld = str(_random.choice(accs_ld)[0])
    uc_ld = await get_user_client(acc_id_ld)
    if not uc_ld:
        await bot_client.send_message(ADMIN_ID, "❌ اکانت در دسترس نیست.")
        return

    ok, fail = 0, 0
    try:
        await uc_ld.start()
        for i, raw in enumerate(lines, 1):
            if is_stopped():
                await bot_client.send_message(ADMIN_ID, "🛑 عملیات توسط کاربر متوقف شد.")
                break

            raw = raw.strip()
            if raw.startswith("https://t.me/"):
                chat_input = raw.split("t.me/")[-1].strip("/").split("?")[0]
            elif raw.startswith("@"):
                chat_input = raw.lstrip("@")
            elif raw.lstrip("-").isdigit():
                chat_input = raw
            else:
                chat_input = raw.lstrip("@")

            try:
                target_ld = int(chat_input)
            except ValueError:
                target_ld = chat_input

            try:
                chat_info = await uc_ld.get_chat(target_ld)
                real_id = str(chat_info.id)
                title = getattr(chat_info, 'title', '') or chat_input
            except FloodWait as e:
                await bot_client.send_message(
                    ADMIN_ID,
                    f"❗️ محدودیت تلگرام {e.value} ثانیه؛ صبر می‌کند و ادامه می‌دهد..."
                )
                await asyncio.sleep(e.value)
                try:
                    chat_info = await uc_ld.get_chat(target_ld)
                    real_id = str(chat_info.id)
                    title = getattr(chat_info, 'title', '') or chat_input
                except Exception:
                    real_id = chat_input
                    title = chat_input
            except Exception:
                real_id = chat_input
                title = chat_input

            try:
                u("INSERT IGNORE INTO linkdoni_sources "
                  "(admin_id, chat_id, chat_title, source_link) VALUES (%s,%s,%s,%s)",
                  (ADMIN_ID, real_id, title[:200], raw[:300]))
                ok += 1
                await bot_client.send_message(ADMIN_ID, f"✅ [{i}/{len(lines)}] افزوده شد: {title}")
            except Exception as ex:
                fail += 1
                await bot_client.send_message(ADMIN_ID, f"❌ [{i}/{len(lines)}] خطا در «{raw}»: {ex}")

        try:
            await uc_ld.stop()
        except Exception:
            pass
    except Exception as ex:
        try:
            await uc_ld.stop()
        except Exception:
            pass
        print(f"[LinkdoniBulkAdd] {ex}")

    from keyboards import ld_sources_kb
    srcs = q("SELECT id, chat_id, chat_title, is_active "
             "FROM linkdoni_sources WHERE admin_id=%s ORDER BY added_at DESC",
             (ADMIN_ID,))
    src_list = [{"id": r[0], "chat_id": r[1],
                 "chat_title": r[2], "is_active": r[3]} for r in srcs]
    await bot_client.send_message(
        ADMIN_ID,
        f"📋 **پایان افزودن دسته‌ای لینکدونی‌ها**\n✅ موفق: {ok}\n❌ ناموفق: {fail}",
        reply_markup=ld_sources_kb(src_list)
    )


async def _extract_links(acc_id, channel, limit):
    uc = await get_user_client(acc_id)
    if not uc:
        return []
    pattern = re.compile(r'https?://t\.me/[^\s\]\)\"\']+')
    links = []
    BATCH = 200
    offset_id = 0
    try:
        await uc.start()
        while len(links) < limit:
            batch = []
            async for msg in uc.get_chat_history(channel, limit=BATCH, offset_id=offset_id):
                batch.append(msg)

            if not batch:
                # تاریخچهٔ کانال تمام شده
                break

            for msg in batch:
                # ۱. متن پیام
                txt = (msg.text or "") + " " + (msg.caption or "")
                links += pattern.findall(txt)

                # ۲. entities (لینک‌های کلیک‌پذیر داخل متن)
                for entities in [msg.entities or [], msg.caption_entities or []]:
                    for e in entities:
                        if hasattr(e, 'url') and e.url:
                            links += pattern.findall(e.url)

                # ۳. دکمه‌های inline
                if msg.reply_markup:
                    try:
                        kb = msg.reply_markup
                        rows = getattr(kb, 'inline_keyboard', None)
                        if rows:
                            for row in rows:
                                for btn in row:
                                    url = getattr(btn, 'url', None)
                                    if url:
                                        links += pattern.findall(url)
                    except Exception:
                        pass

                # ۴. web preview
                if msg.web_page and hasattr(msg.web_page, 'url') and msg.web_page.url:
                    links += pattern.findall(msg.web_page.url)

            # برای صفحهٔ بعدی، از آخرین پیام این batch ادامه بده
            offset_id = batch[-1].id

            if len(batch) < BATCH:
                # یعنی به انتهای تاریخچهٔ کانال رسیدیم
                break

        await uc.stop()
    except Exception as ex:
        print(f"[ExtractLinks] {ex}")
        try:
            await uc.stop()
        except Exception:
            pass

    # پاکسازی: حذف کاراکترهای اضافی از انتها + حذف تکراری
    cleaned = []
    for lnk in links:
        lnk = lnk.rstrip('.,;:!?)\"\'')
        if lnk not in cleaned:
            cleaned.append(lnk)

    return cleaned[:limit]


async def _join_links(bot_client, acc_id, links, min_d, max_d, tag=""):
    """عضویت در لینک‌ها با هندل کامل خطاها + ذخیره برچسب"""
    uc = await get_user_client(acc_id)
    if not uc:
        return
    await uc.start()
    me = await uc.get_me()
    acc_display = me.phone_number or str(me.id)
    ok_links, fail_links = [], []
    row = q("SELECT auto_leave_limited FROM accounts WHERE id=%s", (acc_id,))
    auto_leave = row[0][0] if row else 0

    for i, link in enumerate(links, 1):
        if is_stopped():
            await bot_client.send_message(ADMIN_ID, "🛑 عملیات توسط کاربر متوقف شد.")
            break

        # تبدیل لینک به فرمت قابل استفاده برای Pyrogram
        link_clean = link.strip()
        if link_clean.startswith("@"):
            target = link_clean.lstrip("@")
        elif "t.me/+" in link_clean or "t.me/joinchat/" in link_clean:
            # لینک دعوت خصوصی — کامل بده
            target = link_clean
        elif "t.me/" in link_clean:
            # لینک عمومی — فقط username بگیر
            target = link_clean.split("t.me/")[-1].strip("/").split("?")[0]
        else:
            target = link_clean
        try:
            result = await uc.join_chat(target)
            ok_links.append(link)
            # ذخیره گروه با برچسب
            if result and hasattr(result, 'id'):
                chat_title = getattr(result, 'title', '') or ''
                u("INSERT INTO group_tags (admin_id,account_id,chat_id,chat_title,tag_name) "
                  "VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE tag_name=%s, chat_title=%s",
                  (ADMIN_ID, acc_id, result.id, chat_title, tag, tag, chat_title))
                # چک عضویت اجباری بات‌محور (ربات گروه ممکنه بخواد کانال دیگه‌ای رو هم جوین کنیم)
                try:
                    fj_result = await detect_and_handle_bot_forced_join(uc, result.id)
                    if fj_result.get("forced_join_detected"):
                        channel = fj_result.get("channel", "")
                        joined = fj_result.get("joined", False)
                        if joined:
                            await bot_client.send_message(
                                ADMIN_ID,
                                f"🔗 **عضویت اجباری تشخیص داده شد**\n"
                                f"گروه: `{link}`\n"
                                f"اکانت: `{acc_display}`\n"
                                f"کانال اجباری: @{channel}\n"
                                f"✅ عضو کانال شدید"
                            )
                        else:
                            await bot_client.send_message(
                                ADMIN_ID,
                                f"⚠️ **عضویت اجباری تشخیص داده شد**\n"
                                f"گروه: `{link}`\n"
                                f"اکانت: `{acc_display}`\n"
                                f"کانال اجباری: @{channel}\n"
                                f"❌ عضویت در کانال ناموفق بود"
                            )
                except Exception as fj_err:
                    print(f"[JoinLinks] خطا در تشخیص عضویت اجباری: {fj_err}")
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
                result = await uc.join_chat(target)
                ok_links.append(link)
                if result and hasattr(result, 'id'):
                    chat_title = getattr(result, 'title', '') or ''
                    u("INSERT INTO group_tags (admin_id,account_id,chat_id,chat_title,tag_name) "
                      "VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE tag_name=%s, chat_title=%s",
                      (ADMIN_ID, acc_id, result.id, chat_title, tag, tag, chat_title))
            except Exception:
                fail_links.append(link)

        except UserAlreadyParticipant:
            ok_links.append(link)

        except InviteRequestSent:
            ok_links.append(link)
            await bot_client.send_message(
                ADMIN_ID,
                f"⏳ **درخواست عضویت ارسال شد**\n"
                f"گروه: `{link}`\n"
                f"اکانت: `{acc_display}`\n"
                f"منتظر تأیید ادمین گروه..."
            )

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
    # ذخیره لینک‌های موفق در used_links تا دفعه بعد تکراری شناخته بشن
    if ok_links:
        _save_used_links(ok_links)
        # آپدیت وضعیت joined در linkdoni_links
        for lnk in ok_links:
            h = _link_hash(lnk)
            try:
                u("UPDATE linkdoni_links SET joined=1 "
                  "WHERE admin_id=%s AND link_hash=%s", (ADMIN_ID, h))
            except Exception:
                pass
    tag_lbl = f" — 🏷 {tag}" if tag else ""
    report = (f"✅ عملیات عضویت تمام شد{tag_lbl}\n👤 {acc_display}\n"
              f"موفق: {len(ok_links)}\nناموفق: {len(fail_links)}")
    if fail_links:
        report += "\n\n❗️ ناموفق‌ها:\n" + "\n".join(fail_links)
    await bot_client.send_message(ADMIN_ID, report)


def get_filtered_accounts(tag_filter):
    """اکانت‌های فیلترشده بر اساس برچسب"""
    if tag_filter == "ALL":
        return q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
    elif tag_filter == "NOTAG":
        return q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                 "AND (tag='' OR tag IS NULL)", (ADMIN_ID,))
    else:
        return q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' AND tag=%s",
                 (ADMIN_ID, tag_filter))

def get_filtered_chat_ids(acc_id, tag_filter):
    """
    chat_id های فیلترشده برای یک اکانت.
    خروجی: (mode, set)
      mode='all'      → فیلتری نیست، همه گروه‌ها
      mode='include'  → فقط chat_id های داخل set
      mode='exclude'  → همه گروه‌ها به‌جز chat_id های داخل set (برای NOTAG)
    """
    if tag_filter == "ALL":
        return ("all", None)
    elif tag_filter == "NOTAG":
        # گروه‌هایی که برچسب غیرخالی دارن رو exclude می‌کنیم؛ بقیه (چه ثبت نشده چه خالی) NOTAG حساب میشن
        rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s "
                 "AND tag_name<>'' AND tag_name IS NOT NULL", (ADMIN_ID, acc_id))
        return ("exclude", set(r[0] for r in rows))
    else:
        rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s AND tag_name=%s",
                 (ADMIN_ID, acc_id, tag_filter))
        return ("include", set(r[0] for r in rows))


def _chat_allowed(chat_id, filter_result):
    mode, ids = filter_result
    if mode == "all":
        return True
    if mode == "include":
        return chat_id in ids
    if mode == "exclude":
        return chat_id not in ids
    return True


async def send_to_groups_smart(bot_client, acc_id, text, force_join=False, group_tag_filter="ALL"):
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

    # فیلتر گروه‌ها بر اساس برچسب
    filter_result = get_filtered_chat_ids(acc_id, group_tag_filter)

    ok = fail = limited = force_joined = left = 0

    try:
        await uc.start()
    except Exception as e:
        print(f"[SendGroups] خطا در اتصال اکانت {acc_id}: {e}")
        await bot_client.send_message(ADMIN_ID, f"❌ اتصال اکانت {display} ناموفق بود: {e}")
        return {"ok": 0, "fail": 0, "limited": 0, "force_joined": 0, "left": 0,
                "display": display, "skipped": True}

    try:
        dialogs = []
        async for dlg in uc.get_dialogs():
            if dlg.chat.type not in (en.ChatType.GROUP, en.ChatType.SUPERGROUP):
                continue
            # اعمال فیلتر برچسب
            if not _chat_allowed(dlg.chat.id, filter_result):
                continue
            dialogs.append(dlg)
    except Exception as e:
        print(f"[SendGroups] خطا در گرفتن لیست گروه‌ها برای {acc_id}: {e}")
        try: await uc.stop()
        except Exception: pass
        await bot_client.send_message(ADMIN_ID, f"❌ خطا در خواندن گروه‌های {display}: {e}")
        return {"ok": 0, "fail": 0, "limited": 0, "force_joined": 0, "left": 0,
                "display": display, "skipped": True}

    for dlg in dialogs:
        if is_stopped():
            break
        try:
            await uc.send_message(dlg.chat.id, text)
            ok += 1
            # تشخیص عضویت اجباری بات‌محور (نه از طرف Telegram بلکه ربات گروه)
            if do_force_join:
                fj_result = await detect_and_handle_bot_forced_join(uc, dlg.chat.id, original_text=text)
                if fj_result.get("forced_join_detected") and fj_result.get("resent"):
                    force_joined += 1
            # فاصله تصادفی بین گروه‌ها
            await asyncio.sleep(random.uniform(1.5, 4))

        except (ChatWriteForbidden, UserBannedInChannel, ChatRestricted,
                ChatSendMediaForbidden) as e:
            err_str = str(e)
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
                    if auto_leave:
                        try:
                            await uc.leave_chat(dlg.chat.id); left += 1
                        except Exception: pass
                    limited += 1
            elif auto_leave:
                try:
                    await uc.leave_chat(dlg.chat.id); left += 1
                except Exception: pass
                limited += 1
            else:
                limited += 1

        except SlowmodeWait:
            limited += 1

        except FloodWait as e:
            # صبر می‌کنیم و همین گروه را دوباره امتحان می‌کنیم، بقیه گروه‌ها رو ول نمی‌کنیم
            wait_s = min(e.value, 120)
            await bot_client.send_message(
                ADMIN_ID, f"❗️ محدودیت {wait_s} ثانیه — صبر و ادامه\n👤 {display}"
            )
            await asyncio.sleep(wait_s)
            try:
                await uc.send_message(dlg.chat.id, text); ok += 1
            except Exception: fail += 1

        except RPCError as e:
            err_str = str(e).lower()
            if any(k in err_str for k in ["forbidden","banned","restricted","rights"]):
                if auto_leave:
                    try:
                        await uc.leave_chat(dlg.chat.id); left += 1
                    except Exception: pass
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


# ─── توابع کمکی تشخیص لینک تکراری ────────────────────────────

def _normalize_link(link: str) -> str:
    """نرمال‌سازی لینک: lowercase + حذف پارامترهای اضافه مثل ?start=..."""
    link = link.strip().lower()
    link = link.split("?")[0]   # حذف query string
    link = link.rstrip("/")     # حذف slash انتهایی
    return link


def _link_hash(link: str) -> str:
    """تبدیل لینک نرمال‌شده به hash برای ذخیره در دیتابیس"""
    return hashlib.sha256(_normalize_link(link).encode()).hexdigest()


def _check_duplicate_links(links: list) -> tuple:
    """
    جداسازی لینک‌های جدید از تکراری.
    خروجی: (new_links, dup_links)
    """
    if not links:
        return [], []

    hashes = [_link_hash(l) for l in links]
    # کوئری یکجا برای همه hash‌ها
    placeholders = ",".join(["%s"] * len(hashes))
    existing = q(
        f"SELECT link_hash FROM used_links WHERE admin_id=%s AND link_hash IN ({placeholders})",
        (ADMIN_ID, *hashes)
    )
    existing_hashes = set(r[0] for r in existing) if existing else set()

    new_links, dup_links = [], []
    for link, h in zip(links, hashes):
        if h in existing_hashes:
            dup_links.append(link)
        else:
            new_links.append(link)

    return new_links, dup_links


def _save_used_links(links: list):
    """ذخیره لینک‌ها در جدول used_links (تکراری‌ها نادیده گرفته می‌شن)"""
    for link in links:
        norm = _normalize_link(link)
        h = _link_hash(link)
        try:
            u(
                "INSERT IGNORE INTO used_links (admin_id, link_hash, link_text) VALUES (%s,%s,%s)",
                (ADMIN_ID, h, norm[:500])
            )
        except Exception as e:
            print(f"[UsedLinks] خطا در ذخیره: {e}")
