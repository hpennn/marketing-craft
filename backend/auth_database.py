"""
用户认证数据库模块 - 用户名+邮箱+密码登录注册、JWT Token管理
与积分数据库共享同一 data/ai_staff.db 文件
"""

import os
import sqlite3
import secrets
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ai_staff.db")


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_auth_db() -> sqlite3.Connection:
    """获取数据库连接"""
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_auth_db():
    """初始化认证相关表"""
    conn = get_auth_db()
    cursor = conn.cursor()

    # 用户表（普通用户，与admin表区分）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nickname TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_login_at TEXT
        )
    """)

    # 迁移：旧版phone字段升级（如果存在旧表则添加新字段）
    try:
        cursor.execute("PRAGMA table_info(users)")
        columns = {row["name"] for row in cursor.fetchall()}
        if "phone" in columns and "username" not in columns:
            # 旧表需要迁移 - 添加新列
            cursor.execute("ALTER TABLE users ADD COLUMN username TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
            # 将 phone 值迁移到 username 作为默认值
            cursor.execute("UPDATE users SET username = phone WHERE username IS NULL")
            cursor.execute("UPDATE users SET email = phone || '@example.com' WHERE email IS NULL")
    except Exception:
        pass

    # 用户JWT Token表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # 用户-设备绑定表（用于积分迁移）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            bound_at TEXT NOT NULL,
            UNIQUE(user_id, device_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ============ 密码哈希 ============

def hash_password(password: str) -> str:
    """使用 sha256 + salt 进行密码哈希"""
    salt = "ai_staff_auth_salt_2026"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配"""
    return hash_password(password) == password_hash


# ============ 用户名/邮箱验证 ============

def validate_username(username: str) -> bool:
    """验证用户名格式：3-20位字母、数字、下划线"""
    return bool(re.match(r'^[a-zA-Z0-9_]{3,20}$', username))


def validate_email(email: str) -> bool:
    """验证邮箱格式"""
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """验证密码强度，返回 (valid, error_message)"""
    if len(password) < 6:
        return False, "密码长度至少6位"
    if len(password) > 128:
        return False, "密码长度不能超过128位"
    return True, ""


# ============ 用户操作 ============

def create_user(username: str, email: str, password: str) -> dict:
    """创建新用户
    Raises: ValueError if username or email already exists
    """
    conn = get_auth_db()
    now = datetime.now().isoformat()
    cursor = conn.cursor()

    # 检查用户名是否已存在
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cursor.fetchone():
        conn.close()
        raise ValueError("用户名已存在")

    # 检查邮箱是否已存在
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        raise ValueError("邮箱已被注册")

    # 创建用户
    password_hash = hash_password(password)
    nickname = username
    cursor.execute(
        "INSERT INTO users (username, email, password_hash, nickname, created_at, last_login_at) VALUES (?, ?, ?, ?, ?, ?)",
        (username, email, password_hash, nickname, now, now),
    )
    conn.commit()
    user_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def get_user_by_id(user_id: int) -> Optional[dict]:
    """通过ID获取用户"""
    conn = get_auth_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[dict]:
    """通过用户名获取用户"""
    conn = get_auth_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[dict]:
    """通过邮箱获取用户"""
    conn = get_auth_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_login(login: str) -> Optional[dict]:
    """通过用户名或邮箱获取用户（登录时使用）"""
    # 先尝试用户名
    user = get_user_by_username(login)
    if user:
        return user
    # 再尝试邮箱
    return get_user_by_email(login)


def update_last_login(user_id: int) -> None:
    """更新用户最后登录时间"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user_id))
    conn.commit()
    conn.close()


# ============ Token 操作 ============

def create_token(user_id: int) -> str:
    """创建用户Token"""
    token = secrets.token_hex(32)
    conn = get_auth_db()
    now = datetime.now().isoformat()
    # Token有效期30天
    expires = (datetime.now() + timedelta(days=30)).isoformat()
    conn.execute(
        "INSERT INTO user_tokens (user_id, token, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (user_id, token, now, expires),
    )
    conn.commit()
    conn.close()
    return token


def verify_token(token: str) -> Optional[dict]:
    """验证Token，返回用户信息或None"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.user_id, t.expires_at, u.username, u.email, u.nickname, u.created_at, u.last_login_at
        FROM user_tokens t
        JOIN users u ON t.user_id = u.id
        WHERE t.token = ?
    """, (token,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    # 检查是否过期
    if row["expires_at"] < now:
        # 清理过期token
        conn.execute("DELETE FROM user_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None

    result = dict(row)
    conn.close()
    return result


def delete_token(token: str) -> None:
    """删除Token（登出）"""
    conn = get_auth_db()
    conn.execute("DELETE FROM user_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def cleanup_expired_tokens() -> None:
    """清理过期Token"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM user_tokens WHERE expires_at < ?", (now,))
    conn.commit()
    conn.close()


# ============ 设备绑定操作 ============

def bind_device(user_id: int, device_id: str) -> None:
    """绑定设备到用户账号"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO user_devices (user_id, device_id, bound_at) VALUES (?, ?, ?)",
        (user_id, device_id, now),
    )
    conn.commit()
    conn.close()


def get_user_devices(user_id: int) -> list[str]:
    """获取用户绑定的所有设备ID"""
    conn = get_auth_db()
    rows = conn.execute(
        "SELECT device_id FROM user_devices WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()
    return [r["device_id"] for r in rows]


def find_user_by_device(device_id: str) -> Optional[dict]:
    """通过设备ID查找已绑定的用户"""
    conn = get_auth_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.* FROM users u
        JOIN user_devices ud ON u.id = ud.user_id
        WHERE ud.device_id = ?
        ORDER BY ud.bound_at DESC LIMIT 1
    """, (device_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# 初始化
init_auth_db()
