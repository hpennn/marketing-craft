"""
认证路由 - 管理员认证 + 用户用户名/邮箱密码登录注册
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from database import get_db
import secrets
import re
import random
from datetime import datetime

# 用户认证模块
from auth_database import (
    validate_username, validate_email, validate_password_strength,
    create_user, get_user_by_id, get_user_by_login,
    verify_password, update_last_login,
    create_token, verify_token, delete_token, bind_device, find_user_by_device,
)

# 积分迁移
from credits_database import register_user, get_user_credits, add_credits, get_user

router = APIRouter()

# ---- Pydantic models ----

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    device_id: Optional[str] = ""


class LoginRequest(BaseModel):
    login: str  # 用户名或邮箱
    password: str
    device_id: Optional[str] = ""


class AuthResponse(BaseModel):
    token: str
    user: dict


class MeResponse(BaseModel):
    id: int
    username: str
    email: str
    created_at: str


# ---- Admin Auth dependency (保留原有) ----

async def get_current_admin(request: Request):
    """Extract and validate token from Authorization header (管理员)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = auth_header[7:]
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.token, s.admin_id, a.phone, a.created_at
        FROM sessions s
        JOIN admin a ON s.admin_id = a.id
        WHERE s.token = ?
    """, (token,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return dict(row)


# ---- User Auth dependency ----

async def get_current_user(request: Request):
    """获取当前登录用户（普通用户，用户名/邮箱+密码登录）"""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")

    token = auth_header[7:]
    user_info = verify_token(token)
    if not user_info:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    return user_info


# ---- 原有Admin Auth routes (保留) ----

class AuthStatusResponse(BaseModel):
    has_admin: bool

@router.get("/auth/status")
async def auth_status():
    """Check if admin exists (used by frontend to decide register vs login)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM admin")
    cnt = cursor.fetchone()["cnt"]
    conn.close()
    return {"has_admin": cnt > 0}


# ---- 原有Admin SMS utility ----

def _generate_code() -> str:
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def _validate_phone(phone: str) -> bool:
    return bool(re.match(r'^1[3-9]\d{9}$', phone))


# ---- 原有Admin send-code (保留) ----

class PhoneCodeRequest(BaseModel):
    phone: str

class PhoneLoginRequest(BaseModel):
    phone: str
    code: str


@router.post("/auth/admin-send-code")
async def admin_send_verification_code(req: PhoneCodeRequest):
    """管理员发送手机验证码"""
    phone = req.phone.strip()

    if not _validate_phone(phone):
        raise HTTPException(status_code=400, detail="请输入正确的手机号码")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT created_at FROM phone_codes 
        WHERE phone = ? ORDER BY created_at DESC LIMIT 1
    """, (phone,))
    last = cursor.fetchone()
    if last:
        last_time = datetime.fromisoformat(last["created_at"])
        if (datetime.now() - last_time).total_seconds() < 60:
            conn.close()
            raise HTTPException(status_code=429, detail="验证码发送过于频繁，请60秒后重试")

    code = _generate_code()
    cursor.execute("""
        INSERT INTO phone_codes (phone, code, expires_at)
        VALUES (?, ?, datetime('now', '+5 minutes'))
    """, (phone, code))
    conn.commit()
    conn.close()

    return {
        "message": "验证码已发送",
        "code": code,
        "expire_seconds": 300
    }


# ---- 原有Admin phone-login (保留) ----

@router.post("/auth/admin-login")
async def admin_phone_login(req: PhoneLoginRequest):
    """管理员手机号验证码登录"""
    phone = req.phone.strip()
    code = req.code.strip()

    if not _validate_phone(phone):
        raise HTTPException(status_code=400, detail="请输入正确的手机号码")
    if not code:
        raise HTTPException(status_code=400, detail="请输入验证码")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM phone_codes 
        WHERE phone = ? AND code = ? AND expires_at > datetime('now')
        ORDER BY created_at DESC LIMIT 1
    """, (phone, code))
    code_row = cursor.fetchone()

    if not code_row:
        conn.close()
        raise HTTPException(status_code=401, detail="验证码错误或已过期")

    cursor.execute("DELETE FROM phone_codes WHERE phone = ?", (phone,))

    cursor.execute("SELECT id, phone FROM admin WHERE phone = ?", (phone,))
    admin = cursor.fetchone()

    if not admin:
        cursor.execute("INSERT INTO admin (phone) VALUES (?)", (phone,))
        conn.commit()
        admin_id = cursor.lastrowid
    else:
        admin_id = admin["id"]

    token = secrets.token_hex(32)
    cursor.execute(
        "INSERT INTO sessions (token, admin_id) VALUES (?, ?)",
        (token, admin_id)
    )
    conn.commit()
    conn.close()

    return {"token": token, "phone": phone}


# ---- 原有Admin me/logout (保留) ----

@router.get("/auth/admin-me")
async def admin_me(admin: dict = Depends(get_current_admin)):
    """获取当前管理员信息"""
    return {
        "id": admin["admin_id"],
        "phone": admin["phone"],
        "created_at": admin["created_at"]
    }


@router.post("/auth/admin-logout")
async def admin_logout(request: Request):
    """管理员退出登录"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    return {"message": "已退出登录"}


# ============================================
# 用户注册 / 登录 API（用户名+邮箱+密码）
# ============================================

@router.post("/auth/register")
async def user_register(req: RegisterRequest):
    """用户注册
    - 验证用户名、邮箱、密码格式
    - 创建用户
    - 生成Token
    - 如果传了device_id，绑定设备并迁移积分
    """
    username = req.username.strip()
    email = req.email.strip()
    password = req.password

    # 验证用户名
    if not username:
        raise HTTPException(status_code=400, detail="请输入用户名")
    if not validate_username(username):
        raise HTTPException(status_code=400, detail="用户名格式不正确（3-20位字母、数字、下划线）")

    # 验证邮箱
    if not email:
        raise HTTPException(status_code=400, detail="请输入邮箱")
    if not validate_email(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")

    # 验证密码强度
    valid, error_msg = validate_password_strength(password)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # 创建用户
    try:
        user = create_user(username, email, password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 生成Token
    token = create_token(user["id"])

    # 注册积分系统（确保credit_users表中有此用户）
    user_credit_id = f"user_{user['id']}"
    register_user(user_credit_id)

    # 绑定设备 & 积分迁移
    migrated = False
    if req.device_id:
        bind_device(user["id"], req.device_id)
        migrated = _migrate_device_credits(req.device_id, user_credit_id)

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "nickname": user.get("nickname", ""),
        },
        "migrated": migrated,
    }


@router.post("/auth/login")
async def user_login(req: LoginRequest):
    """用户登录（用户名/邮箱 + 密码）

    - 支持用户名或邮箱登录
    - 验证密码
    - 生成Token
    - 如果传了device_id，绑定设备并迁移积分
    """
    login = req.login.strip()
    password = req.password

    if not login:
        raise HTTPException(status_code=400, detail="请输入用户名或邮箱")
    if not password:
        raise HTTPException(status_code=400, detail="请输入密码")

    # 查找用户（支持用户名或邮箱）
    user = get_user_by_login(login)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 更新最后登录时间
    update_last_login(user["id"])

    # 生成Token
    token = create_token(user["id"])

    # 注册积分系统（确保credit_users表中有此用户）
    user_credit_id = f"user_{user['id']}"
    register_user(user_credit_id)

    # 绑定设备 & 积分迁移
    migrated = False
    if req.device_id:
        bind_device(user["id"], req.device_id)
        migrated = _migrate_device_credits(req.device_id, user_credit_id)

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "nickname": user.get("nickname", ""),
        },
        "migrated": migrated,
    }


@router.get("/auth/me")
async def user_me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息"""
    user_id = user["user_id"]
    user_info = get_user_by_id(user_id)
    if not user_info:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 获取积分
    user_credit_id = f"user_{user_id}"
    credit_user = get_user(user_credit_id)
    credits = credit_user["credits"] if credit_user else 0

    return {
        "id": user_info["id"],
        "username": user_info["username"],
        "email": user_info["email"],
        "nickname": user_info.get("nickname", ""),
        "created_at": user_info["created_at"],
        "last_login_at": user_info.get("last_login_at", ""),
        "credits": credits,
    }


@router.post("/auth/logout")
async def user_logout(request: Request):
    """用户退出登录"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        delete_token(token)
    return {"message": "已退出登录"}


# ---- 积分迁移 ----

def _migrate_device_credits(device_id: str, user_credit_id: str) -> bool:
    """将deviceId的积分迁移到用户账号

    - 如果deviceId在credit_users表中有积分，且用户账号积分较少
    - 将deviceId的积分合并到用户账号
    - 返回是否发生了迁移
    """
    device_user = get_user(device_id)
    if not device_user or device_user["credits"] <= 0:
        return False

    user_data = get_user(user_credit_id)
    if not user_data:
        return False

    # 只有当设备积分 > 0 时才迁移
    device_credits = device_user["credits"]
    if device_credits <= 0:
        return False

    # 将设备积分加到用户账号
    add_credits(user_credit_id, device_credits, "merge", f"从设备{device_id[:8]}...迁移{device_credits}积分")

    # 将设备积分清零（防止重复迁移）
    from credits_database import get_credits_db
    conn = get_credits_db()
    now = datetime.now().isoformat()
    conn.execute("UPDATE credit_users SET credits = 0 WHERE user_id = ?", (device_id,))
    conn.execute(
        "INSERT INTO credit_logs (user_id, amount, type, description, created_at) VALUES (?, ?, ?, ?, ?)",
        (device_id, -device_credits, "merge", f"积分已迁移到账号{user_credit_id}", now),
    )
    conn.commit()
    conn.close()

    return True


# ---- 兼容：保留原有 phone-login 路由指向管理员登录 ----

@router.post("/auth/phone-login")
async def phone_login_compat(req: PhoneLoginRequest):
    """兼容旧版手机号登录（管理员）"""
    return await admin_phone_login(req)
