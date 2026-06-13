import asyncio, time
from pyrogram import enums
from pyrogram.errors import AuthKeyUnregistered, UserDeactivated, SessionExpired
from database import q, u
from utils import get_user_client, ADMIN_ID

async def run(bot_client):
    print("⏰ Global scheduler worker started")
    while True:
        try:
            now = int(time.time())
            jobs = q(
                "SELECT id, target, text, interval_minutes, last_run "
                "FROM global_schedule WHERE admin_id=%s AND is_active=1",
                (ADMIN_ID,)
            )
            for (job_id, target, text, interval_min, last_run) in jobs:
                if now - last_run < interval_min * 60:
                    continue
                if not text:
                    continue

                accs = q("SELECT id, phone FROM accounts WHERE admin_id=%s AND status='active'", (ADMIN_ID,))
                tot_ok = tot_left = tot_fail = 0

                for (acc_id, phone) in accs:
                    uc = await get_user_client(acc_id)
                    if not uc:
                        continue
                    try:
                        await uc.start()
                        if target == "pv":
                            async for dlg in uc.get_dialogs():
                                if dlg.chat.type != enums.ChatType.PRIVATE:
                                    continue
                                try:
                                    await uc.send_message(dlg.chat.id, text)
                                    tot_ok += 1
                                    await asyncio.sleep(2)
                                except Exception:
                                    tot_fail += 1
                        else:  # group
                            from pyrogram.errors import ChatWriteForbidden, ChatForbidden
                            async for dlg in uc.get_dialogs():
                                if dlg.chat.type not in (enums.ChatType.GROUP, enums.ChatType.SUPERGROUP):
                                    continue
                                try:
                                    await uc.send_message(dlg.chat.id, text)
                                    tot_ok += 1
                                    await asyncio.sleep(2)
                                except (ChatWriteForbidden, ChatForbidden):
                                    try:
                                        await uc.leave_chat(dlg.chat.id)
                                        tot_left += 1
                                    except Exception:
                                        tot_fail += 1
                                except Exception:
                                    tot_fail += 1
                        await uc.stop()
                    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
                        u("UPDATE accounts SET status='inactive' WHERE id=%s", (acc_id,))
                        print(f"[GlobalScheduler] اکانت {acc_id} منقضی شد - غیرفعال شد")
                        try:
                            await uc.stop()
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"[GlobalScheduler] خطا در اکانت {acc_id}: {e}")
                        try:
                            await uc.stop()
                        except Exception:
                            pass

                u("UPDATE global_schedule SET last_run=%s WHERE id=%s", (now, job_id))

                label = "پی‌وی‌ها" if target == "pv" else "گروه‌ها"
                report = f"⏰ **ارسال زمان‌بندی به {label} انجام شد**\n\n✔️ موفق: {tot_ok}\n❌ ناموفق: {tot_fail}"
                if target == "group":
                    report += f"\n🚫 محدود بود و خروج شد: {tot_left}"
                try:
                    await bot_client.send_message(ADMIN_ID, report)
                except Exception:
                    pass
        except Exception as e:
            print(f"[GlobalScheduler] خطای کلی: {e}")
        await asyncio.sleep(60)
