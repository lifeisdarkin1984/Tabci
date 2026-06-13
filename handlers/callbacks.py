import asyncio, time
from pyrogram import filters
from pyrogram.types import CallbackQuery
from database import q, u
from utils import (ADMIN_ID, get_step, get_step_data, set_step,
                   clear_step, get_user_client, report_flood)
from keyboards import *

def register(app):

    @app.on_callback_query()
    async def on_cb(client, cb: CallbackQuery):
        if cb.from_user.id != ADMIN_ID:
            await cb.answer("⛔️ دسترسی ندارید")
            return
        d = cb.data

        try:
            # ══ منوی اصلی ══
            if d == "back_main":
                await cb.message.edit_text("یک گزینه را انتخاب کنید:", reply_markup=main_menu_kb())

            elif d == "menu_tabchi":
                accs = q("SELECT id,phone,name FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if not accs:
                    await cb.answer("هیچ اکانتی ثبت نشده. /add_account", show_alert=True)
                    return
                await cb.message.edit_text("📌 **لیست تبچی‌های شما:**",
                                            reply_markup=tabchi_list_kb(accs))

            elif d == "menu_global":
                await cb.message.edit_text("🌐 **مدیریت همگانی**", reply_markup=global_kb())

            # ══ منشی خودکار همگانی ══
            elif d == "g_sec":
                await cb.message.edit_text(
                    "👽 **پنل منشی خودکار همگانی**\n\n"
                    "پیام‌های خوشامدگویی را تنظیم کنید، سپس «فعال‌سازی برای همه اکانت‌ها»\n"
                    "را بزنید تا همین پیام‌ها روی منشی خودکار **تمام اکانت‌ها** اعمال شده\n"
                    "و منشی خودکار برای همه آن‌ها فعال شود.\n\n"
                    "✅ هر ۳۰ دقیقه چت‌ها بررسی و پاسخ داده می‌شه.",
                    reply_markup=global_secretary_kb()
                )

            elif d == "g_sec_apply":
                banners = q(
                    "SELECT slot,text,file_id,file_type FROM banners "
                    "WHERE account_id='global' AND context='secretary' ORDER BY slot"
                )
                if not banners:
                    await cb.answer("⚠️ ابتدا حداقل یک پیام تنظیم کنید", show_alert=True)
                    return
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                for (aid,) in accs:
                    u("DELETE FROM banners WHERE account_id=%s AND context='secretary'", (aid,))
                    for (slot, txt, fid, ftype) in banners:
                        u("INSERT INTO banners (account_id,admin_id,slot,text,file_id,file_type,context) "
                          "VALUES(%s,%s,%s,%s,%s,%s,'secretary')",
                          (aid, ADMIN_ID, slot, txt, fid, ftype))
                    u("INSERT INTO secretary (account_id,admin_id,is_active) VALUES(%s,%s,1) "
                      "ON DUPLICATE KEY UPDATE is_active=1", (aid, ADMIN_ID))
                await cb.answer(f"✅ منشی خودکار برای {len(accs)} اکانت فعال شد", show_alert=True)

            elif d == "g_sec_disable":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                for (aid,) in accs:
                    u("UPDATE secretary SET is_active=0 WHERE account_id=%s", (aid,))
                await cb.answer(f"✅ منشی خودکار برای {len(accs)} اکانت غیرفعال شد", show_alert=True)

            # ══ حذف اکانت - تایید (باید قبل از acc_sel_ باشه) ══
            elif d.startswith("acc_del_yes_"):
                acc_id = d[12:]
                u("DELETE FROM accounts WHERE id=%s AND admin_id=%s", (acc_id, ADMIN_ID))
                u("DELETE FROM secretary WHERE account_id=%s", (acc_id,))
                u("DELETE FROM scheduler WHERE account_id=%s", (acc_id,))
                u("DELETE FROM banners WHERE account_id=%s", (acc_id,))
                u("DELETE FROM join_settings WHERE account_id=%s", (acc_id,))
                accs = q("SELECT id,phone,name FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if accs:
                    await cb.message.edit_text("✅ اکانت حذف شد.\n\n📌 لیست تبچی‌ها:",
                                                reply_markup=tabchi_list_kb(accs))
                else:
                    await cb.message.edit_text("✅ اکانت حذف شد.\n\nهیچ اکانتی باقی نمانده.\nبرای افزودن: /add_account",
                                                reply_markup=back_kb("back_main"))

            # ══ حذف اکانت - سوال (باید قبل از acc_sel_ باشه) ══
            elif d.startswith("acc_del_"):
                acc_id = d[8:]
                acc = q("SELECT name,phone FROM accounts WHERE id=%s", (acc_id,))
                name = f"{acc[0][0]} | {acc[0][1]}" if acc else acc_id
                await cb.message.edit_text(
                    f"❗️ آیا مطمئن هستید که می‌خواهید اکانت\n👤 {name}\nرا حذف کنید؟",
                    reply_markup=confirm_kb(f"acc_del_yes_{acc_id}", "menu_tabchi")
                )

            # ══ انتخاب اکانت ══
            elif d.startswith("acc_sel_"):
                acc_id = d[8:]
                acc = q("SELECT id,phone,name,username FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                a = acc[0]
                await cb.message.edit_text(
                    f"👤 **{a[2]}** | `{a[1]}`\n🔗 یوزرنیم: @{a[3] or 'ندارد'}",
                    reply_markup=acc_info_kb(acc_id)
                )

            # ══ مدیریت تبچی ══
            elif d.startswith("acc_manage_"):
                acc_id = d[11:]
                acc = q("SELECT name,phone FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                await cb.message.edit_text(
                    f"⚙️ پنل مدیریت **{acc[0][0]}** | `{acc[0][1]}`",
                    reply_markup=manage_kb(acc_id)
                )

            # ══ کد ورود ══
            elif d.startswith("acc_code_"):
                acc_id = d[9:]
                acc = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
                if not acc:
                    await cb.answer("اکانت یافت نشد", show_alert=True); return
                await cb.answer(
                    f"📱 کد ورود به این شماره در تلگرام ارسال می‌شود:\n{acc[0][0]}",
                    show_alert=True
                )

            # ══ وضعیت اکانت ══
            elif d.startswith("acc_status_"):
                acc_id = d[11:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ سشن پیدا نشد", show_alert=True); return
                try:
                    await uc.start()
                    me = await uc.get_me()
                    await uc.stop()
                    await cb.answer(f"✅ اکانت فعال\n👤 {me.first_name}", show_alert=True)
                except Exception as e:
                    await cb.answer(f"❌ غیرفعال: {str(e)[:100]}", show_alert=True)

            # ══ بروزرسانی همه ══
            elif d == "acc_refresh":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                ok = 0
                for (aid,) in accs:
                    try:
                        uc = await get_user_client(aid)
                        await uc.start()
                        me = await uc.get_me()
                        await uc.stop()
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
                    await uc.start()
                    me = await uc.get_me()
                    grps = chns = pvs = 0
                    from pyrogram import enums
                    async for dialog in uc.get_dialogs():
                        if dialog.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                            grps += 1
                        elif dialog.chat.type == enums.ChatType.CHANNEL:
                            chns += 1
                        elif dialog.chat.type == enums.ChatType.PRIVATE:
                            pvs += 1
                    await uc.stop()
                    await cb.message.edit_text(
                        f"⚙️ به پنل مدیریت `{me.id}` خوش آمدید\n\n"
                        f"👤 نام: {me.first_name or ''} {me.last_name or ''}\n"
                        f"📊 وضعیت: فعال ✅\n"
                        f"💬 کانال: {chns}\n"
                        f"🗣 گروه‌ها: {grps}\n"
                        f"🪡 پیوی‌ها: {pvs}\n"
                        f"🔗 یوزرنیم: @{me.username or 'ندارد'}",
                        reply_markup=back_kb(f"acc_manage_{acc_id}")
                    )
                except Exception as e:
                    await cb.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)

            # ══ منشی خودکار ══
            elif d.startswith("m_sec_"):
                acc_id = d[6:]
                row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                await cb.message.edit_text(
                    "👽 **پنل منشی خودکار**\n\n"
                    "با منشی خودکار می‌تونید پیام خوشامدگویی به کاربرایی که\n"
                    "برای اولین بار پیام میدن به‌صورت خودکار بفرستید.\n\n"
                    "✅ هر ۳۰ دقیقه چت‌ها بررسی و پاسخ داده می‌شه.\n\n"
                    f"وضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=secretary_kb(acc_id, active)
                )

            elif d.startswith("sec_tog_"):
                acc_id = d[8:]
                row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                u("INSERT INTO secretary (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"منشی {'فعال' if new else 'غیرفعال'} شد")
                row2 = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                await cb.message.edit_reply_markup(secretary_kb(acc_id, row2[0][0]))

            elif d.startswith("sec_b"):
                slot = int(d[5])
                acc_id = d[7:]
                bnrs = q("SELECT slot,text,file_id FROM banners "
                         "WHERE account_id=%s AND context='secretary' ORDER BY slot", (acc_id,))
                txt = "✏️ **مدیریت بنرها**\n\n"
                for b in bnrs:
                    short = (b[1] or "")[:40]
                    has_f = "✅" if b[2] else "❌"
                    txt += f"═-═-═-═ {b[0]} ═-═-═-═\n💬 متن: [{short}...]\n📁 فایل: {has_f}\n\n"
                if not bnrs:
                    txt += "هیچ بنری ثبت نشده."
                await cb.message.edit_text(txt, reply_markup=banner_slot_kb(acc_id, slot, "secretary"))

            elif d.startswith("bn_add_"):
                parts = d.split("_")
                acc_id, slot, ctx = parts[2], int(parts[3]), parts[4]
                set_step(ADMIN_ID, f"bn_text_{acc_id}_{slot}_{ctx}")
                await cb.message.edit_text("📝 متن بنر را وارد کنید:")

            elif d.startswith("bn_del_"):
                parts = d.split("_")
                acc_id, slot, ctx = parts[2], int(parts[3]), parts[4]
                u("DELETE FROM banners WHERE account_id=%s AND slot=%s AND context=%s",
                  (acc_id, slot, ctx))
                await cb.answer(f"✅ بنر {slot} حذف شد")
                await cb.message.edit_reply_markup(banner_slot_kb(acc_id, slot, ctx))

            elif d.startswith("bn_delall_"):
                parts = d.split("_")
                acc_id, ctx = parts[2], parts[3]
                u("DELETE FROM banners WHERE account_id=%s AND context=%s", (acc_id, ctx))
                await cb.answer("✅ همه بنرها حذف شدند")

            elif d.startswith("bn_back_"):
                parts = d.split("_")
                acc_id, ctx = parts[2], parts[3]
                if ctx == "secretary":
                    if acc_id == "global":
                        await cb.message.edit_text("👽 پنل منشی خودکار همگانی:", reply_markup=global_secretary_kb())
                    else:
                        row = q("SELECT is_active FROM secretary WHERE account_id=%s", (acc_id,))
                        active = row[0][0] if row else 0
                        await cb.message.edit_text("👽 پنل منشی خودکار:", reply_markup=secretary_kb(acc_id, active))
                else:
                    row = q("SELECT is_active FROM scheduler WHERE account_id=%s", (acc_id,))
                    active = row[0][0] if row else 0
                    await cb.message.edit_text("⏰ پنل زمان‌بند:", reply_markup=scheduler_kb(acc_id, active))

            # ══ زمان‌بند ══
            elif d.startswith("m_sch_"):
                acc_id = d[6:]
                row = q("SELECT is_active,interval_minutes FROM scheduler WHERE account_id=%s", (acc_id,))
                active = row[0][0] if row else 0
                interval = row[0][1] if row else 10
                await cb.message.edit_text(
                    f"⏰ **پنل ارسال زمان‌بندی**\n\nفاصله: هر {interval} دقیقه\nوضعیت: {'✅ فعال' if active else '❌ غیرفعال'}",
                    reply_markup=scheduler_kb(acc_id, active)
                )

            elif d.startswith("sch_tog_"):
                acc_id = d[8:]
                row = q("SELECT is_active FROM scheduler WHERE account_id=%s", (acc_id,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                u("INSERT INTO scheduler (account_id,admin_id,is_active) VALUES(%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"زمان‌بند {'فعال' if new else 'غیرفعال'} شد")
                await cb.message.edit_reply_markup(scheduler_kb(acc_id, new))

            elif d.startswith("sch_time_"):
                acc_id = d[9:]
                set_step(ADMIN_ID, f"sch_int_{acc_id}")
                await cb.message.edit_text("⏱ زمان ارسال را به دقیقه وارد کنید:\nمثال: `10`")

            elif d.startswith("sch_txt_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"bn_text_{acc_id}_1_scheduler")
                await cb.message.edit_text("📝 متن بنر زمان‌بند را وارد کنید:")

            elif d.startswith("sch_ref_"):
                await cb.answer("🔄 بروزرسانی شد", show_alert=True)

            elif d.startswith("sch_fwd_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"sch_fwd_link_{acc_id}")
                await cb.message.edit_text(
                    "📤 لینک پیامی که فوروارد شود:\nمثال: `https://t.me/channel/123`",
                    reply_markup=back_kb(f"m_sch_{acc_id}")
                )

            # ══ استخراج لینک ══
            elif d.startswith("m_ext_"):
                acc_id = d[6:]
                await cb.message.edit_text(
                    "🔗 **استخراج لینک**\n\nیکی از روش‌های زیر را انتخاب کنید:",
                    reply_markup=ext_menu_kb(acc_id)
                )

            elif d.startswith("ext_single_"):
                acc_id = d[11:]
                set_step(ADMIN_ID, f"ext_ch_{acc_id}")
                await cb.message.edit_text(
                    "🔗 آیدی لینکدونی را بفرستید:\nمثال: `@link4you`",
                    reply_markup=back_kb(f"m_ext_{acc_id}")
                )

            elif d.startswith("ext_multi_"):
                acc_id = d[10:]
                set_step(ADMIN_ID, f"extm_ch_{acc_id}")
                await cb.message.edit_text(
                    "🔗📚 آیدی لینکدونی‌ها را ارسال کنید (هر کدام در یک خط):\n\n"
                    "مثال:\n`@link4you`\n`@channel2`\n`@channel3`",
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
                from pyrogram import enums
                grps = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                        grps += 1
                await uc.stop()
                await cb.answer(f"👥 تعداد گروه‌ها: {grps}", show_alert=True)

            elif d.startswith("grp_leave_limited_"):
                acc_id = d[18:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums
                from pyrogram.errors import ChatWriteForbidden
                left = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                        try:
                            await uc.send_message(dlg.chat.id, ".")
                        except ChatWriteForbidden:
                            await uc.leave_chat(dlg.chat.id)
                            left += 1
                await uc.stop()
                await cb.answer(f"✅ از {left} گروه محدود خارج شد", show_alert=True)

            elif d.startswith("grp_fj_tog_"):
                acc_id = d[11:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                  "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE force_join_active=%s",
                  (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"عضویت اجبار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)
                await cb.message.edit_reply_markup(groups_kb(acc_id, new))

            # ══ حذف پیوی‌ها ══
            elif d.startswith("delpv_yes_"):
                acc_id = d[10:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums
                count = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type == enums.ChatType.PRIVATE:
                        try:
                            await uc.delete_history(dlg.chat.id, revoke=True)
                            count += 1
                        except Exception:
                            pass
                await uc.stop()
                await cb.message.edit_text(f"✅ {count} پیوی حذف شد.",
                                            reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_delpv_"):
                acc_id = d[8:]
                await cb.message.edit_text(
                    "🗑 آیا مطمئن هستید که می‌خواهید **همه پیوی‌ها** را حذف کنید؟",
                    reply_markup=confirm_kb(f"delpv_yes_{acc_id}", f"acc_manage_{acc_id}")
                )

            # ══ عضویت در لینک‌ها ══
            elif d.startswith("join_go_"):
                acc_id = d[8:]
                links_raw = get_step_data(ADMIN_ID)
                links = [l for l in links_raw.splitlines() if l.strip()]
                row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
                mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                await cb.message.edit_text(f"🚀 عملیات عضویت برای {len(links)} لینک شروع شد...")
                asyncio.create_task(_join_task(client, acc_id, links, mn, mx))
                clear_step(ADMIN_ID)

            elif d.startswith("m_join_"):
                acc_id = d[7:]
                row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (acc_id,))
                mn, mx = (row[0][0]//60, row[0][1]//60) if row else (3, 7)
                set_step(ADMIN_ID, f"join_{acc_id}")
                await cb.message.edit_text(
                    f"➕ **عضو شدن در لینک گروه‌ها**\n\n"
                    f"⏱ فاصله فعلی: {mn}–{mx} دقیقه\n\n"
                    f"لینک‌ها را هر کدام در یک خط وارد کنید:\n"
                    f"⚠️ برای جلوگیری از لیمیت، کمتر از ۱۰ لینک بفرستید.",
                    reply_markup=back_kb(f"acc_manage_{acc_id}")
                )

            # ══ عضویت اجبار ══
            elif d.startswith("fj_tog_"):
                acc_id = d[7:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                cur = row[0][0] if row else 0
                new = 0 if cur else 1
                u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                  "VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE force_join_active=%s",
                  (acc_id, ADMIN_ID, new, new))
                await cb.answer(f"عضویت اجبار {'فعال' if new else 'غیرفعال'} شد", show_alert=True)

            elif d.startswith("m_fj_"):
                acc_id = d[5:]
                row = q("SELECT force_join_active FROM join_settings WHERE account_id=%s", (acc_id,))
                fj = row[0][0] if row else 0
                await cb.message.edit_text(
                    "🕵️ **شناسایی عضویت اجباری گروه‌ها**\n\n"
                    f"وضعیت: {'✅ فعال' if fj else '❌ غیرفعال'}",
                    reply_markup=confirm_kb(f"fj_tog_{acc_id}", f"acc_manage_{acc_id}")
                )

            # ══ ارسال پیام به پیوی‌ها ══
            elif d.startswith("spv_go_"):
                acc_id = d[7:]
                text = get_step_data(ADMIN_ID)
                await cb.message.edit_text("⏳ در حال ارسال به پیوی‌ها...")
                asyncio.create_task(_send_to_pvs(client, acc_id, text))
                clear_step(ADMIN_ID)

            elif d.startswith("m_spv_"):
                acc_id = d[6:]
                set_step(ADMIN_ID, f"spv_{acc_id}")
                await cb.message.edit_text("💬 متن پیام برای پیوی‌ها:",
                                            reply_markup=back_kb(f"acc_manage_{acc_id}"))

            # ══ ارسال پیام به گروه‌ها ══
            elif d.startswith("sgrp_go_"):
                acc_id = d[8:]
                text = get_step_data(ADMIN_ID)
                await cb.message.edit_text("⏳ در حال ارسال به گروه‌ها...")
                asyncio.create_task(_send_to_groups(client, acc_id, text))
                clear_step(ADMIN_ID)

            elif d.startswith("m_sgrp_"):
                acc_id = d[7:]
                set_step(ADMIN_ID, f"sgrp_{acc_id}")
                await cb.message.edit_text("📢 متن پیام برای گروه‌ها:",
                                            reply_markup=back_kb(f"acc_manage_{acc_id}"))

            # ══ خروج از همه ══
            elif d.startswith("leave_yes_"):
                acc_id = d[10:]
                uc = await get_user_client(acc_id)
                if not uc:
                    await cb.answer("❌ در دسترس نیست", show_alert=True); return
                from pyrogram import enums
                count = 0
                await uc.start()
                async for dlg in uc.get_dialogs():
                    if dlg.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL):
                        try:
                            await uc.leave_chat(dlg.chat.id)
                            count += 1
                            await asyncio.sleep(0.5)
                        except Exception:
                            pass
                await uc.stop()
                await cb.message.edit_text(f"✅ از {count} گروه و کانال خارج شد.",
                                            reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_leave_"):
                acc_id = d[8:]
                await cb.message.edit_text(
                    "⚠️ آیا مطمئن هستید که می‌خواهید از **تمام گروه‌ها و کانال‌ها** خارج شوید؟",
                    reply_markup=confirm_kb(f"leave_yes_{acc_id}", f"acc_manage_{acc_id}")
                )

            # ══ تنظیمات پروفایل ══
            elif d.startswith("m_bio_"):
                acc_id = d[6:]
                set_step(ADMIN_ID, f"set_bio_{acc_id}")
                await cb.message.edit_text("📝 بیو جدید:", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_uname_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"set_uname_{acc_id}")
                await cb.message.edit_text("🆔 نام کاربری جدید (بدون @):", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_fname_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"set_fname_{acc_id}")
                await cb.message.edit_text("👤 نام جدید:", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            elif d.startswith("m_lname_"):
                acc_id = d[8:]
                set_step(ADMIN_ID, f"set_lname_{acc_id}")
                await cb.message.edit_text("👤 فامیلی جدید:", reply_markup=back_kb(f"acc_manage_{acc_id}"))

            # ══ global ══
            elif d == "g_stats":
                accs = q("SELECT id,name,phone FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                txt = f"📊 **آمار همه اکانت‌ها ({len(accs)})**\n\n"
                for a in accs:
                    txt += f"👤 {a[1]} | `{a[2]}`\n"
                await cb.message.edit_text(txt, reply_markup=back_kb("menu_global"))

            elif d == "g_status":
                accs = q("SELECT id,name,phone FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                txt = "♻️ **وضعیت اکانت‌ها:**\n\n"
                for a in accs:
                    uc = await get_user_client(a[0])
                    try:
                        await uc.start()
                        await uc.get_me()
                        await uc.stop()
                        txt += f"✅ {a[1]} | `{a[2]}`\n"
                    except Exception:
                        txt += f"❌ {a[1]} | `{a[2]}`\n"
                await cb.message.edit_text(txt, reply_markup=back_kb("menu_global"))

            elif d == "g_bio":
                set_step(ADMIN_ID, "g_bio")
                await cb.message.edit_text("📝 بیو جدید برای همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_fname":
                set_step(ADMIN_ID, "g_fname")
                await cb.message.edit_text("👤 نام جدید برای همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_lname":
                set_step(ADMIN_ID, "g_lname")
                await cb.message.edit_text("👤 فامیلی جدید برای همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_spv":
                set_step(ADMIN_ID, "g_spv")
                await cb.message.edit_text("💬 متن پیام برای پیوی‌های همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_spv_go":
                text = get_step_data(ADMIN_ID)
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                for (aid,) in accs:
                    asyncio.create_task(_send_to_pvs(client, aid, text))
                await cb.message.edit_text("✅ ارسال شروع شد.", reply_markup=global_kb())
                clear_step(ADMIN_ID)

            elif d == "g_sgrp":
                set_step(ADMIN_ID, "g_sgrp")
                await cb.message.edit_text("📢 متن پیام برای گروه‌های همه:", reply_markup=back_kb("menu_global"))

            elif d == "g_sgrp_go":
                text = get_step_data(ADMIN_ID)
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                await cb.message.edit_text("⏳ ارسال به گروه‌های همه اکانت‌ها شروع شد...", reply_markup=global_kb())
                clear_step(ADMIN_ID)
                asyncio.create_task(_send_to_groups_all(client, [a[0] for a in accs], text))

            elif d == "g_join":
                set_step(ADMIN_ID, "g_join")
                await cb.message.edit_text("➕ لینک‌ها را هر کدام در یک خط وارد کنید:",
                                            reply_markup=back_kb("menu_global"))

            elif d == "g_join_split":
                links_raw = get_step_data(ADMIN_ID)
                links = [l for l in links_raw.splitlines() if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                if not accs:
                    await cb.answer("اکانتی وجود ندارد", show_alert=True); return
                per = max(1, len(links) // len(accs))
                await cb.message.edit_text(f"🔀 {len(links)} لینک بین {len(accs)} اکانت تقسیم شد.")
                for i, (aid,) in enumerate(accs):
                    chunk = links[i*per:(i+1)*per]
                    if chunk:
                        row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                        mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                        asyncio.create_task(_join_task(client, aid, chunk, mn, mx))
                clear_step(ADMIN_ID)

            elif d == "g_join_all":
                links_raw = get_step_data(ADMIN_ID)
                links = [l for l in links_raw.splitlines() if l.strip()]
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                await cb.message.edit_text(f"📋 همه اکانت‌ها {len(links)} لینک را عضو می‌شوند.")
                for (aid,) in accs:
                    row = q("SELECT min_delay,max_delay FROM join_settings WHERE account_id=%s", (aid,))
                    mn, mx = (row[0][0], row[0][1]) if row else (180, 420)
                    asyncio.create_task(_join_task(client, aid, links, mn, mx))
                clear_step(ADMIN_ID)

            elif d == "g_fj":
                accs = q("SELECT id FROM accounts WHERE admin_id=%s", (ADMIN_ID,))
                for (aid,) in accs:
                    u("INSERT INTO join_settings (account_id,admin_id,force_join_active) "
                      "VALUES(%s,%s,1) ON DUPLICATE KEY UPDATE force_join_active=1", (aid, ADMIN_ID))
                await cb.answer("✅ عضویت اجبار برای همه فعال شد", show_alert=True)

            elif d in ("gsch_pv", "gsch_grp"):
                target = "pv" if d == "gsch_pv" else "group"
                row = q("SELECT text,interval_minutes,is_active FROM global_schedule WHERE admin_id=%s AND target=%s",
                        (ADMIN_ID, target))
                txt, interval, active = (row[0] if row else ("", 60, 0))
                label = "پی‌وی‌ها" if target == "pv" else "گروه‌ها"
                await cb.message.edit_text(
                    f"⏰ **ارسال زمان‌بندی به {label}**\n\n"
                    f"📝 متن فعلی: {txt or '—'}\n"
                    f"⏱ فاصله ارسال: هر {interval} دقیقه\n"
                    f"وضعیت: {'✅ فعال' if active else '❌ غیرفعال'}\n\n"
                    "ابتدا متن و زمان را تنظیم کنید سپس روشن کنید.",
                    reply_markup=global_schedule_kb(target, active, interval)
                )

            elif d.startswith("gsch_text_"):
                target = d[10:]
                panel_cb = "gsch_pv" if target == "pv" else "gsch_grp"
                set_step(ADMIN_ID, f"gsch_text_{target}")
                await cb.message.edit_text(
                    "📝 متنی که باید طبق زمان‌بندی ارسال شود را بفرستید:",
                    reply_markup=back_kb(panel_cb)
                )

            elif d.startswith("gsch_int_"):
                target = d[9:]
                panel_cb = "gsch_pv" if target == "pv" else "gsch_grp"
                set_step(ADMIN_ID, f"gsch_int_{target}")
                await cb.message.edit_text(
                    "⏱ فاصله ارسال را به دقیقه وارد کنید:\nمثال: `60`",
                    reply_markup=back_kb(panel_cb)
                )

            elif d.startswith("gsch_tog_"):
                target = d[9:]
                cur_row = q("SELECT text,interval_minutes,is_active FROM global_schedule WHERE admin_id=%s AND target=%s",
                             (ADMIN_ID, target))
                txt, interval, active = (cur_row[0] if cur_row else ("", 60, 0))
                if not active and not txt:
                    await cb.answer("⚠️ ابتدا متن را تنظیم کنید", show_alert=True)
                    return
                new = 0 if active else 1
                u("INSERT INTO global_schedule (admin_id,target,interval_minutes,is_active) VALUES(%s,%s,%s,%s) "
                  "ON DUPLICATE KEY UPDATE is_active=%s", (ADMIN_ID, target, interval, new, new))
                await cb.answer(f"زمان‌بندی {'فعال' if new else 'غیرفعال'} شد")
                await cb.message.edit_reply_markup(global_schedule_kb(target, new, interval))

            elif d == "g_fwdgrp":
                set_step(ADMIN_ID, "g_fwdgrp")
                await cb.message.edit_text("📤 لینک پیامی که فوروارد شود:", reply_markup=back_kb("menu_global"))

        except Exception as e:
            print(f"[CB ERROR] {d}: {e}")
            try:
                await cb.answer(f"❌ خطا: {str(e)[:100]}", show_alert=True)
            except Exception:
                pass

        try:
            await cb.answer()
        except Exception:
            pass


# ─── helpers ────────────────────────────────────────────────

from handlers.text_handler import _join_links

async def _join_task(bot_client, acc_id, links, mn, mx):
    await _join_links(bot_client, acc_id, links, mn, mx)

async def _send_to_pvs(bot_client, acc_id, text):
    from pyrogram import enums
    from pyrogram.errors import FloodWait
    uc = await get_user_client(acc_id)
    if not uc: return
    me_info = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
    display = me_info[0][0] if me_info else acc_id
    ok = fail = 0
    await uc.start()
    async for dlg in uc.get_dialogs():
        if dlg.chat.type == enums.ChatType.PRIVATE:
            try:
                try:
                    await uc.send_message(dlg.chat.id, text)
                except FloodWait as e:
                    await report_flood(bot_client, display, "ارسال به پیوی‌ها", e)
                    await uc.send_message(dlg.chat.id, text)
                ok += 1
                await asyncio.sleep(2)
            except Exception:
                fail += 1
    await uc.stop()
    await bot_client.send_message(
        ADMIN_ID,
        f"✅ ارسال به پیوی‌ها تمام شد\n👤 {display}\n✔️ موفق: {ok}\n❌ ناموفق: {fail}"
    )

async def _send_to_groups_all(bot_client, acc_ids, text):
    tot_ok = tot_left = tot_fail = 0
    for aid in acc_ids:
        ok, left, fail = await _send_to_groups(bot_client, aid, text, report=False)
        tot_ok += ok; tot_left += left; tot_fail += fail
    await bot_client.send_message(
        ADMIN_ID,
        "✅ **ارسال به گروه‌های همه اکانت‌ها تمام شد**\n\n"
        f"✔️ موفق: {tot_ok}\n"
        f"🚫 محدود بود (پیام ارسال نشد) و خروج شد: {tot_left}\n"
        f"⚠️ سایر موارد ناموفق (احتمالاً عضویت اجباری یا خطای دیگر): {tot_fail}"
    )

async def _send_to_groups(bot_client, acc_id, text, report=True):
    from pyrogram import enums
    from pyrogram.errors import ChatWriteForbidden, ChatForbidden, FloodWait
    uc = await get_user_client(acc_id)
    if not uc:
        return (0, 0, 0)
    me_info = q("SELECT phone FROM accounts WHERE id=%s", (acc_id,))
    display = me_info[0][0] if me_info else acc_id
    ok = fail = left = 0
    await uc.start()
    async for dlg in uc.get_dialogs():
        if dlg.chat.type in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
            try:
                try:
                    await uc.send_message(dlg.chat.id, text)
                except FloodWait as e:
                    await report_flood(bot_client, display, "ارسال به گروه‌ها", e)
                    await uc.send_message(dlg.chat.id, text)
                ok += 1
                await asyncio.sleep(2)
            except (ChatWriteForbidden, ChatForbidden):
                # ── گروه محدود/مسدود برای ارسال پیام → خروج خودکار ──
                try:
                    await uc.leave_chat(dlg.chat.id)
                    left += 1
                except Exception:
                    fail += 1
            except Exception:
                fail += 1
    await uc.stop()
    if report:
        await bot_client.send_message(
            ADMIN_ID,
            f"✅ ارسال به گروه‌ها تمام شد\n👤 {display}\n"
            f"✔️ موفق: {ok}\n"
            f"🚫 محدود بود و خروج شد: {left}\n"
            f"⚠️ سایر موارد ناموفق: {fail}"
        )
    return (ok, left, fail)
