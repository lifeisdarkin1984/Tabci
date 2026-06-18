import asyncio
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired
from database import q, u
from utils import get_user_client, ADMIN_ID

async def _reply_to_pvs(uc, acc_id, banners, replied):
    """ارسال بنرها به پیوی‌های جدید"""
    async for dlg in uc.get_dialogs():
        if dlg.chat.type != enums.ChatType.PRIVATE:
            continue
        uid = str(dlg.chat.id)
        if uid in replied:
            continue
        async for msg in uc.get_chat_history(dlg.chat.id, limit=1):
            if msg.from_user and str(msg.from_user.id) == uid:
                for b in banners:
                    txt, fid, ftype = b
                    try:
                        if fid:
                            if ftype == "photo":
                                await uc.send_photo(dlg.chat.id, fid, caption=txt)
                            elif ftype == "video":
                                await uc.send_video(dlg.chat.id, fid, caption=txt)
                            else:
                                await uc.send_document(dlg.chat.id, fid, caption=txt)
                        else:
                            await uc.send_message(dlg.chat.id, txt)
                        await asyncio.sleep(2)
                    except Exception:
                        pass
                replied.add(uid)
    return replied

async def run():
    print("🤖 Secretary worker started")
    while True:
        try:
            # ── منشی تک‌اکانت ──
            active = q(
                "SELECT s.account_id, s.replied_users "
                "FROM secretary s "
                "JOIN accounts a ON s.account_id=a.id "
                "WHERE s.is_active=1 AND a.admin_id=%s AND a.status='active'",
                (ADMIN_ID,)
            )
            for (acc_id, replied_raw) in active:
                replied = set(replied_raw.split(",")) if replied_raw else set()
                banners = q(
                    "SELECT text,file_id,file_type FROM banners "
                    "WHERE account_id=%s AND context='secretary' ORDER BY slot",
                    (acc_id,)
                )
                if not banners:
                    continue
                uc = await get_user_client(acc_id)
                if not uc:
                    continue
                try:
                    await uc.start()
                    replied = await _reply_to_pvs(uc, acc_id, banners, replied)
                    await uc.stop()
                    u("UPDATE secretary SET replied_users=%s WHERE account_id=%s",
                      (",".join(replied), acc_id))
                except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
                    u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
                    print(f"[Secretary] اکانت {acc_id} منقضی شد")
                    try: await uc.stop()
                    except Exception: pass
                except Exception as e:
                    print(f"[Secretary] خطا در {acc_id}: {e}")
                    try: await uc.stop()
                    except Exception: pass

            # ── منشی همگانی ──
            g_active = q(
                "SELECT COUNT(*) FROM secretary "
                "WHERE admin_id=%s AND is_active=1",
                (ADMIN_ID,)
            )
            if g_active and g_active[0][0] > 0:
                g_banners = q(
                    "SELECT text,file_id,file_type FROM banners "
                    "WHERE admin_id=%s AND context='g_secretary' ORDER BY slot",
                    (ADMIN_ID,)
                )
                if g_banners:
                    accs = q(
                        "SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
                        (ADMIN_ID,)
                    )
                    for (acc_id,) in accs:
                        # چک اگه این اکانت منشی تک‌اکانت داره، از اون استفاده نکن
                        has_own = q(
                            "SELECT COUNT(*) FROM secretary WHERE account_id=%s AND is_active=1",
                            (acc_id,)
                        )
                        if has_own and has_own[0][0] > 0:
                            continue
                        g_replied_row = q(
                            "SELECT replied_users FROM secretary "
                            "WHERE account_id=%s",
                            (f"g_{acc_id}",)
                        )
                        g_replied = set(g_replied_row[0][0].split(",")) if (g_replied_row and g_replied_row[0][0]) else set()
                        uc = await get_user_client(acc_id)
                        if not uc:
                            continue
                        try:
                            await uc.start()
                            g_replied = await _reply_to_pvs(uc, acc_id, g_banners, g_replied)
                            await uc.stop()
                            u("INSERT INTO secretary (account_id,admin_id,is_active,replied_users) "
                              "VALUES(%s,%s,0,%s) ON DUPLICATE KEY UPDATE replied_users=%s",
                              (f"g_{acc_id}", ADMIN_ID, ",".join(g_replied), ",".join(g_replied)))
                        except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
                            u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
                            try: await uc.stop()
                            except Exception: pass
                        except Exception as e:
                            print(f"[Secretary Global] خطا در {acc_id}: {e}")
                            try: await uc.stop()
                            except Exception: pass

        except Exception as e:
            print(f"[Secretary] خطای کلی: {e}")
        await asyncio.sleep(1800)

