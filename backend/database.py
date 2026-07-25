import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ai_staff.db")


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row["name"] for row in cursor.fetchall()]
    return column in columns


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            name TEXT NOT NULL,
            role_description TEXT NOT NULL,
            knowledge_base TEXT DEFAULT '[]',
            avatar_color TEXT DEFAULT '#6366f1',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            staff_id INTEGER NOT NULL,
            session_id TEXT NOT NULL,
            messages TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS webhook_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL,
            webhook_url TEXT NOT NULL,
            staff_id INTEGER NOT NULL,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(admin_id, key)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            phone TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            admin_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admin(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            platform TEXT NOT NULL,
            shop_name TEXT NOT NULL,
            shop_id TEXT NOT NULL,
            staff_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS platform_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            platform TEXT NOT NULL,
            config_json TEXT NOT NULL DEFAULT '{}',
            status TEXT DEFAULT '未配置',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(admin_id, platform)
        )
    """)

    # Subscription & payment tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan TEXT NOT NULL DEFAULT 'free',
            amount INTEGER DEFAULT 0,
            starts_at TEXT,
            expires_at TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            subscription_id INTEGER,
            plan TEXT NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            qr_code_path TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            FOREIGN KEY (subscription_id) REFERENCES subscriptions(id)
        )
    """)

    # Default settings (admin_id=0 as global defaults)
    cursor.execute("INSERT OR IGNORE INTO settings (admin_id, key, value) VALUES (0, 'api_key', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (admin_id, key, value) VALUES (0, 'model_id', 'ep-20260707225043-z7nkm')")
    cursor.execute("INSERT OR IGNORE INTO settings (admin_id, key, value) VALUES (0, 'api_base_url', 'https://ark.cn-beijing.volces.com/api/v3')")

    conn.commit()

    # Extend staff table with new columns
    new_columns = {
        "platform": "TEXT DEFAULT '通用'",
        "welcome_message": "TEXT DEFAULT ''",
        "transfer_keywords": "TEXT DEFAULT '[]'",
        "sensitive_words": "TEXT DEFAULT '[]'",
        "auto_reply_rules": "TEXT DEFAULT '[]'",
        "transfer_message": "TEXT DEFAULT '正在为您转接人工客服，请稍候...'",
        "shop_id": "INTEGER",
        "multilingual": "INTEGER DEFAULT 0",
    }
    for col, col_type in new_columns.items():
        if not _column_exists(cursor, "staff", col):
            cursor.execute(f"ALTER TABLE staff ADD COLUMN {col} {col_type}")

    # Phone verification codes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phone_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add rating column to conversation table
    if not _column_exists(cursor, "conversation", "rating"):
        cursor.execute("ALTER TABLE conversation ADD COLUMN rating TEXT DEFAULT ''")

    # Feature 5: Broadcasts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            staff_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            schedule_time TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)

    # Feature 7: Schedules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL DEFAULT 0,
            staff_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
