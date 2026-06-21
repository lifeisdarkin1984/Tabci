import asyncio, random, time
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from database import q, u
from utils import get_user_client, ADMIN_ID

STOP_FLAG = False

async def run_once(acc_id, message_text, group_tag_filter="ALL"):
    uc = await get_user_client(acc_id)
    if not uc:
        return

    # گرفتن chat_id های مجاز بر اساس فیلتر
    allowed_chats = None
    exclude_chats = None
    if group_tag_filter not in ("ALL", ""):
        if group_tag_filter == "NOTAG":
            rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s "
                     "AND tag_name<>'' AND tag_name IS NOT NULL", (ADMIN_ID, acc_id))
            exclude_chats = set(r[0] for r in rows)
        else:
            rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s AND tag_name=%s",
                     (ADMIN_ID, acc_id, group_tag_filter))
            allowed_chats = set(r[0] for r in rows)
    try:
        await uc.start()

        dialogs = []
        async for dlg in uc.get_dialogs():
            if dlg.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                continue
            # اعمال فیلتر برچسب
            if allowed_chats is not None and dlg.chat.id not in allowed_chats:
                continue
            if exclude_chats is not None and dlg.chat.id in exclude_chats:
                continue
            dialogs.append(dlg)

        for dlg in dialogs:
            if STOP_FLAG:
                break
            try:
                valid_msgs = []
                async for msg in uc.get_chat_history(dlg.chat.id, limit=10):
                    if STOP_FLAG: break
                    if not msg.from_user: continue
                    if msg.from_user.is_bot: continue
                    if msg.service: continue
                    try:
                        member = await uc.get_chat_member(dlg.chat.id, msg.from_user.id)
                        if member.status in (enums.ChatMemberStatus.ADMINISTRATOR,
                                             enums.ChatMemberStatus.OWNER):
                            continue
                    except Exception:
                        pass
                    valid_msgs.append(msg)

                if not valid_msgs:
                    continue

                target = random.choice(valid_msgs)
                await uc.send_message(dlg.chat.id, message_text,
                                       reply_to_message_id=target.id)
                # فاصله تصادفی بین گروه‌ها
                await asyncio.sleep(random.uniform(3, 8))

            except FloodWait as e:
                # صبر می‌کنیم و گروه بعدی رو ادامه می‌دیم، اکانت رو کنار نمی‌ذاریم
                await asyncio.sleep(min(e.value, 120))
            except Exception:
                continue

        await uc.stop()
    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
        u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
        try: await uc.stop()
        except Exception: pass
    except Exception as e:
        print(f"[ReplyWorker] خطا در {acc_id}: {e}")
        try: await uc.stop()
        except Exception: pass

async def _get_next_banner(acc_id):
    """پیام بعدی را به ترتیب از جدول بنرها برمی‌گرداند"""
    bnrs = q("SELECT text FROM reply_rand_banners WHERE account_id=%s ORDER BY slot", (acc_id,))
    if not bnrs:
        # fallback به message_text قدیمی (برای سازگاری)
        row = q("SELECT message_text FROM reply_rand WHERE account_id=%s", (acc_id,))
        return row[0][0] if row and row[0][0] else None
    row = q("SELECT last_index FROM reply_rand WHERE account_id=%s", (acc_id,))
    idx = (row[0][0] if row else 0) % len(bnrs)
    msg_text = bnrs[idx][0]
    u("INSERT INTO reply_rand (account_id,admin_id,last_index) VALUES(%s,%s,%s) "
      "ON DUPLICATE KEY UPDATE last_index=%s",
      (acc_id, ADMIN_ID, idx+1, idx+1))
    return msg_text


async def run():
    global STOP_FLAG
    print("↩️ Reply worker started")
    while True:
        try:
            STOP_FLAG = False
            now = int(time.time())

            # ── تنظیمات تک‌اکانت ──
            jobs = q(
                "SELECT r.account_id, r.interval_minutes, r.last_run, "
                "r.group_tag_filter, r.acc_tag_filter "
                "FROM reply_rand r "
                "JOIN accounts a ON r.account_id=a.id "
                "WHERE r.is_active=1 AND a.admin_id=%s AND a.status='active'",
                (ADMIN_ID,)
            )
            for (acc_id, interval_min, last_run, gtag, atag) in jobs:
                if STOP_FLAG:
                    break
                if now - last_run < interval_min * 60:
                    continue
                msg_text = await _get_next_banner(acc_id)
                if not msg_text:
                    continue
                await run_once(acc_id, msg_text, group_tag_filter=gtag or "ALL")
                u("UPDATE reply_rand SET last_run=%s WHERE account_id=%s", (now, acc_id))

            # ── تنظیمات همگانی (account_id='global') ──
            grow = q(
                "SELECT interval_minutes, last_run, group_tag_filter, acc_tag_filter "
                "FROM reply_rand "
                "WHERE account_id='global' AND admin_id=%s AND is_active=1",
                (ADMIN_ID,)
            )
            if grow:
                interval_min, last_run, gtag, atag = grow[0]
                if now - last_run >= interval_min * 60:
                    msg_text = await _get_next_banner("global")
                    if msg_text:
                        # فیلتر اکانت‌ها
                        if atag and atag not in ("ALL", ""):
                            if atag == "NOTAG":
                                accs = q("SELECT id FROM accounts WHERE admin_id=%s "
                                         "AND status='active' AND (tag='' OR tag IS NULL)", (ADMIN_ID,))
                            else:
                                accs = q("SELECT id FROM accounts WHERE admin_id=%s "
                                         "AND status='active' AND tag=%s", (ADMIN_ID, atag))
                        else:
                            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
                                     (ADMIN_ID,))
                        for (acc_id,) in accs:
                            if STOP_FLAG:
                                break
                            await run_once(acc_id, msg_text, group_tag_filter=gtag or "ALL")
                        u("UPDATE reply_rand SET last_run=%s WHERE account_id='global' AND admin_id=%s",
                          (now, ADMIN_ID))

        except Exception as e:
            print(f"[ReplyWorker] خطای کلی: {e}")
        await asyncio.sleep(60)

