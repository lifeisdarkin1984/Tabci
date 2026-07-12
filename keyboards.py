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
        [InlineKeyboardButton("🗑 حذف",             callback_data=f"m_del_menu_{acc_id}"),
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

# ─── منوی حذف (تک‌اکانت) ─────────────────────────────────────
def del_menu_kb(acc_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 حذف پی‌وی‌ها",  callback_data=f"m_delpv_{acc_id}"),
         InlineKeyboardButton("👥 حذف گروه‌ها",   callback_data=f"m_delgrp_{acc_id}")],
        [InlineKeyboardButton("🤖 حذف ربات‌ها",   callback_data=f"m_delbot_{acc_id}"),
         InlineKeyboardButton("📢 حذف کانال‌ها",  callback_data=f"m_delchannel_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",         callback_data=f"acc_manage_{acc_id}")],
    ])

# ─── منوی همگانی ────────────────────────────────────────────
def global_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 توقف تمام عملیات", callback_data="g_stopall")],
        [InlineKeyboardButton("🗑 حذف",                     callback_data="g_del_menu")],
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
        [InlineKeyboardButton("🏷 مدیریت برچسب‌ها", callback_data="tags_menu")],
        [InlineKeyboardButton("📥 جوین از پیوی‌ها", callback_data="g_pvjoin")],
        [InlineKeyboardButton("📡 لینکدونی هوشمند", callback_data="ld_menu")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])

# ─── منوی حذف همگانی ───────────────────────────────────────
def global_del_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 حذف پی‌وی‌ها",  callback_data="g_delpv"),
         InlineKeyboardButton("👥 حذف گروه‌ها",   callback_data="g_delgrp")],
        [InlineKeyboardButton("🤖 حذف ربات‌ها",   callback_data="g_delbot"),
         InlineKeyboardButton("📢 حذف کانال‌ها",  callback_data="g_delchannel")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
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
        [InlineKeyboardButton("⚡ ارسال فوری", callback_data="gsec_now")],
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
def reply_rand_kb(acc_id, active, back_to=None, group_tag="ALL", acc_tag="ALL"):
    lbl = "🔴 غیرفعال" if active else "🟢 فعال"
    back = back_to or f"acc_manage_{acc_id}"
    gtag = f"🏷 {group_tag}" if group_tag not in ("ALL","") else "🏷 همه گروه‌ها"
    atag = f"👤 {acc_tag}" if acc_tag not in ("ALL","") else "👤 همه اکانت‌ها"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 مدیریت متن‌ها",     callback_data=f"rr_banners_{acc_id}")],
        [InlineKeyboardButton("⏱ تنظیم زمان",        callback_data=f"rr_time_{acc_id}"),
         InlineKeyboardButton(lbl,                    callback_data=f"rr_tog_{acc_id}")],
        [InlineKeyboardButton(gtag,                   callback_data=f"rr_gtag_{acc_id}"),
         InlineKeyboardButton(atag,                   callback_data=f"rr_atag_{acc_id}")],
        [InlineKeyboardButton("▶️ اجرای دستی",       callback_data=f"rr_run_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",            callback_data=back)],
    ])

def reply_banner_list_kb(acc_id, banners, back_to=None):
    """نمایش لیست بنرهای ریپلای با امکان اضافه/حذف"""
    back = back_to or f"m_reply_{acc_id}"
    rows = []
    for b in banners:
        slot = b[0]
        short = (b[1] or "")[:20]
        rows.append([InlineKeyboardButton(
            f"🗑 حذف [{slot}] {short}{'...' if b[1] and len(b[1])>20 else ''}",
            callback_data=f"rr_bdel_{acc_id}_{slot}"
        )])
    rows.append([InlineKeyboardButton("➕ افزودن متن جدید", callback_data=f"rr_badd_{acc_id}")])
    if banners:
        rows.append([InlineKeyboardButton("🗑 حذف همه", callback_data=f"rr_bdelall_{acc_id}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=back)])
    return InlineKeyboardMarkup(rows)

# ─── ری‌اکت رندم ────────────────────────────────────────────
def react_rand_kb(acc_id, active, back_to=None, group_tag="ALL", acc_tag="ALL"):
    lbl = "🔴 غیرفعال" if active else "🟢 فعال"
    back = back_to or f"acc_manage_{acc_id}"
    gtag = f"🏷 {group_tag}" if group_tag not in ("ALL","") else "🏷 همه گروه‌ها"
    atag = f"👤 {acc_tag}" if acc_tag not in ("ALL","") else "👤 همه اکانت‌ها"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⏱ تنظیم زمان",  callback_data=f"rc_time_{acc_id}"),
         InlineKeyboardButton(lbl,              callback_data=f"rc_tog_{acc_id}")],
        [InlineKeyboardButton(gtag,             callback_data=f"rc_gtag_{acc_id}"),
         InlineKeyboardButton(atag,             callback_data=f"rc_atag_{acc_id}")],
        [InlineKeyboardButton("▶️ اجرای دستی", callback_data=f"rc_run_{acc_id}")],
        [InlineKeyboardButton("🔙 بازگشت",      callback_data=back)],
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
def global_sch_panel_kb(target, active, gtag="ALL", atag="ALL", max_rounds=0, current_round=0):
    lbl = "🔴 خاموش کردن" if active else "🟢 روشن کردن"
    g_lbl = f"🏷 {gtag}" if gtag != "ALL" else "🏷 همه گروه‌ها"
    a_lbl = f"👤 {atag}" if atag != "ALL" else "👤 همه اکانت‌ها"
    if max_rounds == 0:
        rounds_lbl = "🔄 دور: نامحدود"
    else:
        rounds_lbl = f"🔄 دور: {current_round}/{max_rounds}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 پیام ۱", callback_data=f"gsch_b1_{target}"),
         InlineKeyboardButton("💬 پیام ۲", callback_data=f"gsch_b2_{target}")],
        [InlineKeyboardButton("💬 پیام ۳", callback_data=f"gsch_b3_{target}"),
         InlineKeyboardButton("💬 پیام ۴", callback_data=f"gsch_b4_{target}")],
        [InlineKeyboardButton("⏱ تنظیم زمان", callback_data=f"gsch_time_{target}"),
         InlineKeyboardButton(lbl, callback_data=f"gsch_tog_{target}")],
        [InlineKeyboardButton(g_lbl, callback_data=f"gsch_gtag_{target}"),
         InlineKeyboardButton(a_lbl, callback_data=f"gsch_atag_{target}")],
        [InlineKeyboardButton(rounds_lbl, callback_data=f"gsch_rounds_{target}")],
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

# ─── جوین از پیوی‌ها ─────────────────────────────────────────
def pv_join_kb(link_count, last_scan):
    last = last_scan.strftime("%H:%M - %y/%m/%d") if last_scan else "هرگز"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔍 اسکن الان ({last})", callback_data="g_pvjoin_scan")],
        [InlineKeyboardButton(f"📋 نمایش لینک‌ها ({link_count} عدد)", callback_data="g_pvjoin_show")],
        [InlineKeyboardButton("✅ جوین با لینک‌های یافت‌شده", callback_data="g_pvjoin_join")],
        [InlineKeyboardButton("🗑 پاک کردن لیست", callback_data="g_pvjoin_clear")],
        [InlineKeyboardButton("⚙️ تنظیمات اسکن خودکار", callback_data="g_pvjoin_settings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

def pv_join_settings_kb(auto_scan, interval_hours, daily_limit):
    auto_lbl = "🟢 فعال" if auto_scan else "🔴 غیرفعال"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"اسکن خودکار: {auto_lbl}", callback_data="g_pvjoin_tog_auto")],
        [InlineKeyboardButton(f"⏰ فاصله اسکن: {interval_hours} ساعت", callback_data="g_pvjoin_set_interval")],
        [InlineKeyboardButton(f"📊 سقف روزانه: {daily_limit} لینک", callback_data="g_pvjoin_set_limit")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="g_pvjoin")],
    ])

# ─── مدیریت برچسب‌ها ────────────────────────────────────────
def tags_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 برچسب گروه‌ها", callback_data="tags_groups")],
        [InlineKeyboardButton("👤 برچسب اکانت‌ها", callback_data="tags_accounts")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])

def tags_list_kb(tags, context="groups"):
    """لیست برچسب‌ها با امکان حذف"""
    rows = []
    for t in tags:
        rows.append([InlineKeyboardButton(
            f"🗑 حذف «{t}»", callback_data=f"tag_del_{context}_{t}"
        )])
    rows.append([InlineKeyboardButton("➕ برچسب جدید", callback_data=f"tag_new_{context}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tags_menu")])
    return InlineKeyboardMarkup(rows)

def tag_select_kb(tags, callback_prefix, show_no_tag=True, show_all=True):
    """انتخاب برچسب برای فیلتر عملیات"""
    rows = []
    for t in tags:
        rows.append([InlineKeyboardButton(
            f"🏷 {t}", callback_data=f"{callback_prefix}_tag_{t}"
        )])
    if show_no_tag:
        rows.append([InlineKeyboardButton(
            "🔘 بدون برچسب", callback_data=f"{callback_prefix}_tag_NOTAG"
        )])
    if show_all:
        rows.append([InlineKeyboardButton(
            "📋 همه", callback_data=f"{callback_prefix}_tag_ALL"
        )])
    return InlineKeyboardMarkup(rows)

def account_tag_kb(accounts):
    """لیست اکانت‌ها برای تنظیم برچسب"""
    rows = []
    for a in accounts:
        tag_str = f" [{a[3]}]" if a[3] else ""
        rows.append([InlineKeyboardButton(
            f"👤 {a[1]} | {a[2]}{tag_str}",
            callback_data=f"acctag_sel_{a[0]}"
        )])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tags_menu")])
    return InlineKeyboardMarkup(rows)

def account_tag_multi_kb(acc_id, all_tags, current_tags):
    """انتخاب چندگانه (toggle) برچسب برای یک اکانت"""
    rows = []
    for t in all_tags:
        mark = "✅" if t in current_tags else "⬜️"
        rows.append([InlineKeyboardButton(
            f"{mark} {t}", callback_data=f"acctagm_tog_{acc_id}_{t}"
        )])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="tags_accounts")])
    return InlineKeyboardMarkup(rows)


# ─── لینکدونی هوشمند ─────────────────────────────────────────

def ld_menu_kb(source_count, pending_count, auto_scan, auto_join):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📋 مدیریت لینکدونی‌ها ({source_count} عدد)",
                              callback_data="ld_sources")],
        [InlineKeyboardButton("🔍 اسکن فوری", callback_data="ld_scan_now")],
        [InlineKeyboardButton(f"🔗 لینک‌های دریافتی ({pending_count} عدد)",
                              callback_data="ld_show_links")],
        [InlineKeyboardButton("✅ جوین دستی لینک‌ها", callback_data="ld_join_manual")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="ld_settings")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_global")],
    ])


def ld_sources_kb(sources):
    buttons = []
    for s in sources:
        lbl = f"{'✅' if s['is_active'] else '⏸'} {s['chat_title'] or s['chat_id']}"
        buttons.append([InlineKeyboardButton(lbl,
                        callback_data=f"ld_src_{s['id']}")])
    buttons.append([InlineKeyboardButton("➕ افزودن لینکدونی",
                    callback_data="ld_add_source")])
    buttons.append([InlineKeyboardButton("📥 دریافت همه لینک‌ها",
                    callback_data="ld_src_getall")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="ld_menu")])
    return InlineKeyboardMarkup(buttons)


def ld_source_detail_kb(source_id, is_active):
    toggle_lbl = "⏸ غیرفعال کردن" if is_active else "▶️ فعال کردن"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_lbl,
                              callback_data=f"ld_src_tog_{source_id}")],
        [InlineKeyboardButton("🗑 حذف", callback_data=f"ld_src_del_{source_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ld_sources")],
    ])


def ld_settings_kb(auto_scan, interval, auto_join, join_mode, join_tag):
    mode_labels = {"random": "رندوم", "split": "تقسیم", "all": "همه به همه"}
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"اسکن خودکار: {'🟢 فعال' if auto_scan else '🔴 غیرفعال'}",
            callback_data="ld_tog_autoscan")],
        [InlineKeyboardButton(f"⏰ فاصله اسکن: هر {interval} ساعت",
                              callback_data="ld_set_interval")],
        [InlineKeyboardButton(
            f"جوین خودکار: {'🟢 فعال' if auto_join else '🔴 غیرفعال'}",
            callback_data="ld_tog_autojoin")],
        [InlineKeyboardButton(
            f"حالت جوین: {mode_labels.get(join_mode, join_mode)}",
            callback_data="ld_set_joinmode")],
        [InlineKeyboardButton(
            f"🏷 برچسب جوین: {join_tag if join_tag else 'بدون برچسب'}",
            callback_data="ld_set_tag")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ld_menu")],
    ])


def ld_joinmode_kb(current):
    modes = [("random", "رندوم — یه اکانت تصادفی"),
             ("split", "تقسیم — بین همه اکانت‌ها"),
             ("all", "همه به همه — همه اکانت‌ها جوین بشن")]
    buttons = []
    for key, label in modes:
        lbl = f"✅ {label}" if key == current else label
        buttons.append([InlineKeyboardButton(lbl,
                        callback_data=f"ld_joinmode_{key}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت",
                    callback_data="ld_settings")])
    return InlineKeyboardMarkup(buttons)


def ld_links_kb(count):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"👁 مشاهده لینک‌ها ({count} عدد)",
                              callback_data="ld_links_view")],
        [InlineKeyboardButton("🗑 حذف لینک‌ها",
                              callback_data="ld_links_clear")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="ld_menu")],
    ])

