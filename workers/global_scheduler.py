import asyncio, time, random
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired, FloodWait
from database import q, u
from utils import get_user_client, ADMIN_ID, is_stopped, record_flood, is_in_cooldown, reset_flood


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
    """target = 'groups' ÛŒØ§ 'pvs'"""
    now = int(time.time())
    row = q(
        "SELECT interval_minutes, last_run, last_index, group_tag_filter, acc_tag_filter "
        "FROM global_scheduler "
        "WHERE admin_id=%s AND target=%s AND is_active=1",
        (ADMIN_ID, target)
    )
    if not row:
        return
    interval_min, last_run, last_index, gtag, atag = row[0]
    gtag = gtag or "ALL"
    atag = atag or "ALL"
    if now - last_run < interval_min * 60:
        return

    banners = q(
        "SELECT slot, text, file_id, file_type FROM global_banners "
        "WHERE admin_id=%s AND target=%s ORDER BY slot",
        (ADMIN_ID, target)
    )
    if not banners:
        return

    idx = last_index % len(banners)
    _, bt, bf, bft = banners[idx]

    chat_type_filter = (
        (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP)
        if target == "groups" else
        (enums.ChatType.PRIVATE,)
    )

    # ÙÛŒÙ„ØªØ± Ø§Ú©Ø§Ù†Øªâ€ŒÙ‡Ø§ Ø¨Ø± Ø§Ø³Ø§Ø³ Ø¨Ø±Ú†Ø³Ø¨
    if atag not in ("ALL", ""):
        if atag == "NOTAG":
            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' "
                     "AND (tag='' OR tag IS NULL)", (ADMIN_ID,))
        else:
            accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active' AND tag=%s",
                     (ADMIN_ID, atag))
    else:
        accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))

    for (acc_id,) in accs:
        if is_stopped():
            break
        if is_in_cooldown(acc_id):
            print(f"[GlobalScheduler:{target}] Ø§Ú©Ø§Ù†Øª {acc_id} Ø¯Ø± cooldownØŒ Ø±Ø¯ Ø´Ø¯")
            continue
        uc = await get_user_client(acc_id)
        if not uc:
            continue
        try:
            await uc.start()

            # ÙÛŒÙ„ØªØ± Ú¯Ø±ÙˆÙ‡â€ŒÙ‡Ø§ Ø¨Ø± Ø§Ø³Ø§Ø³ Ø¨Ø±Ú†Ø³Ø¨ (ÙÙ‚Ø· Ø¨Ø±Ø§ÛŒ groups)
            allowed_chats = None
            if target == "groups" and gtag not in ("ALL", ""):
                if gtag == "NOTAG":
                    rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s "
                             "AND (tag_name='' OR tag_name IS NULL)", (ADMIN_ID, acc_id))
                else:
                    rows = q("SELECT chat_id FROM group_tags WHERE admin_id=%s AND account_id=%s AND tag_name=%s",
                             (ADMIN_ID, acc_id, gtag))
                allowed_chats = set(r[0] for r in rows)

            # Ù…Ø±ØªØ¨â€ŒØ³Ø§Ø²ÛŒ â€” ÙØ¹Ø§Ù„â€ŒØªØ±ÛŒÙ† Ø§ÙˆÙ„
            dialogs = []
            async for dlg in uc.get_dialogs():
                if dlg.chat.type not in chat_type_filter:
                    continue
                if allowed_chats is not None and dlg.chat.id not in allowed_chats:
                    continue
                last_ts = dlg.top_message.date.timestamp() if dlg.top_message else 0
                dialogs.append((last_ts, dlg))
            dialogs.sort(key=lambda x: x[0], reverse=True)

            for _, dlg in dialogs:
                if is_stopped():
                    break
                try:
                    await _send_banner(uc, dlg.chat.id, bt, bf, bft)
                    reset_flood(acc_id)
                    await asyncio.sleep(random.uniform(1.5, 4))
                except FloodWait as e:
                    entered = record_flood(acc_id)
                    if entered:
                        break
                    await asyncio.sleep(min(e.value, 60))
                except Exception:
                    pass

            await uc.stop()
        except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
            u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
            try: await uc.stop()
            except Exception: pass
        except Exception as e:
            print(f"[GlobalScheduler:{target}] Ø®Ø·Ø§ Ø¯Ø± {acc_id}: {e}")
            try: await uc.stop()
            except Exception: pass

    u(
        "UPDATE global_scheduler SET last_run=%s, last_index=%s "
        "WHERE admin_id=%s AND target=%s",
        (now, idx + 1, ADMIN_ID, target)
    )


async def run():
    print("ðŸ“¨ Global scheduler worker started")
    while True:
        try:
            await _run_for_target("groups")
            await _run_for_target("pvs")
        except Exception as e:
            print(f"[GlobalScheduler] Ø®Ø·Ø§ÛŒ Ú©Ù„ÛŒ: {e}")
        await asyncio.sleep(60)
