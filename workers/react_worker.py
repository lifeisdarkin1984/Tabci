import asyncio, random, time
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from database import q, u
from utils import get_user_client, ADMIN_ID

STOP_FLAG = False

FALLBACK_EMOJIS = ["👍", "❤️", "🔥", "🥰", "👏", "😁", "🎉", "🤩", "😍", "💯"]

async def get_available_reactions(uc, chat_id):
    try:
        chat = await uc.get_chat(chat_id)
        if hasattr(chat, 'available_reactions') and chat.available_reactions:
            return [r.emoji for r in chat.available_reactions if hasattr(r, 'emoji')]
    except Exception:
        pass
    return FALLBACK_EMOJIS

async def run_once(acc_id, group_tag_filter="ALL"):
    uc = await get_user_client(acc_id)
    if not uc:
        return

    # فیلتر گروه‌ها بر اساس برچسب
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
                reactions = await get_available_reactions(uc, dlg.chat.id)
                emoji = random.choice(reactions)
                await uc.send_reaction(dlg.chat.id, target.id, emoji)
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
        print(f"[ReactWorker] خطا در {acc_id}: {e}")
        try: await uc.stop()
        except Exception: pass

async def run():
    global STOP_FLAG
    print("😀 React worker started")
    while True:
        try:
            STOP_FLAG = False
            now = int(time.time())

            # ── تنظیمات تک‌اکانت ──
            jobs = q(
                "SELECT r.account_id, r.interval_minutes, r.last_run, "
                "r.group_tag_filter, r.acc_tag_filter "
                "FROM react_rand r "
                "JOIN accounts a ON r.account_id=a.id "
                "WHERE r.is_active=1 AND a.admin_id=%s AND a.status='active'",
                (ADMIN_ID,)
            )
            for (acc_id, interval_min, last_run, gtag, atag) in jobs:
                if STOP_FLAG:
                    break
                if now - last_run < interval_min * 60:
                    continue
                await run_once(acc_id, group_tag_filter=gtag or "ALL")
                u("UPDATE react_rand SET last_run=%s WHERE account_id=%s", (now, acc_id))

            # ── تنظیمات همگانی (هر لایه مستقل — account_id='global{layer_id}') ──
            grows = q(
                "SELECT account_id, interval_minutes, last_run, group_tag_filter, acc_tag_filter "
                "FROM react_rand "
                "WHERE admin_id=%s AND account_id LIKE 'global%%' AND is_active=1",
                (ADMIN_ID,)
            )
            for (gl_acc_id, interval_min, last_run, gtag, atag) in grows:
                if STOP_FLAG:
                    break
                if now - last_run < interval_min * 60:
                    continue
                try:
                    lyr_id = int(gl_acc_id[6:])
                except ValueError:
                    continue
                if atag and atag not in ("ALL", ""):
                    if atag == "NOTAG":
                        accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                                 "AND layer_id=%s AND (tag='' OR tag IS NULL)", (ADMIN_ID, lyr_id))
                    else:
                        accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                                 "AND layer_id=%s AND tag=%s", (ADMIN_ID, lyr_id, atag))
                else:
                    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' AND layer_id=%s",
                             (ADMIN_ID, lyr_id))
                for (acc_id,) in accs:
                    if STOP_FLAG:
                        break
                    await run_once(acc_id, group_tag_filter=gtag or "ALL")
                u("UPDATE react_rand SET last_run=%s WHERE account_id=%s AND admin_id=%s",
                  (now, gl_acc_id, ADMIN_ID))

        except Exception as e:
            print(f"[ReactWorker] خطای کلی: {e}")
        await asyncio.sleep(60)
