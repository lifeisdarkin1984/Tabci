import asyncio, random, time
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from pyrogram.raw import functions, types
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

async def run_once(acc_id):
    uc = await get_user_client(acc_id)
    if not uc:
        return
    try:
        await uc.start()
        async for dlg in uc.get_dialogs():
            if STOP_FLAG:
                break
            if dlg.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                continue
            try:
                valid_msgs = []
                async for msg in uc.get_chat_history(dlg.chat.id, limit=10):
                    if STOP_FLAG:
                        break
                    if not msg.from_user:
                        continue
                    if msg.from_user.is_bot:
                        continue
                    if msg.service:
                        continue
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
                reactions = await get_available_reactions(uc, dlg.chat.id)
                emoji = random.choice(reactions)

                await uc.send_reaction(dlg.chat.id, target.id, emoji)
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
        print(f"[ReactWorker] خطا در {acc_id}: {e}")
        try:
            await uc.stop()
        except Exception:
            pass

async def run():
    global STOP_FLAG
    print("😀 React worker started")
    while True:
        try:
            STOP_FLAG = False
            now = int(time.time())

            # ── تنظیمات تک‌اکانت ──
            jobs = q(
                "SELECT r.account_id, r.interval_minutes, r.last_run "
                "FROM react_rand r "
                "JOIN accounts a ON r.account_id=a.id "
                "WHERE r.is_active=1 AND a.admin_id=%s AND a.status='active'",
                (ADMIN_ID,)
            )
            for (acc_id, interval_min, last_run) in jobs:
                if STOP_FLAG:
                    break
                if now - last_run < interval_min * 60:
                    continue
                await run_once(acc_id)
                u("UPDATE react_rand SET last_run=%s WHERE account_id=%s", (now, acc_id))

            # ── تنظیمات همگانی (account_id='global') ──
            grow = q(
                "SELECT interval_minutes, last_run FROM react_rand "
                "WHERE account_id='global' AND admin_id=%s AND is_active=1",
                (ADMIN_ID,)
            )
            if grow:
                interval_min, last_run = grow[0]
                if now - last_run >= interval_min * 60:
                    accs = q(
                        "SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
                        (ADMIN_ID,)
                    )
                    for (acc_id,) in accs:
                        if STOP_FLAG:
                            break
                        await run_once(acc_id)
                    u("UPDATE react_rand SET last_run=%s WHERE account_id='global' AND admin_id=%s",
                      (now, ADMIN_ID))

        except Exception as e:
            print(f"[ReactWorker] خطای کلی: {e}")
        await asyncio.sleep(60)
