import asyncio
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired
from database import q, u
from utils import get_user_client, ADMIN_ID

async def run():
    print("🤖 Secretary worker started")
    while True:
        try:
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
                    async for dlg in uc.get_dialogs():
                        if dlg is None or dlg.chat is None:
                            continue
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
                    await uc.stop()
                    u("UPDATE secretary SET replied_users=%s WHERE account_id=%s",
                      (",".join(replied), acc_id))
                except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
                    u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
                    print(f"[Secretary] اکانت {acc_id} منقضی شد - غیرفعال شد")
                    try:
                        await uc.stop()
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[Secretary] خطا در اکانت {acc_id}: {e}")
                    try:
                        await uc.stop()
                    except Exception:
                        pass
        except Exception as e:
            print(f"[Secretary] خطای کلی: {e}")
        await asyncio.sleep(1800)
