import asyncio, random, time
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from database import q, u
from utils import get_user_client, ADMIN_ID

STOP_FLAG = False

async def run_once(acc_id, message_text, bot_client=None):
    uc = await get_user_client(acc_id)
    if not uc:
        return
    try:
        await uc.start()
        me = await uc.get_me()
        async for dlg in uc.get_dialogs():
            if STOP_FLAG:
                break
            if dlg.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                continue
            try:
                # گرفتن ۱۰ پیام آخر
                valid_msgs = []
                async for msg in uc.get_chat_history(dlg.chat.id, limit=10):
                    if STOP_FLAG:
                        break
                    # فیلتر ربات، ادمین، سرویس
                    if not msg.from_user:
                        continue
                    if msg.from_user.is_bot:
                        continue
                    if msg.service:
                        continue
                    # چک ادمین بودن
                    try:
                        member = await uc.get_chat_member(dlg.chat.id, msg.from_user.id)
                        if member.status in (enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER):
                            continue
                    except Exception:
                        pass
                    valid_msgs.append(msg)

                if not valid_msgs:
                    continue

                target = random.choice(valid_msgs)
                await uc.send_message(dlg.chat.id, message_text, reply_to_message_id=target.id)
                await asyncio.sleep(random.uniform(2, 5))

            except FloodWait as e:
                await asyncio.sleep(e.value * 2)
            except Exception:
                continue

        await uc.stop()
    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
        u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
        try:
            await uc.stop()
        except Exception:
            pass
    except Exception as e:
        print(f"[ReplyWorker] خطا در {acc_id}: {e}")
        try:
            await uc.stop()
        except Exception:
            pass

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
                "SELECT r.account_id, r.interval_minutes, r.last_run "
                "FROM reply_rand r "
                "JOIN accounts a ON r.account_id=a.id "
                "WHERE r.is_active=1 AND a.admin_id=%s AND a.status='active'",
                (ADMIN_ID,)
            )
            for (acc_id, interval_min, last_run) in jobs:
                if STOP_FLAG:
                    break
                if now - last_run < interval_min * 60:
                    continue
                msg_text = await _get_next_banner(acc_id)
                if not msg_text:
                    continue
                await run_once(acc_id, msg_text)
                u("UPDATE reply_rand SET last_run=%s WHERE account_id=%s", (now, acc_id))

            # ── تنظیمات همگانی (account_id='global') ──
            grow = q(
                "SELECT interval_minutes, last_run FROM reply_rand "
                "WHERE account_id='global' AND admin_id=%s AND is_active=1",
                (ADMIN_ID,)
            )
            if grow:
                interval_min, last_run = grow[0]
                if now - last_run >= interval_min * 60:
                    msg_text = await _get_next_banner("global")
                    if msg_text:
                        accs = q(
                            "SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
                            (ADMIN_ID,)
                        )
                        for (acc_id,) in accs:
                            if STOP_FLAG:
                                break
                            await run_once(acc_id, msg_text)
                        u("UPDATE reply_rand SET last_run=%s WHERE account_id='global' AND admin_id=%s",
                          (now, ADMIN_ID))

        except Exception as e:
            print(f"[ReplyWorker] خطای کلی: {e}")
        await asyncio.sleep(60)

