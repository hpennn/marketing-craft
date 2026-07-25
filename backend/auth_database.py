"""
用户认证数据库模块 - 手机号登录注册、JWT Token管理
与积分数据库共享同一 data/ai_staff.db 文件
"""

import os
import sqlite3
import secrets
import re
import random
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
            phone TEXT UNIQUE NOT NULL,
            nickname TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_login_at TEXT
        )
    """)

    # 验证码表（复用已有的phone_codes表，增加每日计数支持）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phone_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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


# ============ 手机号验证 ============

def validate_phone(phone: str) -> bool:
    """验证中国大陆手机号格式"""
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


def generate_code() -> str:
    """生成6位数字验证码"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


# ============ 验证码操作 ============

def save_verification_code(phone: str, code: str) -> None:
    """保存验证码，5分钟有效"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    expires = (datetime.now() + timedelta(minutes=5)).isoformat()
    conn.execute(
        "INSERT INTO phone_codes (phone, code, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (phone, code, expires, now),
    )
    conn.commit()
    conn.close()


def check_code_rate_limit(phone: str) -> tuple[bool, str]:
    """检查验证码发送频率限制
    - 60秒内不能重复发送
    - 每天最多10条
    返回 (allowed, error_message)
    """
    conn = get_auth_db()
    cursor = conn.cursor()
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # 检查最近一条的发送时间（60秒间隔）
    cursor.execute("""
        SELECT created_at FROM phone_codes
        WHERE phone = ? ORDER BY created_at DESC LIMIT 1
    """, (phone,))
    last = cursor.fetchone()
    if last:
        last_time = datetime.fromisoformat(last["created_at"])
        if (now - last_time).total_seconds() < 60:
            conn.close()
            return False, "验证码发送过于频繁，请60秒后重试"

    # 检查今日发送数量（每天最多10条）
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM phone_codes
        WHERE phone = ? AND created_at >= ?
    """, (phone, today_start))
    count = cursor.fetchone()["cnt"]
    if count >= 10:
        conn.close()
        return False, "今日验证码发送次数已达上限，请明天再试"

    conn.close()
    return True, ""


def verify_code(phone: str, code: str) -> bool:
    """验证验证码是否正确且未过期"""
    conn = get_auth_db()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("""
        SELECT id FROM phone_codes
        WHERE phone = ? AND code = ? AND expires_at > ?
        ORDER BY created_at DESC LIMIT 1
    """, (phone, code, now))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    # 验证码使用后删除，防止重放
    cursor.execute("DELETE FROM phone_codes WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()
    return True


# ============ 用户操作 ============

def create_or_get_user(phone: str) -> dict:
    """创建或获取用户（手机号登录时自动注册）"""
    conn = get_auth_db()
    now = datetime.now().isoformat()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE phone = ?", (phone,))
    user = cursor.fetchone()

    if user:
        # 更新最后登录时间
        conn.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (now, user["id"]))
        conn.commit()
        result = dict(user)
        result["last_login_at"] = now
        conn.close()
        return result

    # 新用户注册
    nickname = f"用户{phone[-4:]}"
    cursor.execute(
        "INSERT INTO users (phone, nickname, created_at, last_login_at) VALUES (?, ?, ?, ?)",
        (phone, nickname, now, now),
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


def get_user_by_phone(phone: str) -> Optional[dict]:
    """通过手机号获取用户"""
    conn = get_auth_db()
    row = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****1234"""
    if len(phone) == 11:
        return phone[:3] + "****" + phone[7:]
    return phone


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
        SELECT t.user_id, t.expires_at, u.phone, u.nickname, u.created_at, u.last_login_at
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
