"""
订阅管理路由
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta
from database import get_db
from models import SubscriptionCreate, SubscriptionResponse, PaymentCallback
from routers.auth import get_current_admin
import time

router = APIRouter(tags=["subscription"])

# 定价方案
PLANS = {
    "free": {"name": "免费版", "price": 0, "conversations": 100, "staff_limit": 1, "features": ["100条对话/月", "1个客服员工", "基础功能"]},
    "basic": {"name": "基础版", "price": 29, "conversations": 1000, "staff_limit": 3, "features": ["1000条对话/月", "3个客服员工", "全部功能"]},
    "pro": {"name": "专业版", "price": 99, "conversations": -1, "staff_limit": -1, "features": ["无限对话", "无限客服员工", "全部功能", "优先支持"]},
    "enterprise": {"name": "企业版", "price": 299, "conversations": -1, "staff_limit": -1, "features": ["无限对话", "无限客服员工", "全部功能", "白标定制", "API接入", "专属支持"]},
}


@router.get("/plans")
async def get_plans():
    """获取所有定价方案"""
    return {"plans": PLANS}


@router.get("/subscription/current")
async def get_current_subscription(admin: dict = Depends(get_current_admin)):
    """获取当前订阅状态"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subscriptions ORDER BY id DESC LIMIT 1")
    sub = cursor.fetchone()

    if not sub:
        conn.close()
        return {
            "plan": "free", "plan_name": "免费版",
            "conversations_used": _get_monthly_conversations(cursor),
            "conversations_limit": 100, "staff_limit": 1,
            "expires_at": None, "status": "active"
        }

    expires_at = datetime.fromisoformat(sub["expires_at"]) if sub["expires_at"] else None
    status = "expired" if expires_at and expires_at < datetime.now(timezone.utc) else "active"
    conn.close()

    return {
        "plan": sub["plan"],
        "plan_name": PLANS.get(sub["plan"], {}).get("name", sub["plan"]),
        "conversations_used": _get_monthly_conversations(cursor),
        "conversations_limit": PLANS.get(sub["plan"], {}).get("conversations", -1),
        "staff_limit": PLANS.get(sub["plan"], {}).get("staff_limit", 1),
        "expires_at": sub["expires_at"], "status": status
    }


@router.get("/subscription/history")
async def get_subscription_history(admin: dict = Depends(get_current_admin)):
    """获取订阅历史记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.*, p.amount as payment_amount, p.status as payment_status
        FROM subscriptions s LEFT JOIN payments p ON p.subscription_id = s.id
        ORDER BY s.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return {"subscriptions": [dict(row) for row in rows]}


@router.post("/subscription/create-order")
async def create_subscription_order(data: SubscriptionCreate, admin: dict = Depends(get_current_admin)):
    """创建订阅订单（发起微信支付）"""
    plan = data.plan
    if plan not in PLANS:
        raise HTTPException(status_code=400, detail="无效的套餐")

    plan_info = PLANS[plan]
    amount_cents = plan_info["price"] * 100

    conn = get_db()
    cursor = conn.cursor()
    order_id = f"SUB{int(time.time())}{int(time.time()*1000) % 10000:04d}"

    cursor.execute("""
        INSERT INTO payments (order_id, plan, amount, status, created_at)
        VALUES (?, ?, ?, 'pending', datetime('now'))
    """, (order_id, plan, amount_cents))
    conn.commit()

    try:
        from payment_service import WechatPayService
        pay_service = WechatPayService()
        result = pay_service.create_native_order(
            description=f"AI客服员工 - {plan_info['name']}订阅",
            out_trade_no=order_id, amount=amount_cents, attach=plan
        )

        if "code_url" in result:
            cursor.execute("""
                UPDATE payments SET status='created', qr_code_path=? WHERE order_id=?
            """, (result.get("qr_code_path", ""), order_id))
            conn.commit()
            conn.close()
            return {"order_id": order_id, "code_url": result["code_url"],
                    "qr_code_path": result.get("qr_code_path", ""), "amount": amount_cents}
        else:
            conn.close()
            return {"error": "创建支付订单失败", "detail": result}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"支付服务错误: {str(e)}")


@router.post("/subscription/callback")
async def payment_callback(callback: PaymentCallback):
    """微信支付回调"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE order_id=?", (callback.out_trade_no,))
    payment = cursor.fetchone()

    if not payment:
        conn.close()
        raise HTTPException(status_code=404, detail="订单不存在")
    if payment["status"] == "paid":
        conn.close()
        return {"code": "SUCCESS", "message": "已处理"}

    cursor.execute("UPDATE payments SET status='paid', paid_at=datetime('now') WHERE order_id=?",
                   (callback.out_trade_no,))

    plan = payment["plan"]
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    cursor.execute("""
        INSERT INTO subscriptions (plan, amount, starts_at, expires_at, status, created_at)
        VALUES (?, ?, datetime('now'), ?, 'active', datetime('now'))
    """, (plan, payment["amount"], expires_at))

    conn.commit()
    conn.close()
    return {"code": "SUCCESS", "message": "支付成功"}


@router.post("/subscription/activate-free")
async def activate_free_plan(admin: dict = Depends(get_current_admin)):
    """激活免费版"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO subscriptions (plan, amount, starts_at, expires_at, status, created_at)
        VALUES ('free', 0, datetime('now'), NULL, 'active', datetime('now'))
    """)
    conn.commit()
    conn.close()
    return {"message": "免费版已激活"}


def _get_monthly_conversations(cursor) -> int:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE created_at >= ?", (month_start.isoformat(),))
    row = cursor.fetchone()
    return row["cnt"] if row else 0
