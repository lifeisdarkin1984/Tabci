import asyncio, time, random
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from database import q, u
from utils import get_user_client, ADMIN_ID, is_stopped


async def _send_banner(uc, chat_id, bt, bf, bft):
    if bf:
        if bft == "photo":
            await uc.send_photo(chat_id, bf, caption=bt)
        elif bft == "video":
            await uc.send_video(chat_id, bf, caption=bt)
        else:
            await uc.send_document(chat_id, bf, caption=bt)
    elif bt:
        await uc.send_message(chat_id, bt)


async def _run_for_target(target):
    """target = 'groups' یا 'pvs'"""
    now = int(time.time())
    row = q(
        "SELECT interval_minutes, last_run, last_index FROM global_scheduler "
        "WHERE admin_id=%s AND target=%s AND is_active=1",
        (ADMIN_ID, target)
    )
    if not row:
        return
    interval_min, last_run, last_index = row[0]
    if now - last_run < interval_min * 60:
        return

    banners = q(
        "SELECT slot, text, file_id, file_type FROM global_banners "
        "WHERE admin_id=%s AND target=%s ORDER BY slot",
        (ADMIN_ID, target)
    )
    if not banners:
        return

    # انتخاب پیام بعدی به ترتیب چرخشی (هر دوره یکی)
    idx = last_index % len(banners)
    _, bt, bf, bft = banners[idx]

    chat_type_filter = (
        (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)
        if target == "groups" else
        (enums.ChatType.PRIVATE,)
    )

    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
    for (acc_id,) in accs:
        if is_stopped():
            break
        uc = await get_user_client(acc_id)
        if not uc:
            continue
        try:
            await uc.start()
            async for dlg in uc.get_dialogs():
                if is_stopped():
                    break
                if dlg.chat.type not in chat_type_filter:
                    continue
                try:
                    await _send_banner(uc, dlg.chat.id, bt, bf, bft)
                    await asyncio.sleep(random.uniform(1, 2))
                except FloodWait as e:
                    await asyncio.sleep(min(e.value, 60))
                except Exception:
                    pass
            await uc.stop()
        except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
            u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
            try:
                await uc.stop()
            except Exception:
                pass
        except Exception as e:
            print(f"[GlobalScheduler:{target}] خطا در اکانت {acc_id}: {e}")
            try:
                await uc.stop()
            except Exception:
                pass

    u(
        "UPDATE global_scheduler SET last_run=%s, last_index=%s "
        "WHERE admin_id=%s AND target=%s",
        (now, idx + 1, ADMIN_ID, target)
    )


async def run():
    print("📨 Global scheduler worker started")
    while True:
        try:
            await _run_for_target("groups")
            await _run_for_target("pvs")
        except Exception as e:
            print(f"[GlobalScheduler] خطای کلی: {e}")
        await asyncio.sleep(60)
