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

            # ══ global عضویت اجبار ══
            elif d == "g_fj_tog":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                row = q("SELECT force_join_active FROM join_settings WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                for (aid,) in accs:
                    u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                      "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE force_join_active=%s",
                      (aid, ADMIN_ID, new, new))
                await cb.answer(f"عضویت اجبار {'فعال' if new else 'غیرفعال'} برای همه", show_alert=True)

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

            # ── انتخاب برچسب برای جوین تک‌اکانت ──
            elif d.startswith("jointag_"):
                # d = jointag_{acc_id}_tag_{tagname}
                rest = d[8:]  # {acc_id}_tag_{tagname}
                acc_id, _, tag_name = rest.partition("_tag_")
                links = [l for l in get_step_data(ADMIN_ID).splitlines() if l.strip()]
                chosen_tag = "" if tag_name == "NOTAG" else tag_name
                row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
                mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                tag_lbl = f"«{chosen_tag}»" if chosen_tag else "بدون برچسب"
                set_stop(False)
                await cb.message.edit_text(
                    f"🚀 عملیات عضویت {len(links)} لینک شروع شد...\n🏷 برچسب: {tag_lbl}"
                )
                from handlers.text_handler import _join_links
                t = asyncio.create_task(_join_links(client, acc_id, links, mn, mx,
                                                     tag=chosen_tag))
                t.set_name("join_task")
                clear_step(ADMIN_ID)

            # ── انتخاب برچسب برای جوین همگانی ──
            elif d == "gjoin_nodup" or d == "gjoin_all":
                import json
                raw = get_step_data(ADMIN_ID)
                try:
                    data = json.loads(raw)
                except Exception:
                    await cb.answer("❌ خطا در بازیابی داده.", show_alert=True)
                    return
                if d == "gjoin_nodup":
                    chosen_links = data.get("new", [])
                else:
                    chosen_links = data.get("all", [])
                if not chosen_links:
                    await cb.answer("❌ هیچ لینکی برای جوین وجود ندارد.", show_alert=True)
                    clear_step(ADMIN_ID)
                    return
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                set_step(ADMIN_ID, "g_join_tag", "\n".join(chosen_links))
                await cb.message.edit_text(
                    f"✅ {len(chosen_links)} لینک انتخاب شد.\nبرچسب گروه‌ها را انتخاب کنید:",
                    reply_markup=tag_select_kb(tag_list, "gjointag", show_all=False)
                )

            elif d.startswith("gjointag_tag_"):
                tag_name = d[13:]
                chosen_tag = "" if tag_name == "NOTAG" else tag_name
                links = [l for l in get_step_data(ADMIN_ID).splitlines() if l.strip()]
                tag_lbl = f"«{chosen_tag}»" if chosen_tag else "بدون برچسب"
                # ذخیره برچسب در step_data با جداکننده
                set_step(ADMIN_ID, "g_join_links",
                         f"TAG:{chosen_tag}\n" + "\n".join(links))
                await cb.message.edit_text(
                    f"✅ {len(links)} لینک — 🏷 {tag_lbl}\nنوع عضویت را انتخاب کنید:",
                    reply_markup=global_join_kb()
                )

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
                msg_text = get_step_data(ADMIN_ID)
                # ذخیره متن + acc_id برای مرحله بعد
                set_step(ADMIN_ID, f"sgrp_gtag_{acc_id}", msg_text)
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "📢 ارسال به کدوم گروه‌ها؟",
                    reply_markup=tag_select_kb(tag_list, f"sgrpgtag_{acc_id}")
                )

            # ── انتخاب برچسب گروه برای ارسال تک‌اکانت ──
            elif d.startswith("sgrpgtag_"):
                rest = d[9:]  # {acc_id}_tag_{tagname}
                acc_id, _, tag_name = rest.partition("_tag_")
                msg_text = get_step_data(ADMIN_ID)
                group_tag = "" if tag_name == "ALL" else ("" if tag_name == "NOTAG" else tag_name)
                group_tag_filter = tag_name  # ALL / NOTAG / tagname
                set_stop(False)
                await cb.message.edit_text("⏳ در حال ارسال به گروه‌ها...")
                t = asyncio.create_task(_send_to_groups_task(client, acc_id, msg_text,
                                                              group_tag_filter=group_tag_filter))
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

            elif d.startswith("rr_banners_"):
                acc_id = d[11:]
                bnrs = q("SELECT slot,text,file_id FROM reply_rand_banners "
                         "WHERE account_id=%s ORDER BY slot", (acc_id,))
                back = "g_rr" if acc_id == "global" else f"m_reply_{acc_id}"
                txt = "📋 **مدیریت متن‌های ریپلای**\n\n"
                if bnrs:
                    for b in bnrs:
                        short = (b[1] or "")[:40]
                        txt += f"═-═ {b[0]} ═-═\n💬 {short}{'...' if b[1] and len(b[1])>40 else ''}\n📁 {'✅' if b[2] else '❌'}\n\n"
                else:
                    txt += "هیچ متنی تنظیم نشده."
                txt += "\nهر دوره یکی به ترتیب شماره ارسال می‌شود."
                await cb.message.edit_text(txt, reply_markup=reply_banner_list_kb(acc_id, bnrs, back_to=back))

            elif d.startswith("rr_badd_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"rr_badd_{acc_id}")
                back = "g_rr" if acc_id == "global" else f"m_reply_{acc_id}"
                await cb.message.edit_text("📝 متن ریپلای جدید را وارد کنید:",
                                            reply_markup=back_kb(f"rr_banners_{acc_id}"))

            elif d.startswith("rr_bdel_"):
                parts = d.split("_", 3)
                acc_id, slot = parts[2], int(parts[3])
                u("DELETE FROM reply_rand_banners WHERE account_id=%s AND slot=%s", (acc_id, slot))
                # شماره‌گذاری مجدد
                remaining = q("SELECT id FROM reply_rand_banners WHERE account_id=%s ORDER BY slot", (acc_id,))
                for i, (rid,) in enumerate(remaining, 1):
                    u("UPDATE reply_rand_banners SET slot=%s WHERE id=%s", (i, rid))
                await cb.answer(f"✅ متن {slot} حذف شد")
                bnrs = q("SELECT slot,text,file_id FROM reply_rand_banners WHERE account_id=%s ORDER BY slot", (acc_id,))
                back = "g_rr" if acc_id == "global" else f"m_reply_{acc_id}"
                await cb.message.edit_reply_markup(reply_banner_list_kb(acc_id, bnrs, back_to=back))

            elif d.startswith("rr_bdelall_"):
                acc_id = d[11:]
                u("DELETE FROM reply_rand_banners WHERE account_id=%s", (acc_id,))
                await cb.answer("✅ همه متن‌ها حذف شدند")
                back = "g_rr" if acc_id == "global" else f"m_reply_{acc_id}"
                await cb.message.edit_reply_markup(reply_banner_list_kb(acc_id, [], back_to=back))

            elif d.startswith("rr_gtag_"):
                acc_id = d[8:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "🏷 فیلتر گروه‌ها برای ریپلای:",
                    reply_markup=tag_select_kb(tag_list, f"rr_gtag_set_{acc_id}")
                )

            elif d.startswith("rr_gtag_set_"):
                rest = d[12:]  # {acc_id}_tag_{tagname}
                acc_id, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO reply_rand (account_id,admin_id,group_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE group_tag_filter=%s", (acc_id, ADMIN_ID, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر گروه: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM reply_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(reply_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

            elif d.startswith("rr_atag_"):
                acc_id = d[8:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "👤 فیلتر اکانت‌ها برای ریپلای:",
                    reply_markup=tag_select_kb(tag_list, f"rr_atag_set_{acc_id}")
                )

            elif d.startswith("rr_atag_set_"):
                rest = d[12:]
                acc_id, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO reply_rand (account_id,admin_id,acc_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE acc_tag_filter=%s", (acc_id, ADMIN_ID, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر اکانت: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM reply_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(reply_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

            elif d.startswith("rc_gtag_"):
                acc_id = d[8:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "🏷 فیلتر گروه‌ها برای ری‌اکت:",
                    reply_markup=tag_select_kb(tag_list, f"rc_gtag_set_{acc_id}")
                )

            elif d.startswith("rc_gtag_set_"):
                rest = d[12:]
                acc_id, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO react_rand (account_id,admin_id,group_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE group_tag_filter=%s", (acc_id, ADMIN_ID, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر گروه: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM react_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(react_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

            elif d.startswith("rc_atag_"):
                acc_id = d[8:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "👤 فیلتر اکانت‌ها برای ری‌اکت:",
                    reply_markup=tag_select_kb(tag_list, f"rc_atag_set_{acc_id}")
                )

            elif d.startswith("rc_atag_set_"):
                rest = d[12:]
                acc_id, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO react_rand (account_id,admin_id,acc_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE acc_tag_filter=%s", (acc_id, ADMIN_ID, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر اکانت: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM react_rand WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(react_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

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
                if new:
                    set_stop(False); rw.STOP_FLAG = False
                await cb.answer(f"ریپلای {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM reply_rand WHERE account_id=%s", (acc_id,))
                active = row2[0][0] if row2 else 0
                gtag = row2[0][1] if row2 else "ALL"
                atag = row2[0][2] if row2 else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(reply_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

            elif d.startswith("rr_run_"):
                acc_id = d[7:]
                bnrs = q("SELECT text FROM reply_rand_banners WHERE account_id=%s ORDER BY slot", (acc_id,))
                if not bnrs:
                    await cb.answer("❌ اول متن تنظیم کنید", show_alert=True); return
                set_stop(False); rw.STOP_FLAG = False
                row_cfg = q("SELECT last_index, group_tag_filter, acc_tag_filter "
                            "FROM reply_rand WHERE account_id=%s", (acc_id,))
                gtag = (row_cfg[0][1] if row_cfg else None) or "ALL"
                atag = (row_cfg[0][2] if row_cfg else None) or "ALL"
                if acc_id == "global":
                    # فیلتر اکانت‌ها
                    if atag not in ("ALL", ""):
                        if atag == "NOTAG":
                            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                                     "AND (tag='' OR tag IS NULL)", (ADMIN_ID,))
                        else:
                            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' AND tag=%s",
                                     (ADMIN_ID, atag))
                    else:
                        accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                    idx = (row_cfg[0][0] if row_cfg else 0) % len(bnrs)
                    msg_text = bnrs[idx][0]
                    for (aid,) in accs:
                        asyncio.create_task(rw.run_once(aid, msg_text, group_tag_filter=gtag))
                    u("INSERT INTO reply_rand (account_id,admin_id,last_index) VALUES('global',%s,%s) "
                      "ON DUPLICATE KEY UPDATE last_index=%s", (ADMIN_ID, idx+1, idx+1))
                    await cb.answer(f"🚀 برای {len(accs)} اکانت شروع شد", show_alert=True)
                else:
                    idx = (row_cfg[0][0] if row_cfg else 0) % len(bnrs)
                    msg_text = bnrs[idx][0]
                    u("INSERT INTO reply_rand (account_id,admin_id,last_index) VALUES(%s,%s,%s) "
                      "ON DUPLICATE KEY UPDATE last_index=%s", (acc_id, ADMIN_ID, idx+1, idx+1))
                    await cb.answer("🚀 شروع شد")
                    asyncio.create_task(rw.run_once(acc_id, msg_text, group_tag_filter=gtag))

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
                if new:
                    set_stop(False); rcw.STOP_FLAG = False
                await cb.answer(f"ری‌اکت {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM react_rand WHERE account_id=%s", (acc_id,))
                active = row2[0][0] if row2 else 0
                gtag = row2[0][1] if row2 else "ALL"
                atag = row2[0][2] if row2 else "ALL"
                back = "menu_global" if acc_id == "global" else None
                await cb.message.edit_reply_markup(react_rand_kb(acc_id, active, back_to=back, group_tag=gtag, acc_tag=atag))

            elif d.startswith("rc_run_"):
                acc_id = d[7:]
                set_stop(False); rcw.STOP_FLAG = False
                row_cfg = q("SELECT group_tag_filter, acc_tag_filter FROM react_rand WHERE account_id=%s", (acc_id,))
                gtag = (row_cfg[0][0] if row_cfg else None) or "ALL"
                atag = (row_cfg[0][1] if row_cfg else None) or "ALL"
                if acc_id == "global":
                    if atag not in ("ALL", ""):
                        if atag == "NOTAG":
                            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                                     "AND (tag='' OR tag IS NULL)", (ADMIN_ID,))
                        else:
                            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' AND tag=%s",
                                     (ADMIN_ID, atag))
                    else:
                        accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                    for (aid,) in accs:
                        asyncio.create_task(rcw.run_once(aid, group_tag_filter=gtag))
                    await cb.answer(f"🚀 برای {len(accs)} اکانت شروع شد", show_alert=True)
                else:
                    await cb.answer("🚀 شروع شد")
                    asyncio.create_task(rcw.run_once(acc_id, group_tag_filter=gtag))

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
                msg_text = get_step_data(ADMIN_ID)
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                if not tag_list:
                    # هیچ برچسبی تعریف نشده - مستقیم با همه شروع کن
                    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                    set_stop(False)
                    await cb.message.edit_text(f"⏳ ارسال به {len(accs)} اکانت شروع شد...")
                    for (aid,) in accs:
                        t = asyncio.create_task(_send_to_groups_task(client, aid, msg_text,
                                                                       group_tag_filter="ALL"))
                        t.set_name("send_grp_task")
                    clear_step(ADMIN_ID)
                    return
                set_step(ADMIN_ID, "g_sgrp_atag", msg_text)
                await cb.message.edit_text(
                    "👤 ارسال با کدوم اکانت‌ها؟",
                    reply_markup=tag_select_kb(tag_list, "gsgrpatag")
                )

            # ── انتخاب برچسب اکانت برای ارسال همگانی ──
            elif d.startswith("gsgrpatag_tag_"):
                acc_tag = d[14:]
                msg_text = get_step_data(ADMIN_ID)
                # ذخیره acc_tag در step_data برای مرحله بعد
                set_step(ADMIN_ID, f"g_sgrp_gtag_{acc_tag}", msg_text)
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text(
                    "👥 ارسال به کدوم گروه‌ها؟",
                    reply_markup=tag_select_kb(tag_list, f"gsgrpgtag_{acc_tag}")
                )

            # ── انتخاب برچسب گروه برای ارسال همگانی ──
            elif d.startswith("gsgrpgtag_"):
                rest = d[10:]  # {acc_tag}_tag_{group_tag}
                acc_tag, _, group_tag_filter = rest.partition("_tag_")
                msg_text = get_step_data(ADMIN_ID)
                from handlers.text_handler import get_filtered_accounts
                accs = get_filtered_accounts(acc_tag)
                set_stop(False)
                await cb.message.edit_text(f"⏳ ارسال به {len(accs)} اکانت شروع شد...")
                for (aid,) in accs:
                    t = asyncio.create_task(_send_to_groups_task(client, aid, msg_text,
                                                                   group_tag_filter=group_tag_filter))
                    t.set_name("send_grp_task")
                clear_step(ADMIN_ID)

            elif d == "g_join":
                set_step(ADMIN_ID, "g_join"); await cb.message.edit_text("➕ لینک‌ها را هر کدام در یک خط:", reply_markup=back_kb("menu_global"))

            elif d == "g_join_split":
                raw = get_step_data(ADMIN_ID)
                lines = raw.splitlines()
                chosen_tag = ""
                if lines and lines[0].startswith("TAG:"):
                    chosen_tag = lines[0][4:]
                    links = [l for l in lines[1:] if l.strip()]
                else:
                    links = [l for l in lines if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if not accs:
                    await cb.answer("اکانتی وجود ندارد", show_alert=True); return
                per = max(1, len(links) // len(accs))
                set_stop(False)
                tag_lbl = f"«{chosen_tag}»" if chosen_tag else "بدون برچسب"
                await cb.message.edit_text(
                    f"🔀 {len(links)} لینک بین {len(accs)} اکانت تقسیم شد.\n🏷 برچسب: {tag_lbl}"
                )
                for i, (aid,) in enumerate(accs):
                    chunk = links[i*per:(i+1)*per]
                    if chunk:
                        row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                        mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                        from handlers.text_handler import _join_links
                        t = asyncio.create_task(_join_links(client, aid, chunk, mn, mx,
                                                             tag=chosen_tag))
                        t.set_name("join_task")
                clear_step(ADMIN_ID)

            elif d == "g_join_all":
                raw = get_step_data(ADMIN_ID)
                lines = raw.splitlines()
                chosen_tag = ""
                if lines and lines[0].startswith("TAG:"):
                    chosen_tag = lines[0][4:]
                    links = [l for l in lines[1:] if l.strip()]
                else:
                    links = [l for l in lines if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                set_stop(False)
                tag_lbl = f"«{chosen_tag}»" if chosen_tag else "بدون برچسب"
                await cb.message.edit_text(
                    f"📋 همه اکانت‌ها {len(links)} لینک — 🏷 {tag_lbl}"
                )
                for (aid,) in accs:
                    row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                    mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                    from handlers.text_handler import _join_links
                    t = asyncio.create_task(_join_links(client, aid, links, mn, mx,
                                                         tag=chosen_tag))
                    t.set_name("join_task")
                clear_step(ADMIN_ID)

            elif d == "g_fj":
                row = q("SELECT force_join_active FROM join_settings WHERE admin_id=%s LIMIT 1", (ADMIN_ID,))
                active = row[0][0] if row else 0
                await cb.message.edit_text(
                    f"🕵️ **عضویت اجبار (همگانی)**\n\n"
                    f"وضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            f"{'🔴 غیرفعال' if active else '🟢 فعال'} برای همه",
                            callback_data="g_fj_tog")],
                        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")]
                    ])
                )

            elif d == "g_sch_menu":
                await cb.message.edit_text(
                    "⏰ **ارسال زمان‌دار همگانی**\n\nنوع ارسال را انتخاب کنید:",
                    reply_markup=global_sch_menu_kb()
                )

            elif d.startswith("gsch_panel_"):
                target = d[11:]
                row = q("SELECT is_active, interval_minutes, group_tag_filter, acc_tag_filter, "
                        "max_rounds, current_round FROM global_scheduler "
                        "WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                active = row[0][0] if row else 0
                interval = row[0][1] if row else 60
                gtag = (row[0][2] if row else None) or "ALL"
                atag = (row[0][3] if row else None) or "ALL"
                max_rounds = row[0][4] if row else 0
                current_round = row[0][5] if row else 0
                title = "📢 گروه‌ها" if target == "groups" else "💬 پیوی‌ها"
                bnrs = q("SELECT slot, text, file_id FROM global_banners "
                         "WHERE admin_id=%s AND target=%s ORDER BY slot", (ADMIN_ID, target))
                txt = f"⏰ **ارسال زمان‌دار به {title}**\n\n"
                txt += f"فاصله: هر {interval} دقیقه\nوضعیت: {'✅ فعال' if active else '❌ غیرفعال'}\n"
                txt += f"🏷 گروه: {gtag} | 👤 اکانت: {atag}\n"
                if max_rounds == 0:
                    txt += "🔄 دور: نامحدود\n\n"
                else:
                    txt += f"🔄 دور: {current_round}/{max_rounds}\n\n"
                for slot in (1, 2, 3, 4):
                    b = next((x for x in bnrs if x[0] == slot), None)
                    if b:
                        short = (b[1] or "")[:30]
                        txt += f"💬 پیام {slot}: [{short}{'...' if b[1] and len(b[1])>30 else ''}] {'📁' if b[2] else ''}\n"
                    else:
                        txt += f"💬 پیام {slot}: تنظیم نشده\n"
                txt += "\nهر دوره یکی از این پیام‌ها به‌ترتیب شماره ارسال می‌شود."
                await cb.message.edit_text(txt, reply_markup=global_sch_panel_kb(
                    target, active, gtag=gtag, atag=atag,
                    max_rounds=max_rounds, current_round=current_round))

            elif d.startswith("gsch_rounds_"):
                target = d[12:]
                set_step(ADMIN_ID, f"gsch_rounds_{target}")
                await cb.message.edit_text(
                    "🔄 تعداد دور را وارد کنید:\n\n"
                    "`0` = نامحدود\n`1` = یک دور (۴ پیام)\n`2` = دو دور (۸ پیام)\n...",
                    reply_markup=back_kb(f"gsch_panel_{target}")
                )

            elif d.startswith("gsch_gtag_set_"):
                rest = d[14:]
                target, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO global_scheduler (admin_id,target,group_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE group_tag_filter=%s", (ADMIN_ID, target, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر گروه: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM global_scheduler "
                        "WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                await cb.message.edit_reply_markup(global_sch_panel_kb(target, active, gtag=gtag, atag=atag))

            elif d.startswith("gsch_gtag_"):
                target = d[10:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text("🏷 فیلتر گروه‌ها برای زمان‌بند:",
                    reply_markup=tag_select_kb(tag_list, f"gsch_gtag_set_{target}"))

            elif d.startswith("gsch_atag_set_"):
                rest = d[14:]
                target, _, tag_name = rest.partition("_tag_")
                u("INSERT INTO global_scheduler (admin_id,target,acc_tag_filter) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE acc_tag_filter=%s", (ADMIN_ID, target, tag_name, tag_name))
                await cb.answer(f"✅ فیلتر اکانت: {tag_name}")
                row = q("SELECT is_active,group_tag_filter,acc_tag_filter FROM global_scheduler "
                        "WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                active = row[0][0] if row else 0
                gtag = row[0][1] if row else "ALL"
                atag = row[0][2] if row else "ALL"
                await cb.message.edit_reply_markup(global_sch_panel_kb(target, active, gtag=gtag, atag=atag))

            elif d.startswith("gsch_atag_"):
                target = d[10:]
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_text("👤 فیلتر اکانت‌ها برای زمان‌بند:",
                    reply_markup=tag_select_kb(tag_list, f"gsch_atag_set_{target}"))

            elif d.startswith("gsch_time_"):
                target = d[10:]
                set_step(ADMIN_ID, f"gsch_int_{target}")
                await cb.message.edit_text(
                    "⏱ فاصله ارسال (دقیقه) را وارد کنید:\nمثال: `60`",
                    reply_markup=back_kb(f"gsch_panel_{target}")
                )

            elif d.startswith("gsch_tog_"):
                target = d[9:]
                row = q("SELECT is_active FROM global_scheduler WHERE admin_id=%s AND target=%s",
                        (ADMIN_ID, target))
                new = 0 if (row[0][0] if row else 0) else 1
                if new:
                    # روشن کردن — reset دور
                    u("INSERT INTO global_scheduler (admin_id,target,is_active,current_round) "
                      "VALUES(%s,%s,%s,0) ON DUPLICATE KEY UPDATE is_active=%s, current_round=0",
                      (ADMIN_ID, target, new, new))
                    set_stop(False)
                else:
                    u("INSERT INTO global_scheduler (admin_id,target,is_active) VALUES(%s,%s,%s) "
                      "ON DUPLICATE KEY UPDATE is_active=%s", (ADMIN_ID, target, new, new))
                await cb.answer(f"ارسال زمان‌دار {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active,group_tag_filter,acc_tag_filter,max_rounds,current_round "
                         "FROM global_scheduler WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                active = row2[0][0] if row2 else 0
                gtag = (row2[0][1] if row2 else None) or "ALL"
                atag = (row2[0][2] if row2 else None) or "ALL"
                max_r = row2[0][3] if row2 else 0
                cur_r = row2[0][4] if row2 else 0
                await cb.message.edit_reply_markup(global_sch_panel_kb(
                    target, active, gtag=gtag, atag=atag, max_rounds=max_r, current_round=cur_r))

            elif d.startswith("gsch_b"):
                # gsch_b1_groups / gsch_b2_pvs / ...
                slot = int(d[6])
                target = d[8:]
                await cb.message.edit_text(
                    f"✏️ مدیریت پیام {slot}",
                    reply_markup=global_banner_slot_kb(target, slot)
                )

            elif d.startswith("gbn_add_"):
                _, _, target, slot = d.split("_", 3)
                slot = int(slot)
                set_step(ADMIN_ID, f"gbn_text_{target}_{slot}")
                await cb.message.edit_text("📝 متن پیام را وارد کنید:")

            elif d.startswith("gbn_del_"):
                _, _, target, slot = d.split("_", 3)
                slot = int(slot)
                u("DELETE FROM global_banners WHERE admin_id=%s AND target=%s AND slot=%s",
                  (ADMIN_ID, target, slot))
                await cb.answer(f"✅ پیام {slot} حذف شد")
                await cb.message.edit_reply_markup(global_banner_slot_kb(target, slot))

            elif d.startswith("gbn_delall_"):
                target = d[11:]
                u("DELETE FROM global_banners WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                await cb.answer("✅ همه پیام‌ها حذف شدند")

            elif d.startswith("gbn_back_"):
                target = d[9:]
                row = q("SELECT is_active, interval_minutes, group_tag_filter, acc_tag_filter, "
                        "max_rounds, current_round FROM global_scheduler "
                        "WHERE admin_id=%s AND target=%s", (ADMIN_ID, target))
                active = row[0][0] if row else 0
                interval = row[0][1] if row else 60
                gtag = (row[0][2] if row else None) or "ALL"
                atag = (row[0][3] if row else None) or "ALL"
                max_r = row[0][4] if row else 0
                cur_r = row[0][5] if row else 0
                title = "📢 گروه‌ها" if target == "groups" else "💬 پیوی‌ها"
                bnrs = q("SELECT slot, text, file_id FROM global_banners "
                         "WHERE admin_id=%s AND target=%s ORDER BY slot", (ADMIN_ID, target))
                txt = f"⏰ **ارسال زمان‌دار به {title}**\n\n"
                txt += f"فاصله: هر {interval} دقیقه\nوضعیت: {'✅ فعال' if active else '❌ غیرفعال'}\n\n"
                for slot in (1, 2, 3, 4):
                    b = next((x for x in bnrs if x[0] == slot), None)
                    if b:
                        short = (b[1] or "")[:30]
                        txt += f"💬 پیام {slot}: [{short}{'...' if b[1] and len(b[1])>30 else ''}] {'📁' if b[2] else ''}\n"
                    else:
                        txt += f"💬 پیام {slot}: تنظیم نشده\n"
                txt += "\nهر دوره (هر X دقیقه) یکی از این پیام‌ها به‌ترتیب شماره ارسال می‌شود."
                await cb.message.edit_text(txt, reply_markup=global_sch_panel_kb(
                    target, active, gtag=gtag, atag=atag, max_rounds=max_r, current_round=cur_r))

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

            # ══ مدیریت برچسب‌ها ══
            elif d == "tags_menu":
                await cb.message.edit_text(
                    "🏷 **مدیریت برچسب‌ها**\n\nبرچسب‌ها برای دسته‌بندی گروه‌ها و اکانت‌ها استفاده می‌شوند.",
                    reply_markup=tags_menu_kb()
                )

            elif d == "tags_groups":
                tags = q("SELECT DISTINCT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                txt = "👥 **برچسب گروه‌ها**\n\n"
                if tag_list:
                    txt += "برچسب‌های موجود:\n" + "\n".join(f"• {t}" for t in tag_list)
                else:
                    txt += "هیچ برچسبی ساخته نشده."
                await cb.message.edit_text(txt, reply_markup=tags_list_kb(tag_list, "groups"))

            elif d == "tags_accounts":
                accs = q("SELECT id,name,phone,tag FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                txt = "👤 **برچسب اکانت‌ها**\n\n"
                for a in accs:
                    tag_str = f"🏷 {a[3]}" if a[3] else "بدون برچسب"
                    txt += f"👤 {a[1]} | {a[2]} — {tag_str}\n"
                await cb.message.edit_text(txt, reply_markup=account_tag_kb(accs))

            elif d.startswith("tag_new_"):
                context = d[8:]
                set_step(ADMIN_ID, f"tag_new_{context}")
                await cb.message.edit_text(
                    "📝 نام برچسب جدید را وارد کنید:\nمثال: `تبلیغاتی`",
                    reply_markup=back_kb("tags_menu")
                )

            elif d.startswith("tag_del_"):
                _, _, context, tag_name = d.split("_", 3)
                u("DELETE FROM tags WHERE admin_id=%s AND name=%s", (ADMIN_ID, tag_name))
                # حذف از گروه‌ها هم
                u("UPDATE group_tags SET tag_name='' WHERE admin_id=%s AND tag_name=%s",
                  (ADMIN_ID, tag_name))
                await cb.answer(f"✅ برچسب «{tag_name}» حذف شد", show_alert=True)
                tags = q("SELECT DISTINCT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                await cb.message.edit_reply_markup(tags_list_kb(tag_list, context))

            elif d.startswith("acctag_sel_"):
                acc_id = d[11:]
                acc = q("SELECT name,phone,tag FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                tag_list = [t[0] for t in tags]
                txt = f"👤 **{acc[0][0]}** | {acc[0][1]}\n"
                txt += f"برچسب فعلی: {acc[0][2] or 'بدون برچسب'}\n\nبرچسب جدید را انتخاب کنید:"
                rows = [[InlineKeyboardButton(f"🏷 {t}", callback_data=f"acctag_set_{acc_id}_{t}")]
                        for t in tag_list]
                rows.append([InlineKeyboardButton("🔘 بدون برچسب", callback_data=f"acctag_set_{acc_id}_NOTAG")])
                rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tags_accounts")])
                await cb.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(rows))

            elif d.startswith("acctag_set_"):
                _, _, acc_id, tag_name = d.split("_", 3)
                new_tag = "" if tag_name == "NOTAG" else tag_name
                u("UPDATE accounts SET tag=%s WHERE id=%s AND admin_id=%s",
                  (new_tag, acc_id, ADMIN_ID))
                lbl = f"«{new_tag}»" if new_tag else "بدون برچسب"
                await cb.answer(f"✅ برچسب اکانت به {lbl} تغییر کرد", show_alert=True)
                accs = q("SELECT id,name,phone,tag FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                txt = "👤 **برچسب اکانت‌ها**\n\n"
                for a in accs:
                    tag_str = f"🏷 {a[3]}" if a[3] else "بدون برچسب"
                    txt += f"👤 {a[1]} | {a[2]} — {tag_str}\n"
                await cb.message.edit_text(txt, reply_markup=account_tag_kb(accs))

            elif d == "g_sec":
                row = q("SELECT is_active FROM global_secretary_settings WHERE admin_id=%s", (ADMIN_ID,))
                active = bool(row[0][0]) if row else False
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
                row = q("SELECT is_active FROM global_secretary_settings WHERE admin_id=%s", (ADMIN_ID,))
                new = 0 if (row and row[0][0]) else 1
                u("INSERT INTO global_secretary_settings (admin_id,is_active) VALUES(%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (ADMIN_ID, new, new))
                await cb.answer(f"منشی همگانی {'فعال' if new else 'غیرفعال'} شد", show_alert=True)
                await cb.message.edit_reply_markup(global_sec_kb(bool(new)))

            elif d == "g_rr":
                row = q("SELECT is_active,interval_minutes,group_tag_filter,acc_tag_filter FROM reply_rand WHERE account_id='global' AND admin_id=%s", (ADMIN_ID,))
                active = row[0][0] if row else 0
                interval = row[0][1] if row else 30
                gtag = (row[0][2] if row else None) or "ALL"
                atag = (row[0][3] if row else None) or "ALL"
                await cb.message.edit_text(
                    f"↩️ **ریپلای رندم همگانی**\n\n"
                    f"این تنظیم برای **همه اکانت‌ها** یکسان اعمال می‌شود؛ "
                    f"هر اکانت مستقل با همین متن و زمان ریپلای می‌زند.\n\n"
                    f"فاصله: {interval} دقیقه\nوضعیت: {'✅' if active else '❌'}",
                    reply_markup=reply_rand_kb("global", active, back_to="menu_global", group_tag=gtag, acc_tag=atag)
                )

            elif d == "g_rc":
                row = q("SELECT is_active,interval_minutes,group_tag_filter,acc_tag_filter FROM react_rand WHERE account_id='global' AND admin_id=%s", (ADMIN_ID,))
                active = row[0][0] if row else 0
                interval = row[0][1] if row else 30
                gtag = (row[0][2] if row else None) or "ALL"
                atag = (row[0][3] if row else None) or "ALL"
                await cb.message.edit_text(
                    f"😀 **ری‌اکت رندم همگانی**\n\n"
                    f"این تنظیم برای **همه اکانت‌ها** یکسان اعمال می‌شود؛ "
                    f"هر اکانت مستقل ری‌اکت می‌زند.\n\n"
                    f"فاصله: {interval} دقیقه\nوضعیت: {'✅' if active else '❌'}",
                    reply_markup=react_rand_kb("global", active, back_to="menu_global", group_tag=gtag, acc_tag=atag)
                )

            # ══ جوین از پیوی‌ها ══
            elif d == "g_pvjoin":
                cnt_row = q("SELECT COUNT(*) FROM pv_links WHERE admin_id=%s", (ADMIN_ID,))
                link_count = cnt_row[0][0] if cnt_row else 0
                st_row = q("SELECT last_scan FROM pv_join_settings WHERE admin_id=%s", (ADMIN_ID,))
                last_scan = st_row[0][0] if st_row else None
                await cb.message.edit_text(
                    "📥 **جوین از پیوی‌ها**\n\n"
                    "اکانت‌ها پیوی‌هایشان را اسکن می‌کنند و لینک‌های تلگرامی استخراج می‌شوند.",
                    reply_markup=pv_join_kb(link_count, last_scan)
                )

            elif d == "g_pvjoin_scan":
                await cb.message.edit_text("🔍 در حال اسکن پیوی‌ها...\nلطفاً صبر کنید.")
                asyncio.create_task(_scan_pvs_for_links(cb._client))

            elif d == "g_pvjoin_show":
                rows = q("SELECT link FROM pv_links WHERE admin_id=%s ORDER BY found_at DESC", (ADMIN_ID,))
                if not rows:
                    await cb.answer("❌ لینکی یافت نشده. ابتدا اسکن کنید.", show_alert=True)
                else:
                    out = "\n".join(r[0] for r in rows)
                    chunks = [out[i:i+4000] for i in range(0, len(out), 4000)]
                    for chunk in chunks:
                        await cb._client.send_message(ADMIN_ID, chunk)
                    await cb.answer(f"✅ {len(rows)} لینک ارسال شد", show_alert=True)

            elif d == "g_pvjoin_join":
                rows = q("SELECT link FROM pv_links WHERE admin_id=%s ORDER BY found_at DESC", (ADMIN_ID,))
                if not rows:
                    await cb.answer("❌ لینکی یافت نشده. ابتدا اسکن کنید.", show_alert=True)
                else:
                    links = [r[0] for r in rows]
                    set_step(ADMIN_ID, "g_join_tag", "\n".join(links))
                    tags = q("SELECT name FROM tags WHERE admin_id=%s ORDER BY name", (ADMIN_ID,))
                    tag_list = [t[0] for t in tags]
                    await cb.message.edit_text(
                        f"✅ **{len(links)} لینک از پیوی‌ها آماده جوین**\n\nبرچسب گروه‌ها را انتخاب کنید:",
                        reply_markup=tag_select_kb(tag_list, "gjointag", show_all=False)
                    )

            elif d == "g_pvjoin_clear":
                u("DELETE FROM pv_links WHERE admin_id=%s", (ADMIN_ID,))
                await cb.answer("✅ لیست لینک‌ها پاک شد", show_alert=True)
                await cb.message.edit_text(
                    "📥 **جوین از پیوی‌ها**\n\n"
                    "اکانت‌ها پیوی‌هایشان را اسکن می‌کنند و لینک‌های تلگرامی استخراج می‌شوند.",
                    reply_markup=pv_join_kb(0, None)
                )

            elif d == "g_pvjoin_settings":
                st_row = q(
                    "SELECT auto_scan, scan_interval_hours, daily_limit "
                    "FROM pv_join_settings WHERE admin_id=%s",
                    (ADMIN_ID,)
                )
                auto_scan = st_row[0][0] if st_row else 0
                interval_hours = st_row[0][1] if st_row else 6
                daily_limit = st_row[0][2] if st_row else 20
                await cb.message.edit_text(
                    "⚙️ **تنظیمات اسکن خودکار پیوی‌ها**",
                    reply_markup=pv_join_settings_kb(auto_scan, interval_hours, daily_limit)
                )

            elif d == "g_pvjoin_tog_auto":
                st_row = q("SELECT auto_scan FROM pv_join_settings WHERE admin_id=%s", (ADMIN_ID,))
                new = 0 if (st_row and st_row[0][0]) else 1
                u(
                    "INSERT INTO pv_join_settings (admin_id, auto_scan) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE auto_scan=%s",
                    (ADMIN_ID, new, new)
                )
                await cb.answer(f"اسکن خودکار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)
                st_row2 = q(
                    "SELECT auto_scan, scan_interval_hours, daily_limit "
                    "FROM pv_join_settings WHERE admin_id=%s",
                    (ADMIN_ID,)
                )
                auto_scan = st_row2[0][0] if st_row2 else new
                interval_hours = st_row2[0][1] if st_row2 else 6
                daily_limit = st_row2[0][2] if st_row2 else 20
                await cb.message.edit_reply_markup(pv_join_settings_kb(auto_scan, interval_hours, daily_limit))

            elif d == "g_pvjoin_set_interval":
                set_step(ADMIN_ID, "g_pvjoin_interval")
                await cb.message.edit_text(
                    "⏰ **فاصله اسکن خودکار**\n\nعدد ساعت را وارد کنید (۱ تا ۲۴):",
                    reply_markup=back_kb("g_pvjoin_settings")
                )

            elif d == "g_pvjoin_set_limit":
                set_step(ADMIN_ID, "g_pvjoin_limit")
                await cb.message.edit_text(
                    "📊 **سقف روزانه جوین**\n\nتعداد لینک در روز را وارد کنید (۱ تا ۱۰۰):",
                    reply_markup=back_kb("g_pvjoin_settings")
                )


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
    from pyrogram.errors import FloodWait, UserIsBlocked, PeerIdInvalid, UserDeactivated as UD

    uc = await get_user_client(acc_id)
    if not uc:
        print(f"[SendPV] اکانت {acc_id} session نداره")
        return

    me_info = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
    display = me_info[0][0] if me_info else acc_id

    ok = fail = blocked = 0
    error_samples = []

    try:
        await uc.start()
    except Exception as e:
        print(f"[SendPV] خطا در اتصال {acc_id}: {e}")
        await bot_client.send_message(ADMIN_ID, f"❌ اتصال اکانت {display} ناموفق: {e}")
        return

    try:
        dialogs = []
        async for dlg in uc.get_dialogs():
            if dlg.chat.type == en.ChatType.PRIVATE:
                dialogs.append(dlg)
    except Exception as e:
        print(f"[SendPV] خطا در گرفتن لیست پیوی‌ها {acc_id}: {e}")
        await bot_client.send_message(ADMIN_ID, f"❌ خطا در خواندن پیوی‌های {display}: {e}")
        try: await uc.stop()
        except Exception: pass
        return

    for dlg in dialogs:
        if is_stopped():
            break
        try:
            await uc.send_message(dlg.chat.id, text)
            ok += 1
            await asyncio.sleep(2)
        except FloodWait as e:
            # صبر می‌کنیم و همین کاربر رو دوباره امتحان می‌کنیم، بقیه رو ول نمی‌کنیم
            wait_s = min(e.value, 120)
            await asyncio.sleep(wait_s)
            try:
                await uc.send_message(dlg.chat.id, text); ok += 1
            except Exception:
                fail += 1
        except UserIsBlocked:
            blocked += 1
        except (PeerIdInvalid, UD):
            fail += 1
        except Exception as e:
            fail += 1
            if len(error_samples) < 3:
                error_samples.append(str(e)[:80])
            print(f"[SendPV] خطا در ارسال به {dlg.chat.id} ({acc_id}): {e}")

    try:
        await uc.stop()
    except Exception:
        pass

    report = f"✅ پیوی‌ها\n👤 {display}\n✔️ موفق: {ok}\n🚫 بلاک شده: {blocked}\n❌ خطا: {fail}"
    if error_samples:
        report += "\n\n❗️ نمونه خطاها:\n" + "\n".join(error_samples)
    await bot_client.send_message(ADMIN_ID, report)


async def _send_to_groups_task(bot_client, acc_id, text, group_tag_filter="ALL"):
    from handlers.text_handler import send_to_groups_smart
    result = await send_to_groups_smart(bot_client, acc_id, text,
                                         group_tag_filter=group_tag_filter)
    tag_lbl = f" [🏷 {group_tag_filter}]" if group_tag_filter not in ("ALL", "") else ""
    report = (
        f"✅ ارسال به گروه‌ها تمام شد{tag_lbl}\n"
        f"👤 {result.get('display', acc_id)}\n"
        f"✔️ موفق: {result['ok']}\n"
        f"❌ ناموفق: {result['fail']}\n"
        f"🚫 محدود شده: {result['limited']}\n"
        f"🔗 عضویت اجبار انجام شد: {result['force_joined']}\n"
        f"🚪 از گروه‌های محدود خارج شد: {result['left']}"
    )
    await bot_client.send_message(ADMIN_ID, report)


async def _scan_pvs_for_links(bot_client):
    """اسکن پیوی‌های همه اکانت‌ها و استخراج لینک‌های تلگرامی — تابع مشترک"""
    import re
    from pyrogram import enums as en
    from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired
    from handlers.text_handler import _link_hash

    LINK_RE = re.compile(r'https?://t\.me/[^\s\]\)"\']+')

    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
    total_new = 0

    for (acc_id,) in accs:
        uc = await get_user_client(acc_id)
        if not uc:
            continue
        try:
            await uc.start()
            async for dlg in uc.get_dialogs():
                if dlg.chat.type != en.ChatType.PRIVATE:
                    continue
                try:
                    async for msg in uc.get_chat_history(dlg.chat.id, limit=50):
                        txt = msg.text or msg.caption or ""
                        for raw_link in LINK_RE.findall(txt):
                            link = raw_link.rstrip(".,;:!?)")
                            lh = _link_hash(link)
                            # چک نبودن در used_links
                            used = q(
                                "SELECT 1 FROM used_links WHERE admin_id=%s AND link_hash=%s",
                                (ADMIN_ID, lh)
                            )
                            if used:
                                continue
                            try:
                                u(
                                    "INSERT IGNORE INTO pv_links (admin_id, link, link_hash) "
                                    "VALUES (%s, %s, %s)",
                                    (ADMIN_ID, link[:500], lh)
                                )
                                # اگه واقعاً insert شد (نه ignore) شمارش می‌کنیم
                            except Exception as e:
                                print(f"[PVScan] خطا در ذخیره لینک: {e}")
                except Exception as e:
                    print(f"[PVScan] خطا در خواندن پیام‌های {dlg.chat.id}: {e}")
            await uc.stop()
        except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
            u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
            try: await uc.stop()
            except Exception: pass
            continue
        except Exception as e:
            print(f"[PVScan] خطا در اکانت {acc_id}: {e}")
            try: await uc.stop()
            except Exception: pass
            continue
        await asyncio.sleep(2)

    # شمارش لینک‌های جدید بعد از اسکن (ساده‌ترین روش)
    cnt_row = q("SELECT COUNT(*) FROM pv_links WHERE admin_id=%s", (ADMIN_ID,))
    total_links = cnt_row[0][0] if cnt_row else 0

    from datetime import datetime
    now = datetime.utcnow()
    u(
        "INSERT INTO pv_join_settings (admin_id, last_scan) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE last_scan=%s",
        (ADMIN_ID, now, now)
    )

    if bot_client:
        try:
            await bot_client.send_message(
                ADMIN_ID,
                f"✅ اسکن تمام شد\n"
                f"📱 اکانت‌ها: {len(accs)}\n"
                f"🔗 لینک‌های موجود در لیست: {total_links}"
            )
        except Exception as e:
            print(f"[PVScan] خطا در ارسال گزارش: {e}")
