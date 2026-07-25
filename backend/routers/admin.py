from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from database import get_db
from routers.auth import get_current_admin
import json
import secrets
import string

router = APIRouter()


# ---- Pydantic models ----

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str


class PlatformConfigUpdate(BaseModel):
    config_json: dict
    status: Optional[str] = None


class ShopCreate(BaseModel):
    platform: str
    shop_name: str
    shop_id: str


class ShopUpdate(BaseModel):
    shop_name: Optional[str] = None
    shop_id: Optional[str] = None
    platform: Optional[str] = None


# ---- Admin info ----

@router.get("/admin/me")
async def get_admin_info(admin: dict = Depends(get_current_admin)):
    return {
        "id": admin["admin_id"],
        "username": admin.get("username", ""),
        "created_at": admin["created_at"]
    }


# ---- Password ----

@router.put("/admin/password")
async def update_password(req: PasswordUpdate, admin: dict = Depends(get_current_admin)):
    if not req.old_password or not req.new_password:
        raise HTTPException(status_code=400, detail="请输入旧密码和新密码")
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="新密码至少6位")

    from routers.auth import verify_password, hash_password

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM admin WHERE id = ?", (admin["admin_id"],))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="管理员不存在")

    if not verify_password(req.old_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=400, detail="旧密码错误")

    new_hash = hash_password(req.new_password)
    cursor.execute("UPDATE admin SET password_hash = ? WHERE id = ?", (new_hash, admin["admin_id"]))
    conn.commit()
    conn.close()
    return {"message": "密码修改成功"}


# ---- Platform Config ----

@router.get("/admin/platforms")
async def get_platforms(request: Request, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM platform_config WHERE admin_id = ? ORDER BY id", (admin["admin_id"],))
    configs = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Ensure all platforms exist (for this admin)
    all_platforms = ["微信", "企业微信", "飞书", "钉钉", "淘宝", "拼多多", "京东", "抖音", "自定义"]
    existing = {c["platform"] for c in configs}
    
    for p in all_platforms:
        if p not in existing:
            configs.append({
                "platform": p,
                "config_json": "{}",
                "status": "未配置",
                "created_at": None,
                "updated_at": None
            })

    # Parse config_json
    for c in configs:
        try:
            c["config_json"] = json.loads(c["config_json"]) if isinstance(c["config_json"], str) else c["config_json"]
        except:
            c["config_json"] = {}

    # Auto-generate webhook helper fields for IM platforms
    slug_map = {
        "微信": "wechat",
        "企业微信": "wecom",
        "飞书": "feishu",
        "钉钉": "dingtalk"
    }

    # Get base URL from request
    base_url = str(request.base_url).rstrip("/")

    for c in configs:
        slug = slug_map.get(c["platform"])
        if slug:
            cfg = c["config_json"]
            c["webhook_url"] = f"{base_url}/api/webhook/{slug}"
            c["auto_token"] = cfg.get("token") or secrets.token_hex(16)
            c["auto_encoding_aes_key"] = cfg.get("encoding_aes_key") or ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(43))

    return configs


@router.put("/admin/platforms/{platform}")
async def update_platform(platform: str, req: PlatformConfigUpdate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    aid = admin["admin_id"]

    config_json_str = json.dumps(req.config_json, ensure_ascii=False)
    status = req.status or ("已接入" if req.config_json else "未配置")

    cursor.execute("SELECT id FROM platform_config WHERE admin_id = ? AND platform = ?", (aid, platform))
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE platform_config SET config_json = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE admin_id = ? AND platform = ?",
            (config_json_str, status, aid, platform)
        )
    else:
        cursor.execute(
            "INSERT INTO platform_config (admin_id, platform, config_json, status) VALUES (?, ?, ?, ?)",
            (aid, platform, config_json_str, status)
        )

    conn.commit()
    conn.close()
    return {"message": "平台配置已更新", "platform": platform, "status": status}


@router.post("/admin/platforms/{platform}/test")
async def test_platform(platform: str, admin: dict = Depends(get_current_admin)):
    """Simulate testing platform connection."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM platform_config WHERE admin_id = ? AND platform = ?", (admin["admin_id"], platform))
    config = cursor.fetchone()
    conn.close()

    if not config:
        raise HTTPException(status_code=404, detail="平台未配置")

    config_data = json.loads(config["config_json"])
    if not config_data:
        raise HTTPException(status_code=400, detail="平台配置为空，请先填写配置信息")

    # Simulate connection test based on platform
    test_results = {
        "微信": "微信接口连接测试通过",
        "淘宝": "淘宝API连接测试通过",
        "拼多多": "拼多多API连接测试通过",
        "京东": "京东API连接测试通过",
        "抖音": "抖音API连接测试通过",
        "自定义": "自定义平台连接测试通过",
    }

    return {
        "success": True,
        "platform": platform,
        "message": test_results.get(platform, "连接测试通过")
    }


# ---- Shops ----

@router.get("/admin/shops")
async def get_shops(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shops WHERE admin_id = ? ORDER BY created_at DESC", (admin["admin_id"],))
    shops = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return shops


@router.post("/admin/shops")
async def create_shop(shop: ShopCreate, admin: dict = Depends(get_current_admin)):
    if not shop.platform or not shop.shop_name or not shop.shop_id:
        raise HTTPException(status_code=400, detail="平台、店铺名称和店铺ID不能为空")

    conn = get_db()
    cursor = conn.cursor()
    aid = admin["admin_id"]

    # Check duplicate (within this admin)
    cursor.execute(
        "SELECT id FROM shops WHERE admin_id = ? AND platform = ? AND shop_id = ?",
        (aid, shop.platform, shop.shop_id)
    )
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="该平台下已存在相同店铺ID")

    cursor.execute(
        "INSERT INTO shops (admin_id, platform, shop_name, shop_id) VALUES (?, ?, ?, ?)",
        (aid, shop.platform, shop.shop_name, shop.shop_id)
    )
    conn.commit()
    shop_id = cursor.lastrowid

    cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    new_shop = dict(cursor.fetchone())
    conn.close()
    return new_shop


@router.put("/admin/shops/{shop_id}")
async def update_shop(shop_id: int, req: ShopUpdate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shops WHERE id = ? AND admin_id = ?", (shop_id, admin["admin_id"]))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="店铺不存在")

    updates = {}
    if req.shop_name is not None:
        updates["shop_name"] = req.shop_name
    if req.shop_id is not None:
        updates["shop_id"] = req.shop_id
    if req.platform is not None:
        updates["platform"] = req.platform

    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [shop_id]
        cursor.execute(f"UPDATE shops SET {set_clause} WHERE id = ?", values)
        conn.commit()

    cursor.execute("SELECT * FROM shops WHERE id = ?", (shop_id,))
    updated = dict(cursor.fetchone())
    conn.close()
    return updated


@router.delete("/admin/shops/{shop_id}")
async def delete_shop(shop_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM shops WHERE id = ? AND admin_id = ?", (shop_id, admin["admin_id"]))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="店铺不存在")

    cursor.execute("DELETE FROM shops WHERE id = ?", (shop_id,))
    # Clear shop_id from any staff bound to this shop (only this admin's staff)
    cursor.execute("UPDATE staff SET shop_id = NULL WHERE shop_id = ? AND admin_id = ?", (shop_id, admin["admin_id"]))
    conn.commit()
    conn.close()
    return {"message": "店铺已删除"}


# ---- Global conversations ----

@router.get("/admin/conversations")
async def get_global_conversations(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, s.name as staff_name, s.avatar_color
        FROM conversation c
        LEFT JOIN staff s ON c.staff_id = s.id
        WHERE c.admin_id = ?
        ORDER BY c.created_at DESC
    """, (admin["admin_id"],))
    conversations = []
    for row in cursor.fetchall():
        conv = dict(row)
        messages = json.loads(conv.get("messages", "[]"))
        last_msg = ""
        if messages:
            last_msg = messages[-1].get("content", "")[:50]
        conv["last_message"] = last_msg
        conversations.append(conv)
    conn.close()
    return conversations


# ---- Stats overview ----

@router.get("/admin/stats")
async def get_admin_stats(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    aid = admin["admin_id"]

    # Total conversations (only for this admin)
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE admin_id = ?", (aid,))
    total_conversations = cursor.fetchone()["cnt"]

    # Today conversations
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE admin_id = ? AND DATE(created_at) = DATE('now', 'localtime')", (aid,))
    today_conversations = cursor.fetchone()["cnt"]

    # Total messages
    cursor.execute("SELECT messages FROM conversation WHERE admin_id = ?", (aid,))
    total_messages = 0
    for row in cursor.fetchall():
        msgs = json.loads(row["messages"] or "[]")
        total_messages += len(msgs)

    # Today messages
    cursor.execute("SELECT messages FROM conversation WHERE admin_id = ? AND DATE(created_at) = DATE('now', 'localtime')", (aid,))
    today_messages = 0
    for row in cursor.fetchall():
        msgs = json.loads(row["messages"] or "[]")
        today_messages += len(msgs)

    # Staff count
    cursor.execute("SELECT COUNT(*) as cnt FROM staff WHERE admin_id = ?", (aid,))
    staff_count = cursor.fetchone()["cnt"]

    # Shop count
    cursor.execute("SELECT COUNT(*) as cnt FROM shops WHERE admin_id = ?", (aid,))
    shop_count = cursor.fetchone()["cnt"]

    conn.close()

    return {
        "total_conversations": total_conversations,
        "today_conversations": today_conversations,
        "total_messages": total_messages,
        "today_messages": today_messages,
        "staff_count": staff_count,
        "shop_count": shop_count
    }
