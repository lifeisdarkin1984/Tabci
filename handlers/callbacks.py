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
           
