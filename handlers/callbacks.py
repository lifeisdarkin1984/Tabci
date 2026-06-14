import asyncio, time
from pyrogram import filters
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import q, u
from utils import (ADMIN_ID, get_step, get_step_data, set_step,
                   clear_step, get_user_client, is_stopped, set_stop)
from keyboards import *
import workers.reply_worker as rw
import workers.react_worker as rcw

def register(app):

    @app.on_callback_query()
    async def on_cb(client, cb: CallbackQuery):
        if cb.from_user.id != ADMIN_ID:
            await cb.answer("⛔️ دسترسی ندارید"); return
        d = cb.data

        try:
            if d == "back_main":
                await cb.message.edit_text("یک گزینه را انتخاب کنید:", reply_markup=main_menu_kb())

            elif d == "menu_tabchi":
                accs = q("SELECT id,phone,name FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if not accs:
                    await cb.answer("/add_account برای افزودن", show_alert=True); return
                await cb.message.edit_text("📌 **لیست تبچی‌های شما:**", reply_markup=tabchi_list_kb(accs))

            elif d == "menu_global":
                await cb.message.edit_text("🌐 **مدیریت همگانی**", reply_markup=global_kb())

            # ══ توقف تمام عملیات ══
            elif d == "g_stopall":
                set_stop(True)
                rw.STOP_FLAG = True
                rcw.STOP_FLAG = True
                for t in asyncio.all_tasks():
                    if t.get_name() in ("join_task","send_pv_task","send_grp_task","reply_task","react_task"):
                        t.cancel()
                await cb.message.edit_text(
                    "🛑 **تمام عملیات متوقف شد**\n\n"
                    "✅ عضویت در گروه‌ها\n✅ ارسال پیام‌ها\n✅ ریپلای و ری‌اکت",
                    reply_markup=global_kb()
                )

            # ══ حذف اکانت ══
            elif d.startswith("acc_del_yes_"):
                acc_id = d[12:]
                for tbl in ["accounts","secretary","scheduler","banners","join_settings","reply_rand","react_rand"]:
                    col = "id" if tbl == "accounts" else "account_id"
                    u(f"DELETE FROM {tbl} WHERE {col}=%s", (acc_id,))
                accs = q("SELECT id,phone,name FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if accs:
                    await cb.message.edit_text("✅ حذف شد.\n\n📌 لیست:", reply_markup=tabchi_list_kb(accs))
                else:
                    await cb.message.edit_text("✅ حذف شد.\n\n/add_account برای افزودن",
                                                reply_markup=back_kb("back_main"))

            elif d.startswith("acc_del_"):
                acc_id = d[8:]
                acc = q("SELECT name,phone FROM accounts WHERE id=%s", (acc_id,))
                name = f"{acc[0][0]} | {acc[0][1]}" if acc else acc_id
                await cb.message.edit_text(
                    f"❗️ حذف اکانت:\n👤 {name}",
                    reply_markup=confirm_kb(f"acc_del_yes_{acc_id}", "menu_tabchi")
                )

            elif d.startswith("acc_sel_"):
                acc_id = d[8:]
                acc = q("SELECT id,phone,name,username FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                a = acc[0]
                await cb.message.edit_text(
                    f"👤 **{a[2]}** | `{a[1]}`\n🔗 @{a[3] or 'ندارد'}",
                    reply_markup=acc_info_kb(acc_id)
                )

            elif d.startswith("acc_manage_"):
                acc_id = d[11:]
                acc = q("SELECT name,phone FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                await cb.message.edit_text(
                    f"⚙️ پنل مدیریت **{acc[0][0]}** | `{acc[0][1]}`",
                    reply_markup=manage_kb(acc_id)
                )

            elif d.startswith("acc_code_"):
                acc_id = d[9:]
                acc = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                await cb.answer(f"📱 کد به {acc[0][0]} ارسال می‌شود", show_alert=True)

            elif d.startswith("acc_status_"):
                acc_id = d[11:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ سشن پیدا نشد", show_alert=True); return
                try:
                    await uc.start(); me = await uc.get_me(); await uc.stop()
                    await cb.answer(f"✅ فعال\n👤 {me.first_name}", show_alert=True)
                except Exception as e:
                    await cb.answer(f"❌ {str(e)[:80]}", show_alert=True)

            elif d == "acc_refresh":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                ok = 0
                for (aid,) in accs:
                    try:
                        uc = await get_user_client(aid)
                        await uc.start(); me = await uc.get_me(); await uc.stop()
                        u("UPDATE accounts SET name=%s,username=%s,status='active' WHERE id=%s",
                          (me.first_name or str(me.id), me.username or "", aid))
                        ok += 1
                    except Exception:
                        u("UPDATE accounts SET status='inactive' WHERE id=%s", (aid,))
                await cb.answer(f"✅ {ok} اکانت بروزرسانی شد", show_alert=True)

            # ══ آمار اکانت ══
            elif d.startswith("m_stats_"):
                acc_id = d[8:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                try:
                    from pyrogram import enums as en
                    await uc.start(); me = await uc.get_me()
                    grps = chns = pvs = 0
                    async for dlg in uc.get_dialogs():
                        if dlg.chat.type in (en.ChatType.GROUP, en.ChatType.SUPERGROUP): grps += 1
                        elif dlg.chat.type == en.ChatType.CHANNEL: chns += 1
                        elif dlg.chat.type == en.ChatType.PRIVATE: pvs += 1
                    await uc.stop()
                    await cb.message.edit_text(
                        f"⚙️ پنل مدیریت `{me.id}`\n\n"
                        f"👤 {me.first_name or ''} {me.last_name or ''}\n"
                        f"📊 وضعیت: فعال ✅\n💬 کانال: {chns}\n"
                        f"🗣 گروه‌ها: {grps}\n🪡 پیوی‌ها: {pvs}\n"
                        f"🔗 @{me.username or 'ندارد'}",
                        reply_markup=back_kb(f"acc_manage_{acc_id}")
                    )
                except Exception as e:
                    await cb.answer(f"❌ {str(e)[:80]}", show_alert=True)

            # ══ خروج خودکار از گروه‌های محدود ══
            elif d.startswith("autoleave_tog_"):
                acc_id = d[14:]
                row = q("SELECT auto_leave_limited FROM accounts WHERE id=%s", (acc_id,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                u("UPDATE accounts SET auto_leave_limited=%s WHERE id=%s", (new, acc_id))
                await cb.answer(f"خروج خودکار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)
                await cb.message.edit_reply_markup(auto_leave_kb(acc_id, new))

            elif d.startswith("m_autoleave_"):
                acc_id = d[12:]
                row = q("SELECT auto_leave_limited FROM accounts WHERE id=%s", (acc_id,))
                active = row[0][0] if row else 0
                await cb.message.edit_text(
                    f"🚫 **خروج خودکار از گروه‌های محدود**\n\n"
                    f"با فعال بودن این گزینه، اگر در هنگام ارسال پیام محدود شوید "
                    f"به‌صورت خودکار از آن گروه خارج می‌شوید.\n\n"
                    f"وضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=auto_leave_kb(acc_id, active)
                )

            # ══ global خروج خودکار ══
            elif d == "g_autoleave_tog":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                row = q("SELECT auto_leave_limited FROM accounts WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                for (aid,) in accs:
                    u("UPDATE accounts SET auto_leave_limited=%s WHERE id=%s", (new, aid))
                await cb.answer(f"خروج خودکار {'فعال' if new else 'غیرفعال'} برای همه", show_alert=True)

            # ══ منشی خودکار ══
            elif d.startswith("m_sec_"):
                acc_id = d[6:]
                row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                await cb.message.edit_text(
                    f"👽 **پنل منشی خودکار**\n\nوضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=secretary_kb(acc_id, active)
                )

            elif d.startswith("sec_tog_"):
                acc_id = d[8:]
                row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO secretary (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"منشی {'فعال' if new else 'غیرفعال'} شد")
                await cb.message.edit_reply_markup(secretary_kb(acc_id, new))

            elif d.startswith("sec_b"):
                slot = int(d[5]); acc_id = d[7:]
                bnrs = q("SELECT slot,text,file_id FROM banners "
                         "WHERE account_id=%s AND context='secretary' ORDER BY slot", (acc_id,))
                txt = "✏️ **مدیریت بنرها**\n\n"
                for b in bnrs:
                    txt += f"═-═ {b[0]} ═-═\n💬 [{(b[1] or '')[:40]}...]\n📁 {'✅' if b[2] else '❌'}\n\n"
                if not bnrs: txt += "هیچ بنری ثبت نشده."
                await cb.message.edit_text(txt, reply_markup=banner_slot_kb(acc_id, slot, "secretary"))

            elif d.startswith("bn_add_"):
                _, _, acc_id, slot, ctx = d.split("_", 4)
                slot = int(slot)
                set_step(ADMIN_ID, f"bn_text_{acc_id}_{slot}_{ctx}")
                await cb.message.edit_text("📝 متن بنر را وارد کنید:")

            elif d.startswith("bn_del_"):
                _, _, acc_id, slot, ctx = d.split("_", 4)
                slot = int(slot)
                u("DELETE FROM banners WHERE account_id=%s AND slot=%s AND context=%s", (acc_id, slot, ctx))
                await cb.answer(f"✅ بنر {slot} حذف شد")
                await cb.message.edit_reply_markup(banner_slot_kb(acc_id, slot, ctx))

            elif d.startswith("bn_delall_"):
                _, _, acc_id, ctx = d.split("_", 3)
                u("DELETE FROM banners WHERE account_id=%s AND context=%s", (acc_id, ctx))
                await cb.answer("✅ همه بنرها حذف شدند")

            elif d.startswith("bn_back_"):
                _, _, acc_id, ctx = d.split("_", 3)
                if ctx == "secretary":
                    row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                    active = row[0][0] if row else 0
                    await cb.message.edit_text("👽 پنل منشی:", reply_markup=secretary_kb(acc_id, active))
                elif ctx == "g_secretary":
                    row = q("SELECT COUNT(*) FROM secretary WHERE is_active=1 AND admin_id=%s", (ADMIN_ID,))
                    active = (row[0][0] if row else 0) > 0
                    await cb.message.edit_text("🤖 **منشی خودکار همگانی**", reply_markup=global_sec_kb(active))
                else:
                    row2 = q("SELECT is_active FROM scheduler WHERE account_id=%s", (acc_id,))
                    active2 = row2[0][0] if row2 else 0
                    await cb.message.edit_text("⏰ پنل زمان‌بند:", reply_markup=scheduler_kb(acc_id, active2))


            # ══ زمان‌بند ══
            elif d.startswith("m_sch_"):
                acc_id = d[6:]
                row = q("SELECT is_active,interval_minutes FROM scheduler WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0; interval = row[0][1] if row else 10
                await cb.message.edit_text(
                    f"⏰ **پنل زمان‌بندی**\nفاصله: {interval} دقیقه\nوضعیت: {'✅' if active else '❌'}",
                    reply_markup=scheduler_kb(acc_id, active)
                )

            elif d.startswith("sch_tog_"):
                acc_id = d[8:]
                row = q("SELECT is_active FROM scheduler WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO scheduler (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"زمان‌بند {'فعال' if new else 'غیرفعال'} شد")
                await cb.message.edit_reply_markup(scheduler_kb(acc_id, new))

            elif d.startswith("sch_time_"):
                acc_id = d[9:]
                set_step(ADMIN_ID, f"sch_int_{acc_id}")
                await cb.message.edit_text("⏱ زمان ارسال (دقیقه):")

            elif d.startswith("sch_txt_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"bn_text_{acc_id}_1_scheduler")
                await cb.message.edit_text("📝 متن بنر زمان‌بند:")

            elif d.startswith("sch_ref_"):
                await cb.answer("🔄 بروزرسانی شد", show_alert=True)

            elif d.startswith("sch_fwd_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"sch_fwd_link_{acc_id}")
                await cb.message.edit_text("📤 لینک پیام برای فوروارد:", reply_markup=back_kb(f"m_sch_{acc_id}"))

            # ══ استخراج لینک ══
            elif d.startswith("m_ext_"):
                acc_id = d[6:]
                await cb.message.edit_text(
                    "🔗 **استخراج لینک**\nنوع استخراج را انتخاب کنید:",
                    reply_markup=extract_kb(acc_id)
                )

            elif d.startswith("ext_one_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"ext_ch_{acc_id}")
                await cb.message.edit_text(
                    "🔗 یوزرنیم لینکدونی را بفرستید:\nمثال: `@link4you`",
                    reply_markup=back_kb(f"m_ext_{acc_id}")
                )

            elif d.startswith("ext_multi_"):
                acc_id = d[10:]
                set_step(ADMIN_ID, f"ext_multi_ch_{acc_id}")
                await cb.message.edit_text(
                    "🔗🔗 یوزرنیم لینکدونی‌ها را هر کدام در یک خط بفرستید:",
                    reply_markup=back_kb(f"m_ext_{acc_id}")
                )

            # ══ لیست گروه‌ها ══
            elif d.startswith("m_grps_"):
                acc_id = d[7:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                fj = row[0][0] if row else 0
                await cb.message.edit_text("👥 **لیست گروه‌های من**", reply_markup=groups_kb(acc_id, fj))

            elif d.startswith("grp_stats_"):
                acc_id = d[10:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums as en
                grps = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (en.ChatType.GROUP, en.ChatType.SUPERGROUP): grps += 1
                await uc.stop()
                await cb.answer(f"👥 گروه‌ها: {grps}", show_alert=True)

            elif d.startswith("grp_leave_limited_"):
                acc_id = d[18:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums as en
                from pyrogram.errors import ChatWriteForbidden
                left = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (en.ChatType.GROUP, en.ChatType.SUPERGROUP):
                        try:
                            await uc.send_message(dlg.chat.id, ".")
                        except ChatWriteForbidden:
                            await uc.leave_chat(dlg.chat.id); left += 1
                await uc.stop()
                await cb.answer(f"✅ از {left} گروه محدود خارج شد", show_alert=True)

            elif d.startswith("grp_fj_tog_"):
                acc_id = d[11:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                  "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE force_join_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"عضویت اجبار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)
                await cb.message.edit_reply_markup(groups_kb(acc_id, new))

            # ══ حذف پیوی‌ها ══
            elif d.startswith("delpv_yes_"):
                acc_id = d[10:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums as en
                count = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type == en.ChatType.PRIVATE:
                        try:
                            await uc.delete_history(dlg.chat.id, revoke=True); count += 1
                        except Exception: pass
                await uc.stop()
                await cb.message.edit_text(f"✅ {count} پیوی حذف شد.", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_delpv_"):
                acc_id = d[8:]
                await cb.message.edit_text("🗑 حذف همه پیوی‌ها؟",
                                            reply_markup=confirm_kb(f"delpv_yes_{acc_id}", f"acc_manage_{acc_id}"))

            # ══ عضویت در لینک‌ها ══
            elif d.startswith("join_go_"):
                acc_id = d[8:]
                links = [l for l in get_step_data(ADMIN_ID).splitlines() if l.strip()]
                row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
                mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                set_stop(False)
                await cb.message.edit_text(f"🚀 عملیات عضویت {len(links)} لینک شروع شد...")
                from handlers.text_handler import _join_links
                t = asyncio.create_task(_join_links(client, acc_id, links, mn, mx))
                t.set_name("join_task")
                clear_step(ADMIN_ID)

            elif d.startswith("m_join_"):
                acc_id = d[7:]
                row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
                mn, mx = (row[0][0]//60, row[0][1]//60) if row else (3, 7)
                set_step(ADMIN_ID, f"join_{acc_id}")
                await cb.message.edit_text(
                    f"➕ **عضو شدن در لینک گروه‌ها**\n\n⏱ فاصله: {mn}–{mx} دقیقه\n\n"
                    f"لینک‌ها را هر کدام در یک خط وارد کنید:",
                    reply_markup=back_kb(f"acc_manage_{acc_id}")
                )

            # ══ عضویت اجبار ══
            elif d.startswith("fj_tog_"):
                acc_id = d[7:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                  "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE force_join_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"عضویت اجبار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)

            elif d.startswith("m_fj_"):
                acc_id = d[5:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                fj = row[0][0] if row else 0
                await cb.message.edit_text(
                    f"🕵️ **عضویت اجباری**\n\nبا فعال بودن، هنگام ارسال پیام اگر با عضویت اجبار مواجه شد "
                    f"خودکار عضو کانال می‌شود و پیام را ارسال می‌کند.\n\n"
                    f"وضعیت: {'✅ فعال' if fj else '❌ غیرفعال'}",
                    reply_markup=confirm_kb(f"fj_tog_{acc_id}", f"acc_manage_{acc_id}")
                )

            # ══ ارسال پیام ══
            elif d.startswith("spv_go_"):
                acc_id = d[7:]
                text = get_step_data(ADMIN_ID)
                set_stop(False)
                await cb.message.edit_text("⏳ در حال ارسال به پیوی‌ها...")
                t = asyncio.create_task(_send_to_pvs(client, acc_id, text))
                t.set_name("send_pv_task")
                clear_step(ADMIN_ID)

            elif d.startswith("m_spv_"):
                acc_id = d[6:]
                set_step(ADMIN_ID, f"spv_{acc_id}")
                await cb.message.edit_text("💬 متن پیام برای پیوی‌ها:", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("sgrp_go_"):
                acc_id = d[8:]
                text = get_step_data(ADMIN_ID)
                set_stop(False)
                await cb.message.edit_text("⏳ در حال ارسال به گروه‌ها...")
                t = asyncio.create_task(_send_to_groups_task(client, acc_id, text))
                t.set_name("send_grp_task")
                clear_step(ADMIN_ID)

            elif d.startswith("m_sgrp_"):
                acc_id = d[7:]
                set_step(ADMIN_ID, f"sgrp_{acc_id}")
                await cb.message.edit_text("📢 متن پیام برای گروه‌ها:", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            # ══ خروج از همه ══
            elif d.startswith("leave_yes_"):
                acc_id = d[10:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums as en
                count = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (en.ChatType.GROUP, en.ChatType.SUPERGROUP, en.ChatType.CHANNEL):
                        try:
                            await uc.leave_chat(dlg.chat.id); count += 1; await asyncio.sleep(0.5)
                        except Exception: pass
                await uc.stop()
                await cb.message.edit_text(f"✅ از {count} گروه/کانال خارج شد.",
                                            reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_leave_"):
                acc_id = d[8:]
                await cb.message.edit_text("⚠️ خروج از **تمام گروه‌ها و کانال‌ها**؟",
                                            reply_markup=confirm_kb(f"leave_yes_{acc_id}", f"acc_manage_{acc_id}"))

            # ══ پروفایل ══
            elif d.startswith("m_bio_"):
                set_step(ADMIN_ID, f"set_bio_{d[6:]}"); await cb.message.edit_text("📝 بیو جدید:", reply_markup=back_kb(f"acc_manage_{d[6:]}"))
            elif d.startswith("m_uname_"):
                set_step(ADMIN_ID, f"set_uname_{d[8:]}"); await cb.message.edit_text("🆔 نام کاربری جدید:", reply_markup=back_kb(f"acc_manage_{d[8:]}"))
            elif d.startswith("m_fname_"):
                set_step(ADMIN_ID, f"set_fname_{d[8:]}"); await cb.message.edit_text("👤 نام جدید:", reply_markup=back_kb(f"acc_manage_{d[8:]}"))
            elif d.startswith("m_lname_"):
                set_step(ADMIN_ID, f"set_lname_{d[8:]}"); await cb.message.edit_text("👤 فامیلی جدید:", reply_markup=back_kb(f"acc_manage_{d[8:]}"))

            # ══ ریپلای رندم ══
            elif d.startswith("m_reply_"):
                acc_id = d[8:]
                row = q("SELECT is_active,interval_minutes,message_text FROM reply_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0; interval = row[0][1] if row else 30; msg = (row[0][2] if row else "") or "تنظیم نشده"
                await cb.message.edit_text(
                    f"↩️ **پنل ریپلای رندم**\n\nپیام: {msg}\nفاصله: {interval} دقیقه\nوضعیت: {'✅' if active else '❌'}",
                    reply_markup=reply_rand_kb(acc_id, active)
                )

            elif d.startswith("rr_setmsg_"):
                acc_id = d[10:]
                set_step(ADMIN_ID, f"rr_msg_{acc_id}")
                await cb.message.edit_text("✏️ متن پیام ریپلای:", reply_markup=back_kb(f"m_reply_{acc_id}"))

            elif d.startswith("rr_time_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"rr_int_{acc_id}")
                await cb.message.edit_text("⏱ فاصله ریپلای (دقیقه):")

            elif d.startswith("rr_tog_"):
                acc_id = d[7:]
                row = q("SELECT is_active FROM reply_rand WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO reply_rand (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"ریپلای {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active FROM reply_rand WHERE account_id=%s", (acc_id,))
                await cb.message.edit_reply_markup(reply_rand_kb(acc_id, row2[0][0]))

            elif d.startswith("rr_run_"):
                acc_id = d[7:]
                row = q("SELECT message_text FROM reply_rand WHERE account_id=%s", (acc_id,))
                if not row or not row[0][0]:
                    await cb.answer("❌ اول پیام تنظیم کنید", show_alert=True); return
                set_stop(False); rw.STOP_FLAG = False
                await cb.answer("🚀 شروع شد")
                asyncio.create_task(rw.run_once(acc_id, row[0][0]))

            # ══ ری‌اکت رندم ══
            elif d.startswith("m_react_"):
                acc_id = d[8:]
                row = q("SELECT is_active,interval_minutes FROM react_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0; interval = row[0][1] if row else 30
                await cb.message.edit_text(
                    f"😀 **پنل ری‌اکت رندم**\n\nفاصله: {interval} دقیقه\nوضعیت: {'✅' if active else '❌'}",
                    reply_markup=react_rand_kb(acc_id, active)
                )

            elif d.startswith("rc_time_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"rc_int_{acc_id}")
                await cb.message.edit_text("⏱ فاصله ری‌اکت (دقیقه):")

            elif d.startswith("rc_tog_"):
                acc_id = d[7:]
                row = q("SELECT is_active FROM react_rand WHERE account_id=%s", (acc_id,))
                new = 0 if (row[0][0] if row else 0) else 1
                u("INSERT INTO react_rand (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"ری‌اکت {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active FROM react_rand WHERE account_id=%s", (acc_id,))
                await cb.message.edit_reply_markup(react_rand_kb(acc_id, row2[0][0]))

            elif d.startswith("rc_run_"):
                acc_id = d[7:]
                set_stop(False); rcw.STOP_FLAG = False
                await cb.answer("🚀 شروع شد")
                asyncio.create_task(rcw.run_once(acc_id))

            # ══ global ══
            elif d == "g_stats":
                accs = q("SELECT id,name,phone FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                total_g = total_p = 0
                txt = f"📊 **آمار ({len(accs)} اکانت)**\n\n"
                for a in accs:
                    uc = await get_user_client(a[0]); grps = pvs = 0
                    try:
                        from pyrogram import enums as en
                        await uc.start()
                        async for dlg in uc.get_dialogs():
                            if dlg.chat.type in (en.ChatType.GROUP, en.ChatType.SUPERGROUP): grps += 1
                            elif dlg.chat.type == en.ChatType.PRIVATE: pvs += 1
                        await uc.stop()
                    except Exception: pass
                    total_g += grps; total_p += pvs
                    txt += f"👤 {a[1]} | `{a[2]}`\n🗣 {grps} گروه | 🪡 {pvs} پیوی\n\n"
                txt += f"─────\n🗣 کل گروه‌ها: {total_g}\n🪡 کل پیوی‌ها: {total_p}"
                await cb.message.edit_text(txt, reply_markup=back_kb("menu_global"))

            elif d == "g_status":
                accs = q("SELECT id,name,phone FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                txt = "♻️ **وضعیت:**\n\n"
                for a in accs:
                    uc = await get_user_client(a[0])
                    try:
                        await uc.start(); await uc.get_me(); await uc.stop()
                        txt += f"✅ {a[1]} | `{a[2]}`\n"
                    except Exception:
                        txt += f"❌ {a[1]} | `{a[2]}`\n"
                await cb.message.edit_text(txt, reply_markup=back_kb("menu_global"))

            elif d == "g_bio":
                set_step(ADMIN_ID, "g_bio"); await cb.message.edit_text("📝 بیو جدید برای همه:", reply_markup=back_kb("menu_global"))
            elif d == "g_fname":
                set_step(ADMIN_ID, "g_fname"); await cb.message.edit_text("👤 نام جدید برای همه:", reply_markup=back_kb("menu_global"))
            elif d == "g_lname":
                set_step(ADMIN_ID, "g_lname"); await cb.message.edit_text("👤 فامیلی جدید برای همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_spv":
                set_step(ADMIN_ID, "g_spv"); await cb.message.edit_text("💬 متن پیام برای پیوی‌های همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_spv_go":
                text = get_step_data(ADMIN_ID)
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                set_stop(False)
                for (aid,) in accs:
                    t = asyncio.create_task(_send_to_pvs(client, aid, text)); t.set_name("send_pv_task")
                await cb.message.edit_text("✅ شروع شد.", reply_markup=global_kb()); clear_step(ADMIN_ID)

            elif d == "g_sgrp":
                set_step(ADMIN_ID, "g_sgrp"); await cb.message.edit_text("📢 متن پیام برای گروه‌های همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_sgrp_go":
                text = get_step_data(ADMIN_ID)
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                set_stop(False)
                for (aid,) in accs:
                    t = asyncio.create_task(_send_to_groups_task(client, aid, text)); t.set_name("send_grp_task")
                await cb.message.edit_text("✅ شروع شد.", reply_markup=global_kb()); clear_step(ADMIN_ID)

            elif d == "g_join":
                set_step(ADMIN_ID, "g_join"); await cb.message.edit_text("➕ لینک‌ها را هر کدام در یک خط:", reply_markup=back_kb("menu_global"))

            elif d == "g_join_split":
                links = [l for l in get_step_data(ADMIN_ID).splitlines() if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if not accs:
                    await cb.answer("اکانتی وجود ندارد", show_alert=True); return
                per = max(1, len(links) // len(accs))
                set_stop(False)
                await cb.message.edit_text(f"🔀 {len(links)} لینک بین {len(accs)} اکانت تقسیم شد.")
                for i, (aid,) in enumerate(accs):
                    chunk = links[i*per:(i+1)*per]
                    if chunk:
                        row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                        mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                        from handlers.text_handler import _join_links
                        t = asyncio.create_task(_join_links(client, aid, chunk, mn, mx)); t.set_name("join_task")
                clear_step(ADMIN_ID)

            elif d == "g_join_all":
                links = [l for l in get_step_data(ADMIN_ID).splitlines() if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                set_stop(False)
                await cb.message.edit_text(f"📋 همه اکانت‌ها {len(links)} لینک.")
                for (aid,) in accs:
                    row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                    mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                    from handlers.text_handler import _join_links
                    t = asyncio.create_task(_join_links(client, aid, links, mn, mx)); t.set_name("join_task")
                clear_step(ADMIN_ID)

            elif d == "g_fj":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                for (aid,) in accs:
                    u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                      "VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE force_join_active=1", (aid, ADMIN_ID))
                await cb.answer("✅ عضویت اجبار برای همه فعال شد", show_alert=True)

            elif d == "g_sch":
                await cb.message.edit_text("⏰ از لیست تبچی اکانت مورد نظر را انتخاب کنید.",
                                            reply_markup=back_kb("menu_global"))

            elif d == "g_fwdgrp":
                set_step(ADMIN_ID, "g_fwdgrp"); await cb.message.edit_text("📤 لینک پیام:", reply_markup=back_kb("menu_global"))

            elif d == "g_autoleave":
                row = q("SELECT auto_leave_limited FROM accounts WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
                active = row[0][0] if row else 0
                await cb.message.edit_text(
                    f"🚫 **خروج خودکار از گروه‌های محدود (همگانی)**\n\n"
                    f"وضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            f"{'🔴 غیرفعال' if active else '🟢 فعال'} برای همه",
                            callback_data="g_autoleave_tog")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")]
                    ])
                )

            elif d == "g_sec":
                row = q("SELECT COUNT(*) FROM secretary WHERE is_active=1 AND admin_id=%s", (ADMIN_ID,))
                active = (row[0][0] if row else 0) > 0
                await cb.message.edit_text("🤖 **منشی خودکار همگانی**", reply_markup=global_sec_kb(active))

            elif d.startswith("gsec_b"):
                slot = int(d[6])
                bnrs = q("SELECT slot,text,file_id FROM banners WHERE admin_id=%s AND context='g_secretary' ORDER BY slot", (ADMIN_ID,))
                txt = "✏️ **بنرهای همگانی منشی**\n\n"
                for b in bnrs:
                    txt += f"═-═ {b[0]} ═-═\n💬 [{(b[1] or '')[:40]}...]\n📁 {'✅' if b[2] else '❌'}\n\n"
                if not bnrs: txt += "هیچ بنری."
                await cb.message.edit_text(txt, reply_markup=banner_slot_kb("global", slot, "g_secretary"))

            elif d == "gsec_tog":
                row = q("SELECT COUNT(*) FROM secretary WHERE is_active=1 AND admin_id=%s", (ADMIN_ID,))
                new = 0 if (row[0][0] if row else 0) > 0 else 1
                u("UPDATE secretary SET is_active=%s WHERE admin_id=%s", (new, ADMIN_ID))
                await cb.answer(f"منشی همگانی {'فعال' if new else 'غیرفعال'} شد", show_alert=True)

            elif d == "g_rr":
                await cb.message.edit_text(
                    "↩️ **ریپلای رندم همگانی**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ اجرای دستی همه", callback_data="g_rr_run")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")]
                    ])
                )

            elif d == "g_rr_run":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                set_stop(False); rw.STOP_FLAG = False
                for (aid,) in accs:
                    row = q("SELECT message_text FROM reply_rand WHERE account_id=%s", (aid,))
                    if row and row[0][0]:
                        asyncio.create_task(rw.run_once(aid, row[0][0]))
                await cb.answer(f"✅ برای {len(accs)} اکانت شروع شد", show_alert=True)

            elif d == "g_rc":
                await cb.message.edit_text(
                    "😀 **ری‌اکت رندم همگانی**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("▶️ اجرای دستی همه", callback_data="g_rc_run")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")]
                    ])
                )

            elif d == "g_rc_run":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                set_stop(False); rcw.STOP_FLAG = False
                for (aid,) in accs:
                    asyncio.create_task(rcw.run_once(aid))
                await cb.answer(f"✅ برای {len(accs)} اکانت شروع شد", show_alert=True)

        except Exception as e:
            print(f"[CB ERROR] {d}: {e}")
            try:
                await cb.answer(f"❌ {str(e)[:100]}", show_alert=True)
            except Exception:
                pass

        try:
            await cb.answer()
        except Exception:
            pass


# ─── helpers ────────────────────────────────────────────────

async def _send_to_pvs(bot_client, acc_id, text):
    from pyrogram import enums as en
    uc = await get_user_client(acc_id)
    if not uc: return
    me_info = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
    display = me_info[0][0] if me_info else acc_id
    ok = fail = 0
    await uc.start()
    async for dlg in uc.get_dialogs():
        if is_stopped(): break
        if dlg.chat.type == en.ChatType.PRIVATE:
            try:
                await uc.send_message(dlg.chat.id, text); ok += 1; await asyncio.sleep(2)
            except Exception: fail += 1
    await uc.stop()
    await bot_client.send_message(ADMIN_ID, f"✅ پیوی‌ها\n👤 {display}\n✔️ {ok}\n❌ {fail}")


async def _send_to_groups_task(bot_client, acc_id, text):
    from handlers.text_handler import send_to_groups_smart
    result = await send_to_groups_smart(bot_client, acc_id, text)
    report = (
        f"✅ ارسال به گروه‌ها تمام شد\n"
        f"👤 {result.get('display', acc_id)}\n"
        f"✔️ موفق: {result['ok']}\n"
        f"❌ ناموفق: {result['fail']}\n"
        f"🚫 محدود شده: {result['limited']}\n"
        f"🔗 عضویت اجبار انجام شد: {result['force_joined']}\n"
        f"🚪 از گروه‌های محدود خارج شد: {result['left']}"
    )
    await bot_client.send_message(ADMIN_ID, report)
