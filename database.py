import mysql.connector, os
from dotenv import load_dotenv
load_dotenv()

def get_db():
    return mysql.connector.connect(
        host=os.environ["MYSQLHOST"],
        port=int(os.environ.get("MYSQLPORT", 3306)),
        user=os.environ["MYSQLUSER"],
        password=os.environ["MYSQLPASSWORD"],
        database=os.environ["MYSQLDATABASE"],
        autocommit=True,
        connection_timeout=10
    )

def q(sql, params=None):
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params or ())
    res = cur.fetchall()
    db.close()
    return res

def u(sql, params=None):
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, params or ())
    db.commit()
    db.close()

def init_db():
    db = get_db()
    cur = db.cursor()
    stmts = [
        """CREATE TABLE IF NOT EXISTS admins (
            id BIGINT PRIMARY KEY,
            step VARCHAR(150) DEFAULT 'idle',
            step_data MEDIUMTEXT
        )""",
        """CREATE TABLE IF NOT EXISTS accounts (
            id VARCHAR(50) PRIMARY KEY,
            phone VARCHAR(30),
            name VARCHAR(255),
            username VARCHAR(100) DEFAULT '',
            session_string MEDIUMTEXT,
            admin_id BIGINT,
            status VARCHAR(20) DEFAULT 'active',
            added_at BIGINT DEFAULT 0,
            auto_leave_limited TINYINT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS pending_logins (
            phone VARCHAR(30) PRIMARY KEY,
            admin_id BIGINT,
            phone_code_hash VARCHAR(300) DEFAULT '',
            created_at BIGINT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS banners (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id VARCHAR(50),
            admin_id BIGINT,
            slot INT DEFAULT 1,
            text MEDIUMTEXT,
            file_id VARCHAR(300) DEFAULT '',
            file_type VARCHAR(30) DEFAULT '',
            context VARCHAR(30) DEFAULT 'secretary',
            UNIQUE KEY uniq_banner (account_id, slot, context)
        )""",
        """CREATE TABLE IF NOT EXISTS scheduler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id VARCHAR(50),
            admin_id BIGINT,
            banner_text MEDIUMTEXT,
            banner_file_id VARCHAR(300) DEFAULT '',
            banner_file_type VARCHAR(30) DEFAULT '',
            interval_minutes INT DEFAULT 10,
            forward_from_chat VARCHAR(150) DEFAULT '',
            forward_msg_id BIGINT DEFAULT 0,
            mode VARCHAR(20) DEFAULT 'text',
            is_active TINYINT DEFAULT 0,
            last_run BIGINT DEFAULT 0,
            UNIQUE KEY uniq_acc (account_id, admin_id)
        )""",
        """CREATE TABLE IF NOT EXISTS secretary (
            account_id VARCHAR(50) PRIMARY KEY,
            admin_id BIGINT,
            is_active TINYINT DEFAULT 0,
            replied_users MEDIUMTEXT
        )""",
        """CREATE TABLE IF NOT EXISTS global_secretary_settings (
            admin_id BIGINT PRIMARY KEY,
            is_active TINYINT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS join_settings (
            account_id VARCHAR(50) PRIMARY KEY,
            admin_id BIGINT,
            min_delay INT DEFAULT 180,
            max_delay INT DEFAULT 420,
            force_join_active TINYINT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS reply_rand (
            account_id VARCHAR(50) PRIMARY KEY,
            admin_id BIGINT,
            message_text VARCHAR(2000) DEFAULT '',
            interval_minutes INT DEFAULT 30,
            is_active TINYINT DEFAULT 0,
            last_run BIGINT DEFAULT 0,
            last_index INT DEFAULT 0,
            group_tag_filter VARCHAR(100) DEFAULT 'ALL',
            acc_tag_filter VARCHAR(100) DEFAULT 'ALL'
        )""",
        """CREATE TABLE IF NOT EXISTS reply_rand_banners (
            id INT AUTO_INCREMENT PRIMARY KEY,
            account_id VARCHAR(50),
            admin_id BIGINT,
            slot INT DEFAULT 1,
            text MEDIUMTEXT,
            file_id VARCHAR(300) DEFAULT '',
            file_type VARCHAR(30) DEFAULT '',
            UNIQUE KEY uniq_slot (account_id, slot)
        )""",
        """CREATE TABLE IF NOT EXISTS react_rand (
            account_id VARCHAR(50) PRIMARY KEY,
            admin_id BIGINT,
            interval_minutes INT DEFAULT 30,
            is_active TINYINT DEFAULT 0,
            last_run BIGINT DEFAULT 0,
            group_tag_filter VARCHAR(100) DEFAULT 'ALL',
            acc_tag_filter VARCHAR(100) DEFAULT 'ALL'
        )""",
        """CREATE TABLE IF NOT EXISTS tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            name VARCHAR(100) NOT NULL,
            UNIQUE KEY uniq_tag (admin_id, name)
        )""",
        """CREATE TABLE IF NOT EXISTS group_tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            account_id VARCHAR(50),
            chat_id BIGINT,
            chat_title VARCHAR(255) DEFAULT '',
            tag_name VARCHAR(100) DEFAULT '',
            UNIQUE KEY uniq_group (admin_id, account_id, chat_id)
        )""",
        """CREATE TABLE IF NOT EXISTS account_tags (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            account_id VARCHAR(50),
            tag_name VARCHAR(100) DEFAULT '',
            UNIQUE KEY uniq_acctag (admin_id, account_id, tag_name)
        )""",
        """CREATE TABLE IF NOT EXISTS global_scheduler (
            admin_id BIGINT,
            target VARCHAR(10) NOT NULL,
            interval_minutes INT DEFAULT 60,
            is_active TINYINT DEFAULT 0,
            last_run BIGINT DEFAULT 0,
            last_index INT DEFAULT 0,
            group_tag_filter VARCHAR(100) DEFAULT 'ALL',
            acc_tag_filter VARCHAR(100) DEFAULT 'ALL',
            max_rounds INT DEFAULT 0,
            current_round INT DEFAULT 0,
            PRIMARY KEY (admin_id, target)
        )""",
        """CREATE TABLE IF NOT EXISTS global_banners (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            target VARCHAR(10) NOT NULL,
            slot INT DEFAULT 1,
            text MEDIUMTEXT,
            file_id VARCHAR(300) DEFAULT '',
            file_type VARCHAR(30) DEFAULT '',
            UNIQUE KEY uniq_slot (admin_id, target, slot)
        )""",
        """CREATE TABLE IF NOT EXISTS used_links (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            link_hash VARCHAR(64) NOT NULL,
            link_text VARCHAR(500) NOT NULL,
            used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_link (admin_id, link_hash)
        )""",
        """CREATE TABLE IF NOT EXISTS pv_links (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            link VARCHAR(500) NOT NULL,
            link_hash VARCHAR(64) NOT NULL,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_pv_link (admin_id, link_hash)
        )""",
        """CREATE TABLE IF NOT EXISTS pv_join_settings (
            admin_id BIGINT PRIMARY KEY,
            auto_scan TINYINT DEFAULT 0,
            scan_interval_hours INT DEFAULT 6,
            daily_limit INT DEFAULT 20,
            last_scan TIMESTAMP NULL
        )""",
        """CREATE TABLE IF NOT EXISTS linkdoni_sources (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            chat_id VARCHAR(100) NOT NULL,
            chat_title VARCHAR(200) DEFAULT '',
            source_link VARCHAR(300) DEFAULT '',
            last_message_id INT DEFAULT 0,
            last_scan TIMESTAMP NULL,
            is_active TINYINT DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uniq_source (admin_id, chat_id)
        )""",
        """CREATE TABLE IF NOT EXISTS linkdoni_links (
            id INT AUTO_INCREMENT PRIMARY KEY,
            admin_id BIGINT,
            link VARCHAR(500) NOT NULL,
            link_hash VARCHAR(64) NOT NULL,
            source_id INT,
            found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            joined TINYINT DEFAULT 0,
            UNIQUE KEY uniq_link (admin_id, link_hash)
        )""",
        """CREATE TABLE IF NOT EXISTS linkdoni_settings (
            admin_id BIGINT PRIMARY KEY,
            auto_scan TINYINT DEFAULT 0,
            scan_interval_hours INT DEFAULT 6,
            auto_join TINYINT DEFAULT 0,
            join_mode ENUM('random','split','all') DEFAULT 'split',
            join_tag VARCHAR(50) DEFAULT '',
            scan_account_mode ENUM('random') DEFAULT 'random',
            last_auto_scan TIMESTAMP NULL
        )""",
    ]
    for s in stmts:
        try:
            cur.execute(s)
        except Exception as e:
            print(f"[DB init] {e}")
    # اضافه کردن ستون‌های جدید اگه وجود ندارن (سازگار با همه نسخه‌های MySQL)
    def column_exists(table, column):
        try:
            cur.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
                (os.environ["MYSQLDATABASE"], table, column)
            )
            return cur.fetchone()[0] > 0
        except Exception:
            return True  # در صورت خطا فرض کن وجود دارد تا ALTER اجرا نشود

    new_columns = [
        ("accounts", "auto_leave_limited", "TINYINT DEFAULT 0"),
        ("accounts", "tag", "VARCHAR(100) DEFAULT ''"),
        ("reply_rand", "last_index", "INT DEFAULT 0"),
        ("reply_rand", "group_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("reply_rand", "acc_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("react_rand", "group_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("react_rand", "acc_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("global_scheduler", "group_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("global_scheduler", "acc_tag_filter", "VARCHAR(100) DEFAULT 'ALL'"),
        ("global_scheduler", "max_rounds", "INT DEFAULT 0"),
        ("global_scheduler", "current_round", "INT DEFAULT 0"),
        ("accounts", "last_sys_msg_id", "BIGINT DEFAULT 0"),
        ("linkdoni_sources", "source_link", "VARCHAR(300) DEFAULT ''"),
    ]
    for table, col, definition in new_columns:
        if not column_exists(table, col):
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
                print(f"[DB init] added column {col} to {table}")
            except Exception as e:
                print(f"[DB init] {e}")

    # تغییر نوع ستون‌های موجود
    try:
        cur.execute(
            "SELECT DATA_TYPE FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='admins' AND COLUMN_NAME='step_data'",
            (os.environ["MYSQLDATABASE"],)
        )
        row = cur.fetchone()
        if row and row[0].lower() == 'varchar':
            cur.execute("ALTER TABLE admins MODIFY COLUMN step_data MEDIUMTEXT")
            print("[DB init] upgraded step_data to MEDIUMTEXT")
    except Exception as e:
        print(f"[DB init] {e}")

    # ── پاکسازی رکوردهای تکراری در banners و اضافه کردن UNIQUE KEY ──
    try:
        # چک آیا UNIQUE KEY از قبل وجود داره
        cur.execute(
            "SELECT COUNT(*) FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA=%s AND TABLE_NAME='banners' AND INDEX_NAME='uniq_banner'",
            (os.environ["MYSQLDATABASE"],)
        )
        has_unique = cur.fetchone()[0] > 0
        if not has_unique:
            # حذف رکوردهای تکراری - فقط جدیدترین id برای هر (account_id, slot, context) نگه دار
            cur.execute("""
                DELETE b1 FROM banners b1
                INNER JOIN banners b2
                WHERE b1.account_id = b2.account_id
                AND b1.slot = b2.slot
                AND b1.context = b2.context
                AND b1.id < b2.id
            """)
            deleted = cur.rowcount
            # اضافه کردن UNIQUE KEY
            cur.execute("ALTER TABLE banners ADD UNIQUE KEY uniq_banner (account_id, slot, context)")
            print(f"[DB init] banners deduplicated ({deleted} removed) + UNIQUE KEY added")
    except Exception as e:
        print(f"[DB init] banners migration: {e}")

    db.commit()
    db.close()
    print("✅ DB ready")
