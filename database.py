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
            step_data VARCHAR(2000) DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS accounts (
            id VARCHAR(50) PRIMARY KEY,
            phone VARCHAR(30),
            name VARCHAR(255),
            username VARCHAR(100) DEFAULT '',
            session_string MEDIUMTEXT,
            admin_id BIGINT,
            status VARCHAR(20) DEFAULT 'active',
            added_at BIGINT DEFAULT 0
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
            context VARCHAR(30) DEFAULT 'secretary'
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
        """CREATE TABLE IF NOT EXISTS join_settings (
            account_id VARCHAR(50) PRIMARY KEY,
            admin_id BIGINT,
            min_delay INT DEFAULT 180,
            max_delay INT DEFAULT 420,
            force_join_active TINYINT DEFAULT 0
        )""",
    ]
    for s in stmts:
        cur.execute(s)
    db.commit()
    db.close()
    print("✅ DB ready")
