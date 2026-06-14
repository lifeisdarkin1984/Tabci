from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─── منوی اصلی ─────────────────────────────────────────────
def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚙️ دستورات تبچی", callback_data="menu_tabchi"),
         InlineKeyboardButton("🌐 مدیریت همگانی", callback_data="menu_global")],
    ])

# ─── لیست اکانت‌ها ──────────────────────────────────────────
def tabchi_list_kb(accounts):
    btns = []
    for a in accounts:
        btns.append([InlineKeyboardButton(
            f"👤 {a[2]} | {a[1]}", callback_data=f"acc_sel_{a[0]}")])
    btns.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
    return InlineKeyboardMarkup(btns)

# ─── اطلاعات اکانت ──────────────────────────────────────────
def acc_info_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 کد ورود",  callback_data=f"acc_code_{acc_id}"),
         InlineKeyboardButton("♻️ وضعیت",   callback_data=f"acc_status_{acc_id}"),
         InlineKeyboardButton("❌ حذف",      callback_data=f"acc_del_{acc_id}")],
        [InlineKeyboardButton("🔧 مدیریت تبچی", callback_data=f"acc_manage_{acc_id}")],
        [InlineKeyboardButton("🔄 بروزرسانی تبچی‌ها", callback_data="acc_refresh")],
        [InlineKeyboardButton("🔙 بازگشت",   callback_data="menu_tabchi")],
    ])

# ─── پنل مدیریت تبچی ────────────────────────────────────────
def manage_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار اکانت", callback_data=f"m_stats_{acc_id}")],
        [InlineKeyboardButton("🤖 منشی خودکار",     callback_data=f"m_sec_{acc_id}"),
         InlineKeyboardButton("⏰ ارسال زمان‌بندی", callback_data=f"m_sch_{acc_id}")],
        [InlineKeyboardButton("↩️ ریپلای رندم",     callback_data=f"m_reply_{acc_id}"),
         InlineKeyboardButton("😀 ری‌اکت رندم",     callback_data=f"m_react_{acc_id}")],
        [InlineKeyboardButton("🔗 استخراج لینک",    callback_data=f"m_ext_{acc_id}"),
         InlineKeyboardButton("👥 لیست گروه‌ها",   callback_data=f"m_grps_{acc_id}")],
        [InlineKeyboardButton("🗑 حذف پیوی‌ها",     callback_data=f"m_delpv_{acc_id}"),
         InlineKeyboardButton("➕ عضو شدن لینک‌ها", callback_data=f"m_join_{acc_id}")],
        [InlineKeyboardButton("🕵️ عضویت اجبار",     callback_data=f"m_fj_{acc_id}"),
         InlineKeyboardButton("🚫 خروج خودکار محدود", callback_data=f"m_autoleave_{acc_id}")],
        [InlineKeyboardButton("💬 پیام به پیوی‌ها", callback_data=f"m_spv_{acc_id}"),
         InlineKeyboardButton("📢 پیام به گروه‌ها", callback_data=f"m_sgrp_{acc_id}")],
        [InlineKeyboardButton("🚪 خروج از همه",     callback_data=f"m_leave_{acc_id}")],
        [InlineKeyboardButton("📝 تنظیم بیو",        callback_data=f"m_bio_{acc_id}"),
         InlineKeyboardButton("🆔 تنظیم آیدی",      callback_data=f"m_uname_{acc_id}")],
        [InlineKeyboardButton("👤 تنظیم نام",        callback_data=f"m_fname_{acc_id}"),
         InlineKeyboardButton("👤 تنظیم فامیلی",    callback_data=f"m_lname_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",           callback_data=f"acc_sel_{acc_id}")],
    ])

# ─── منوی همگانی ────────────────────────────────────────────
def global_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 توقف تمام عملیات", callback_data="g_stopall")],
        [InlineKeyboardButton("⏰ ارسال زمان‌دار",          callback_data="g_sch_menu"),
         InlineKeyboardButton("➕ عضو شدن گروه‌ها",        callback_data="g_join")],
        [InlineKeyboardButton("🕵️ عضویت اجبار",            callback_data="g_fj"),
         InlineKeyboardButton("🚫 خروج خودکار محدود",      callback_data="g_autoleave")],
        [InlineKeyboardButton("📤 فوروارد سریع",           callback_data="g_fwdgrp"),
         InlineKeyboardButton("📢 ارسال سریع به گروه‌ها",  callback_data="g_sgrp")],
        [InlineKeyboardButton("💬 ارسال به پیوی‌ها",       callback_data="g_spv")],
        [InlineKeyboardButton("↩️ ریپلای رندم همگانی",     callback_data="g_rr"),
         InlineKeyboardButton("😀 ری‌اکت رندم همگانی",     callback_data="g_rc")],
        [InlineKeyboardButton("🤖 منشی خودکار همگانی",     callback_data="g_sec")],
        [InlineKeyboardButton("✏️ تغییر نام",    callback_data="g_fname"),
         InlineKeyboardButton("✏️ تغییر فامیلی", callback_data="g_lname"),
         InlineKeyboardButton("📝 تغییر بیو",    callback_data="g_bio")],
        [InlineKeyboardButton("📊 آمار اکانت‌ها",   callback_data="g_stats"),
         InlineKeyboardButton("♻️ وضعیت اکانت‌ها", callback_data="g_status")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])

# ─── منشی خودکار ────────────────────────────────────────────
def secretary_kb(acc_id, active):
    lbl = "🔴 غیرفعال کردن" if active else "🟢 فعال کردن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام اول", callback_data=f"sec_b1_{acc_id}"),
         InlineKeyboardButton("💬 پیام دوم", callback_data=f"sec_b2_{acc_id}")],
        [InlineKeyboardButton("💬 پیام سوم", callback_data=f"sec_b3_{acc_id}")],
        [InlineKeyboardButton(f"{lbl} منشی", callback_data=f"sec_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",   callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── منشی همگانی ────────────────────────────────────────────
def global_sec_kb(active):
    lbl = "🔴 غیرفعال کردن" if active else "🟢 فعال کردن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام اول", callback_data="gsec_b1"),
         InlineKeyboardButton("💬 پیام دوم", callback_data="gsec_b2")],
        [InlineKeyboardButton("💬 پیام سوم", callback_data="gsec_b3")],
        [InlineKeyboardButton(f"{lbl} منشی همگانی", callback_data="gsec_tog")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

# ─── بنر ────────────────────────────────────────────────────
def banner_slot_kb(acc_id, slot, ctx):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗑 حذف بنر [{slot}]", callback_data=f"bn_del_{acc_id}_{slot}_{ctx}"),
         InlineKeyboardButton("🗑 حذف همه",            callback_data=f"bn_delall_{acc_id}_{ctx}")],
        [InlineKeyboardButton("📩 اضافه کردن بنر",    callback_data=f"bn_add_{acc_id}_{slot}_{ctx}"),
         InlineKeyboardButton("🔙 بازگشت",             callback_data=f"bn_back_{acc_id}_{ctx}")],
    ])

# ─── زمان‌بند ────────────────────────────────────────────────
def scheduler_kb(acc_id, active):
    lbl = "🔴 خاموش" if active else "🟢 روشن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 پنل پیام عادی",    callback_data=f"sch_txt_{acc_id}"),
         InlineKeyboardButton("📤 ارسال فوروارد",    callback_data=f"sch_fwd_{acc_id}")],
        [InlineKeyboardButton("⏱ تنظیم زمان",        callback_data=f"sch_time_{acc_id}"),
         InlineKeyboardButton("🔄 بروزرسانی گروه‌ها", callback_data=f"sch_ref_{acc_id}")],
        [InlineKeyboardButton(lbl,                    callback_data=f"sch_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",            callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── ریپلای رندم ────────────────────────────────────────────
def reply_rand_kb(acc_id, active):
    lbl = "🔴 غیرفعال" if active else "🟢 فعال"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تنظیم متن پیام",   callback_data=f"rr_setmsg_{acc_id}")],
        [InlineKeyboardButton("⏱ تنظیم زمان",        callback_data=f"rr_time_{acc_id}"),
         InlineKeyboardButton(lbl,                    callback_data=f"rr_tog_{acc_id}")],
        [InlineKeyboardButton("▶️ اجرای دستی",       callback_data=f"rr_run_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",            callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── ری‌اکت رندم ────────────────────────────────────────────
def react_rand_kb(acc_id, active):
    lbl = "🔴 غیرفعال" if active else "🟢 فعال"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ تنظیم زمان",  callback_data=f"rc_time_{acc_id}"),
         InlineKeyboardButton(lbl,              callback_data=f"rc_tog_{acc_id}")],
        [InlineKeyboardButton("▶️ اجرای دستی", callback_data=f"rc_run_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",      callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── استخراج لینک ───────────────────────────────────────────
def extract_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 استخراج از یک لینکدونی",    callback_data=f"ext_one_{acc_id}")],
        [InlineKeyboardButton("🔗🔗 استخراج از چند لینکدونی", callback_data=f"ext_multi_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── لیست گروه‌ها ───────────────────────────────────────────
def groups_kb(acc_id, active_fj):
    lbl = "🔴 لغو عضویت اجبار" if active_fj else "🟢 فعال عضویت اجبار"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار گروه‌ها",               callback_data=f"grp_stats_{acc_id}")],
        [InlineKeyboardButton("🚫 خروج از گروه‌های محدود",    callback_data=f"grp_leave_limited_{acc_id}")],
        [InlineKeyboardButton(lbl,                              callback_data=f"grp_fj_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",                     callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── خروج خودکار محدود ──────────────────────────────────────
def auto_leave_kb(acc_id, active):
    lbl = "🔴 غیرفعال کردن" if active else "🟢 فعال کردن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{lbl} خروج خودکار",
                              callback_data=f"autoleave_tog_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── عضویت همگانی ───────────────────────────────────────────
def global_join_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔀 تقسیم لینک‌ها", callback_data="g_join_split"),
         InlineKeyboardButton("📋 تمام لینک‌ها",  callback_data="g_join_all")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

# ─── ارسال زمان‌دار همگانی - منو ─────────────────────────────
def global_sch_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 ارسال زمان‌دار گروه‌ها", callback_data="gsch_panel_groups")],
        [InlineKeyboardButton("💬 ارسال زمان‌دار پیوی‌ها", callback_data="gsch_panel_pvs")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

# ─── ارسال زمان‌دار همگانی - پنل (گروه/پیوی) ─────────────────
def global_sch_panel_kb(target, active):
    lbl = "🔴 خاموش کردن" if active else "🟢 روشن کردن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام ۱", callback_data=f"gsch_b1_{target}"),
         InlineKeyboardButton("💬 پیام ۲", callback_data=f"gsch_b2_{target}")],
        [InlineKeyboardButton("💬 پیام ۳", callback_data=f"gsch_b3_{target}"),
         InlineKeyboardButton("💬 پیام ۴", callback_data=f"gsch_b4_{target}")],
        [InlineKeyboardButton("⏱ تنظیم زمان", callback_data=f"gsch_time_{target}"),
         InlineKeyboardButton(lbl, callback_data=f"gsch_tog_{target}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="g_sch_menu")],
    ])

# ─── بنر زمان‌دار همگانی ─────────────────────────────────────
def global_banner_slot_kb(target, slot):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🗑 حذف پیام [{slot}]", callback_data=f"gbn_del_{target}_{slot}"),
         InlineKeyboardButton("🗑 حذف همه",            callback_data=f"gbn_delall_{target}")],
        [InlineKeyboardButton("📩 تنظیم/تغییر پیام",  callback_data=f"gbn_add_{target}_{slot}"),
         InlineKeyboardButton("🔙 بازگشت",             callback_data=f"gbn_back_{target}")],
    ])

# ─── تایید / لغو ────────────────────────────────────────────
def confirm_kb(yes, no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ بله", callback_data=yes),
         InlineKeyboardButton("❌ خیر", callback_data=no)],
    ])

def back_kb(cb):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=cb)]])
