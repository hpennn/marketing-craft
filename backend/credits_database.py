"""
积分数据库模块 - 用户积分管理、订单、流水
使用与主数据库相同的 data/ai_staff.db 文件
"""

import os
import sqlite3
import time
from datetime import datetime
from typing import Optional, List

# 使用与主数据库相同的路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ai_staff.db")

# 新用户注册赠送积分
INITIAL_CREDITS = 3000


def _ensure_dir():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_credits_db() -> sqlite3.Connection:
    """获取数据库连接（与主数据库共享同一文件）"""
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_credits_db():
    """初始化积分相关表"""
    conn = get_credits_db()
    cursor = conn.cursor()

    # 用户积分表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_users (
            user_id TEXT PRIMARY KEY,
            credits INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # 订单表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            credits INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            package TEXT,
            created_at TEXT NOT NULL,
            paid_at TEXT
        )
    """)

    # 积分流水表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL DEFAULT 'consume',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# ============ 用户操作 ============

def register_user(user_id: str) -> dict:
    """注册新用户，赠送初始积分。如已存在则返回现有用户。"""
    conn = get_credits_db()
    now = datetime.now().isoformat()

    existing = conn.execute("SELECT * FROM credit_users WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        conn.close()
        return dict(existing)

    conn.execute(
        "INSERT INTO credit_users (user_id, credits, created_at) VALUES (?, ?, ?)",
        (user_id, INITIAL_CREDITS, now),
    )
    # 记录赠送流水
    conn.execute(
        "INSERT INTO credit_logs (user_id, amount, type, description, created_at) VALUES (?, ?, 'gift', ?, ?)",
        (user_id, INITIAL_CREDITS, f"新用户注册赠送{INITIAL_CREDITS}积分", now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM credit_users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row)


def get_user(user_id: str) -> Optional[dict]:
    """获取用户信息"""
    conn = get_credits_db()
    row = conn.execute("SELECT * FROM credit_users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_credits(user_id: str) -> int:
    """获取用户积分余额，不存在则返回0"""
    user = get_user(user_id)
    if not user:
        return 0
    return user.get("credits", 0)


def deduct_credits(user_id: str, amount: int, description: str = "") -> bool:
    """扣除积分，成功返回True，余额不足或用户不存在返回False"""
    conn = get_credits_db()
    now = datetime.now().isoformat()

    user = conn.execute("SELECT credits FROM credit_users WHERE user_id = ?", (user_id,)).fetchone()
    if not user or user["credits"] < amount:
        conn.close()
        return False

    conn.execute(
        "UPDATE credit_users SET credits = credits - ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.execute(
        "INSERT INTO credit_logs (user_id, amount, type, description, created_at) VALUES (?, ?, 'consume', ?, ?)",
        (user_id, -amount, description, now),
    )
    conn.commit()
    conn.close()
    return True


def add_credits(user_id: str, amount: int, credit_type: str = "recharge", description: str = "") -> bool:
    """增加积分"""
    conn = get_credits_db()
    now = datetime.now().isoformat()

    user = conn.execute("SELECT * FROM credit_users WHERE user_id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return False

    conn.execute(
        "UPDATE credit_users SET credits = credits + ? WHERE user_id = ?",
        (amount, user_id),
    )
    conn.execute(
        "INSERT INTO credit_logs (user_id, amount, type, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, credit_type, description, now),
    )
    conn.commit()
    conn.close()
    return True


# ============ 订单操作 ============

def create_order(order_id: str, user_id: str, amount: float, package: str, credits: int):
    """创建支付订单"""
    conn = get_credits_db()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO credit_orders (order_id, user_id, amount, credits, status, package, created_at) VALUES (?, ?, ?, ?, 'pending', ?, ?)",
        (order_id, user_id, amount, credits, package, now),
    )
    conn.commit()
    conn.close()


def update_order_status(order_id: str, status: str):
    """更新订单状态"""
    conn = get_credits_db()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE credit_orders SET status = ?, paid_at = ? WHERE order_id = ?",
        (status, now if status == "paid" else None, order_id),
    )
    conn.commit()
    conn.close()


def get_order(order_id: str) -> Optional[dict]:
    """获取订单信息"""
    conn = get_credits_db()
    row = conn.execute("SELECT * FROM credit_orders WHERE order_id = ?", (order_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ============ 流水查询 ============

def get_credit_logs(user_id: str = None, limit: int = 50) -> List[dict]:
    """获取积分流水"""
    conn = get_credits_db()
    if user_id:
        rows = conn.execute(
            "SELECT * FROM credit_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM credit_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 初始化
init_credits_db()
