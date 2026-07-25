"""
积分系统API路由 - 虎皮椒支付集成
"""

import time
import hashlib
import uuid
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from credits_database import (
    register_user, get_user, get_user_credits,
    deduct_credits, add_credits,
    create_order, update_order_status, get_order,
    get_credit_logs,
)

router = APIRouter(tags=["credits"])

# ============ 虎皮椒支付配置 ============
XUNHU_APPID = "201906182239"
XUNHU_APPSECRET = "a03834403fd0101fb1c622545967b3db"
XUNHU_API = "https://api.xunhupay.com"

# ============ 积分包套餐配置 ============
CREDIT_PACKAGES = {
    "starter": {
        "price": 9.9,
        "credits": 30000,
        "label": "体验包",
        "desc": "30,000 积分，约1000次基础对话",
    },
    "basic": {
        "price": 29,
        "credits": 90000,
        "label": "基础包",
        "desc": "90,000 积分，约3000次基础对话",
    },
    "pro": {
        "price": 99,
        "credits": 300000,
        "label": "进阶包",
        "desc": "300,000 积分，约10000次基础对话",
    },
    "ultimate": {
        "price": 299,
        "credits": 900000,
        "label": "旗舰包",
        "desc": "900,000 积分，约30000次基础对话",
    },
}

# ============ 积分消耗配置 ============
CREDIT_COSTS = {
    "agent_chat_text": 30,    # 智能体对话（纯文字）
    "agent_chat_image": 50,   # 智能体对话（含图片）
    "skill_execute": 20,      # 技能执行
}


# ============ Models ============

class QueryCreditsRequest(BaseModel):
    user_id: str

class CreatePaymentRequest(BaseModel):
    user_id: str
    package: str  # "starter" | "basic" | "pro" | "ultimate"


# ============ Helpers ============

def _generate_order_id() -> str:
    ts = int(time.time() * 1000)
    rand = uuid.uuid4().hex[:8]
    return f"CRD{ts}{rand}"


def _sign_params(params: dict) -> str:
    """虎皮椒签名"""
    filtered = {k: v for k, v in params.items() if k != "hash" and v != "" and v is not None}
    sorted_keys = sorted(filtered.keys())
    raw = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)
    raw += XUNHU_APPSECRET
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _verify_notify_hash(params: dict) -> bool:
    """验证虎皮椒回调签名"""
    received_hash = params.get("hash", "")
    if not received_hash:
        return False
    filtered = {k: v for k, v in params.items() if k != "hash" and v != "" and v is not None}
    sorted_keys = sorted(filtered.keys())
    raw = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)
    raw += XUNHU_APPSECRET
    expected = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return received_hash == expected


# ============ Routes ============

@router.get("/credits/{user_id}")
async def query_credits(user_id: str, request: Request):
    """查询用户积分余额和套餐信息
    
    优先使用Token认证获取用户积分，user_id作为向后兼容的deviceId方案
    """
    # 尝试通过Token获取登录用户
    effective_user_id = user_id
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from auth_database import verify_token, find_user_by_device, bind_device
        user_info = verify_token(token)
        if user_info:
            token_user_id = f"user_{user_info['user_id']}"
            # 绑定当前deviceId到用户（如果不同）
            if user_id and user_id.startswith("dev_"):
                bind_device(user_info["user_id"], user_id)
            effective_user_id = token_user_id

    # 自动注册（确保用户存在）
    user = register_user(effective_user_id)
    credits = get_user_credits(effective_user_id)
    recent_logs = get_credit_logs(effective_user_id, limit=10)

    return {
        "user_id": effective_user_id,
        "credits": credits,
        "packages": {k: {"price": v["price"], "credits": v["credits"], "label": v["label"], "desc": v["desc"]} for k, v in CREDIT_PACKAGES.items()},
        "credit_costs": CREDIT_COSTS,
        "recent_logs": recent_logs,
    }


@router.post("/credits/recharge")
async def create_payment(req: CreatePaymentRequest, request: Request):
    """创建积分包购买订单（虎皮椒支付）"""
    if req.package not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="无效的套餐类型")

    # 优先使用Token认证
    effective_user_id = req.user_id
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from auth_database import verify_token
        user_info = verify_token(token)
        if user_info:
            effective_user_id = f"user_{user_info['user_id']}"

    # 确保用户已注册
    register_user(effective_user_id)

    pkg = CREDIT_PACKAGES[req.package]
    order_id = _generate_order_id()
    amount = pkg["price"]
    label = pkg["label"]
    credits = pkg["credits"]

    # 创建订单
    create_order(order_id, effective_user_id, amount, req.package, credits)

    # 构建虎皮椒支付参数
    nonce = str(int(time.time()))
    pay_params = {
        "version": "1.1",
        "appid": XUNHU_APPID,
        "trade_order_id": order_id,
        "total_fee": str(amount),
        "title": f"智能体工作台 - {label}",
        "body": f"智能体工作台 {label}，获得 {credits:,} 积分",
        "notify_url": "/api/credits/notify",
        "nonce_str": nonce,
        "time": nonce,
        "type": "WAP",
    }
    pay_params["hash"] = _sign_params(pay_params)

    try:
        resp = requests.post(
            f"{XUNHU_API}/payment/do.html",
            json=pay_params,
            timeout=10,
        )
        data = resp.json()
        if data.get("errcode") != 0:
            raise HTTPException(status_code=500, detail=f"支付创建失败: {data.get('errmsg', '未知错误')}")
        return {
            "order_id": order_id,
            "amount": amount,
            "package": req.package,
            "credits": credits,
            "pay_url": data.get("url", ""),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付服务异常: {str(e)}")


@router.post("/credits/notify")
async def payment_notify(request: Request):
    """虎皮椒支付回调 - 支付成功后加积分"""
    form = await request.form()
    params = dict(form)

    if not _verify_notify_hash(params):
        raise HTTPException(status_code=400, detail="签名验证失败")

    order_id = params.get("trade_order_id", "")
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if order["status"] == "paid":
        return {"errcode": 0, "errmsg": "success"}

    # 更新订单状态
    update_order_status(order_id, "paid")

    # 给用户加积分
    user_id = order["user_id"]
    credits_amount = order["credits"]
    package_id = order["package"]
    pkg = CREDIT_PACKAGES.get(package_id, {})
    label = pkg.get("label", package_id)

    add_credits(user_id, credits_amount, "recharge", f"购买{label}")

    return {"errcode": 0, "errmsg": "success"}


@router.get("/credits/check/{order_id}")
async def check_payment(order_id: str):
    """检查支付状态"""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return {
        "order_id": order_id,
        "status": order["status"],
        "package": order.get("package"),
        "amount": order["amount"],
        "credits": order.get("credits", 0),
    }


@router.get("/credits/packages")
async def get_packages():
    """获取积分包套餐列表"""
    return {
        "packages": CREDIT_PACKAGES,
        "credit_costs": CREDIT_COSTS,
    }


@router.post("/credits/deduct")
async def manual_deduct(request: Request):
    """内部接口：扣除积分（供其他路由调用）"""
    data = await request.json()
    user_id = data.get("user_id", "")
    amount = data.get("amount", 0)
    description = data.get("description", "")

    if not user_id or amount <= 0:
        raise HTTPException(status_code=400, detail="参数错误")

    # 确保用户已注册
    register_user(user_id)

    credits = get_user_credits(user_id)
    if credits < amount:
        return {"success": False, "remaining": credits, "required": amount}

    success = deduct_credits(user_id, amount, description)
    remaining = get_user_credits(user_id)
    return {"success": success, "remaining": remaining}
