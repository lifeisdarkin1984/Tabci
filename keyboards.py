from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ دستورات تبچی", callback_data="menu_tabchi"),
         InlineKeyboardButton("🌐 مدیریت همگانی", callback_data="menu_global")],
    ])

def tabchi_list_kb(accounts):
    btns = []
    for a in accounts:
        btns.append([InlineKeyboardButton(
            f"👤 {a[2]} | {a[1]}", callback_data=f"acc_sel_{a[0]}")])
    btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(btns)

def acc_info_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 کد ورود", callback_data=f"acc_code_{acc_id}"),
         InlineKeyboardButton("♻️ وضعیت",   callback_data=f"acc_status_{acc_id}"),
         InlineKeyboardButton("❌ حذف",      callback_data=f"acc_del_{acc_id}")],
        [InlineKeyboardButton("🔧 مدیریت تبچی", callback_data=f"acc_manage_{acc_id}")],
        [InlineKeyboardButton("🔄 بروزرسانی تبچی‌ها", callback_data="acc_refresh")],
        [InlineKeyboardButton("🔙 بازگشت",   callback_data="menu_tabchi")],
    ])

def manage_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار اکانت", callback_data=f"m_stats_{acc_id}")],
        [InlineKeyboardButton("🤖 منشی خودکار",       callback_data=f"m_sec_{acc_id}"),
         InlineKeyboardButton("⏰ ارسال زمان‌بندی",   callback_data=f"m_sch_{acc_id}")],
        [InlineKeyboardButton("🔗 استخراج لینک",      callback_data=f"m_ext_{acc_id}"),
         InlineKeyboardButton("👥 لیست گروه‌های من",  callback_data=f"m_grps_{acc_id}")],
        [InlineKeyboardButton("🗑 حذف تمام پیوی‌ها",  callback_data=f"m_delpv_{acc_id}"),
         InlineKeyboardButton("➕ عضو شدن لینک‌ها",   callback_data=f"m_join_{acc_id}")],
        [InlineKeyboardButton("🕵️ عضویت اجبار",       callback_data=f"m_fj_{acc_id}"),
         InlineKeyboardButton("💬 پیام به پیوی‌ها",   callback_data=f"m_spv_{acc_id}")],
        [InlineKeyboardButton("📢 پیام به گروه‌ها",   callback_data=f"m_sgrp_{acc_id}"),
         InlineKeyboardButton("🚪 خروج همه گروه‌ها",  callback_data=f"m_leave_{acc_id}")],
        [InlineKeyboardButton("📝 تنظیم بیو",          callback_data=f"m_bio_{acc_id}"),
         InlineKeyboardButton("🆔 تنظیم آیدی",         callback_data=f"m_uname_{acc_id}")],
        [InlineKeyboardButton("👤 تنظیم نام",           callback_data=f"m_fname_{acc_id}"),
         InlineKeyboardButton("👤 تنظیم فامیلی",        callback_data=f"m_lname_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"acc_sel_{acc_id}")],
    ])

def secretary_kb(acc_id, active):
    lbl = "🔴 غیرفعال کردن منشی" if active else "🟢 فعال کردن منشی"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام اول", callback_data=f"sec_b1_{acc_id}"),
         InlineKeyboardButton("💬 پیام دوم", callback_data=f"sec_b2_{acc_id}")],
        [InlineKeyboardButton("💬 پیام سوم", callback_data=f"sec_b3_{acc_id}")],
        [InlineKeyboardButton(lbl,            callback_data=f"sec_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",   callback_data=f"acc_manage_{acc_id}")],
    ])

def banner_slot_kb(acc_id, slot, ctx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗑 حذف بنر [{slot}]",  callback_data=f"bn_del_{acc_id}_{slot}_{ctx}"),
         InlineKeyboardButton("🗑 حذف همه بنرها",       callback_data=f"bn_delall_{acc_id}_{ctx}")],
        [InlineKeyboardButton("📩 اضافه کردن بنر",      callback_data=f"bn_add_{acc_id}_{slot}_{ctx}"),
         InlineKeyboardButton("🔙 بازگشت",              callback_data=f"bn_back_{acc_id}_{ctx}")],
    ])

def scheduler_kb(acc_id, active):
    lbl = "🔴 خاموش" if active else "🟢 روشن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 پنل پیام عادی",       callback_data=f"sch_txt_{acc_id}"),
         InlineKeyboardButton("📤 ارسال فوروارد",        callback_data=f"sch_fwd_{acc_id}")],
        [InlineKeyboardButton("⏱ تنظیم زمان",           callback_data=f"sch_time_{acc_id}"),
         InlineKeyboardButton("🔄 بروزرسانی گروه‌ها",   callback_data=f"sch_ref_{acc_id}")],
        [InlineKeyboardButton(lbl,                        callback_data=f"sch_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",               callback_data=f"acc_manage_{acc_id}")],
    ])

def global_secretary_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام اول", callback_data="sec_b1_global"),
         InlineKeyboardButton("💬 پیام دوم", callback_data="sec_b2_global")],
        [InlineKeyboardButton("💬 پیام سوم", callback_data="sec_b3_global")],
        [InlineKeyboardButton("🟢 فعال‌سازی برای همه اکانت‌ها", callback_data="g_sec_apply")],
        [InlineKeyboardButton("🔴 غیرفعال‌سازی برای همه اکانت‌ها", callback_data="g_sec_disable")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

def global_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤖 منشی خودکار همگانی",        callback_data="g_sec")],
        [InlineKeyboardButton("⏰ ارسال زمان‌دار",           callback_data="g_sch")],
        [InlineKeyboardButton("➕ عضو شدن در لیست گروه‌ها", callback_data="g_join")],
        [InlineKeyboardButton("🕵️ عضویت اجبار گروه‌ها",     callback_data="g_fj")],
        [InlineKeyboardButton("📤 فوروارد سریع به گروه‌ها", callback_data="g_fwdgrp"),
         InlineKeyboardButton("📢 ارسال سریع به گروه‌ها",   callback_data="g_sgrp")],
        [InlineKeyboardButton("💬 ارسال پیام به پیوی‌ها",   callback_data="g_spv")],
        [InlineKeyboardButton("✏️ تغییر نام",   callback_data="g_fname"),
         InlineKeyboardButton("✏️ تغییر فامیلی",callback_data="g_lname"),
         InlineKeyboardButton("📝 تغییر بیو",   callback_data="g_bio")],
        [InlineKeyboardButton("📊 آمار اکانت‌ها",   callback_data="g_stats"),
         InlineKeyboardButton("♻️ وضعیت اکانت‌ها", callback_data="g_status")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])

def global_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔀 تقسیم لینک‌ها", callback_data="g_join_split"),
         InlineKeyboardButton("📋 تمام لینک‌ها",  callback_data="g_join_all")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

def confirm_kb(yes, no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله", callback_data=yes),
         InlineKeyboardButton("❌ خیر", callback_data=no)],
    ])

def back_kb(cb):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=cb)]])

def groups_kb(acc_id, active_fj):
    lbl = "🔴 لغو عضویت اجبار" if active_fj else "🟢 فعال کردن عضویت اجبار"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار گروه‌ها", callback_data=f"grp_stats_{acc_id}")],
        [InlineKeyboardButton("🚫 خروج از گروه‌های محدود شده", callback_data=f"grp_leave_limited_{acc_id}")],
        [InlineKeyboardButton(lbl, callback_data=f"grp_fj_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"acc_manage_{acc_id}")],
    ])
