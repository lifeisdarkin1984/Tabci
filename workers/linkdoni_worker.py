import asyncio, re, random, hashlib
from pyrogram.errors import (FloodWait, AuthKeyUnregistered,
                              UserDeactivated, SessionExpired)
from database import q, u
from utils import get_user_client, ADMIN_ID

BOT_CLIENT = None

LINK_PATTERN = re.compile(r'https?://t\.me/[^\s\]\)"\']+')


def _normalize_link(link: str) -> str:
    link = link.strip().lower().split("?")[0].rstrip("/")
    return link


def _link_hash(link: str) -> str:
    return hashlib.sha256(_normalize_link(link).encode()).hexdigest()


def _get_settings():
    r = q("SELECT auto_scan, scan_interval_hours, auto_join, join_mode, "
          "join_tag, last_auto_scan FROM linkdoni_settings WHERE admin_id=%s",
          (ADMIN_ID,))
    if not r:
        u("INSERT IGNORE INTO linkdoni_settings (admin_id) VALUES (%s)",
          (ADMIN_ID,))
        return {"auto_scan": 0, "scan_interval_hours": 6, "auto_join": 0,
                "join_mode": "split", "join_tag": "", "last_auto_scan": None}
    return {"auto_scan": r[0][0], "scan_interval_hours": r[0][1],
            "auto_join": r[0][2], "join_mode": r[0][3],
            "join_tag": r[0][4] or "", "last_auto_scan": r[0][5]}


async def scan_linkdonis(triggered_by="auto"):
    """
    اسکن همه لینکدونی‌های فعال و استخراج لینک‌های جدید.
    triggered_by: "auto" یا "manual"
    برمی‌گردونه: (total_found, new_count, links_list)
    """
    sources = q("SELECT id, chat_id, chat_title, last_message_id "
                "FROM linkdoni_sources "
                "WHERE admin_id=%s AND is_active=1", (ADMIN_ID,))
    if not sources:
        return 0, 0, []

    # انتخاب یه اکانت رندوم برای اسکن
    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
             (ADMIN_ID,))
    if not accs:
        return 0, 0, []
    acc_id = str(random.choice(accs)[0])

    uc = await get_user_client(acc_id)
    if not uc:
        return 0, 0, []

    total_found = 0
    new_count = 0
    all_new_links = []

    try:
        await uc.start()

        for src_id, chat_id, chat_title, last_msg_id in sources:
            try:
                # تبدیل chat_id به عدد اگه ممکنه
                try:
                    target = int(chat_id)
                except ValueError:
                    target = chat_id

                new_last_id = last_msg_id
                batch_links = []

                # فقط پیام‌های جدیدتر از last_message_id بخون
                async for msg in uc.get_chat_history(target, limit=500):
                    if msg.id <= last_msg_id:
                        break
                    if msg.id > new_last_id:
                        new_last_id = msg.id

                    # استخراج لینک از متن، caption، entities، دکمه‌ها
                    texts = [msg.text or "", msg.caption or ""]
                    for e in (msg.entities or []) + (msg.caption_entities or []):
                        if hasattr(e, 'url') and e.url:
                            texts.append(e.url)
                    if msg.reply_markup:
                        try:
                            rows = getattr(msg.reply_markup,
                                           'inline_keyboard', None)
                            if rows:
                                for row in rows:
                                    for btn in row:
                                        if getattr(btn, 'url', None):
                                            texts.append(btn.url)
                        except Exception:
                            pass

                    for t in texts:
                        for lnk in LINK_PATTERN.findall(t):
                            lnk = lnk.rstrip('.,;:!?)\'"')
                            if 't.me/' in lnk:
                                batch_links.append(lnk)

                total_found += len(batch_links)

                # فیلتر تکراری با used_links و linkdoni_links
                for lnk in batch_links:
                    norm = _normalize_link(lnk)
                    h = _link_hash(lnk)

                    # چک used_links (قبلاً جوین شده)
                    r1 = q("SELECT 1 FROM used_links WHERE admin_id=%s "
                           "AND link_hash=%s", (ADMIN_ID, h))
                    if r1:
                        continue

                    # چک linkdoni_links (قبلاً دریافت شده)
                    r2 = q("SELECT 1 FROM linkdoni_links WHERE admin_id=%s "
                           "AND link_hash=%s", (ADMIN_ID, h))
                    if r2:
                        continue

                    # لینک جدیده — ذخیره کن
                    try:
                        u("INSERT IGNORE INTO linkdoni_links "
                          "(admin_id, link, link_hash, source_id) "
                          "VALUES (%s,%s,%s,%s)",
                          (ADMIN_ID, norm[:500], h, src_id))
                        all_new_links.append(norm)
                        new_count += 1
                    except Exception:
                        pass

                # آپدیت last_message_id و last_scan
                if new_last_id > last_msg_id:
                    u("UPDATE linkdoni_sources SET last_message_id=%s, "
                      "last_scan=NOW() WHERE id=%s",
                      (new_last_id, src_id))

                await asyncio.sleep(2)

            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as ex:
                print(f"[Linkdoni] خطا در اسکن {chat_id}: {ex}")
                continue

        await uc.stop()

    except (AuthKeyUnregistered, UserDeactivated, SessionExpired):
        print(f"[Linkdoni] اکانت {acc_id} منقضی.")
        try:
            await uc.stop()
        except Exception:
            pass
    except Exception as e:
        print(f"[Linkdoni] خطای کلی اسکن: {e}")
        try:
            await uc.stop()
        except Exception:
            pass

    return total_found, new_count, all_new_links


async def run():
    """حلقه اصلی اسکن خودکار"""
    await asyncio.sleep(15)
    while True:
        try:
            settings = _get_settings()
            if settings["auto_scan"]:
                from datetime import datetime, timedelta
                last = settings["last_auto_scan"]
                interval = settings["scan_interval_hours"]
                now = datetime.utcnow()
                should_scan = (
                    last is None or
                    (now - last) >= timedelta(hours=interval)
                )
                if should_scan:
                    u("UPDATE linkdoni_settings SET last_auto_scan=NOW() "
                      "WHERE admin_id=%s", (ADMIN_ID,))
                    total, new_count, links = await scan_linkdonis("auto")

                    # گزارش به ادمین — اسکن خودکار فقط گزارش می‌ده، جوین نمی‌کنه
                    if BOT_CLIENT:
                        try:
                            await BOT_CLIENT.send_message(
                                ADMIN_ID,
                                f"📡 **اسکن خودکار لینکدونی تمام شد**\n\n"
                                f"🔍 لینک‌های بررسی‌شده: {total}\n"
                                f"✅ لینک‌های جدید: {new_count}\n"
                                f"🔄 تکراری حذف‌شده: {total - new_count}\n\n"
                                f"برای جوین دستی: مدیریت همگانی → لینکدونی هوشمند"
                            )
                        except Exception as e:
                            print(f"[Linkdoni] خطا در ارسال گزارش: {e}")

        except Exception as e:
            print(f"[Linkdoni] خطا در run: {e}")
        await asyncio.sleep(300)


async def _do_join(links, settings):
    """جوین لینک‌ها بر اساس تنظیمات — فقط برای جوین دستی (manual)"""
    from handlers.text_handler import _join_links
    join_mode = settings["join_mode"]
    join_tag = settings["join_tag"]

    accs = q("SELECT id FROM accounts WHERE admin_id=%s AND status='active'",
             (ADMIN_ID,))
    if not accs:
        return

    mn_row = q("SELECT min_delay FROM join_settings WHERE admin_id=%s LIMIT 1",
               (ADMIN_ID,))
    mx_row = q("SELECT max_delay FROM join_settings WHERE admin_id=%s LIMIT 1",
               (ADMIN_ID,))
    min_d = mn_row[0][0] if mn_row else 5
    max_d = mx_row[0][0] if mx_row else 15

    if join_mode == "random":
        acc_id = str(random.choice(accs)[0])
        asyncio.create_task(
            _join_links(BOT_CLIENT, acc_id, links, min_d, max_d, join_tag)
        )

    elif join_mode == "split":
        chunk_size = max(1, len(links) // len(accs))
        for i, (acc_id,) in enumerate(accs):
            chunk = links[i * chunk_size: (i + 1) * chunk_size]
            if chunk:
                asyncio.create_task(
                    _join_links(BOT_CLIENT, str(acc_id),
                                chunk, min_d, max_d, join_tag)
                )

    elif join_mode == "all":
        for (acc_id,) in accs:
            asyncio.create_task(
                _join_links(BOT_CLIENT, str(acc_id),
                            links, min_d, max_d, join_tag)
            )

    # آپدیت وضعیت joined در linkdoni_links
    for lnk in links:
        h = _link_hash(lnk)
        u("UPDATE linkdoni_links SET joined=1 WHERE admin_id=%s AND link_hash=%s",
          (ADMIN_ID, h))
