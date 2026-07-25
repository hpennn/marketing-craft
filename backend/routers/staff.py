from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models import StaffCreate, StaffUpdate, SettingsUpdate
from routers.auth import get_current_admin
import json
import random

router = APIRouter()

AVATAR_COLORS = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e",
    "#f97316", "#eab308", "#22c55e", "#14b8a6",
    "#06b6d4", "#3b82f6", "#6366f1", "#a855f7"
]

INDUSTRY_TEMPLATES = [
    {
        "id": "ecommerce",
        "name": "电商客服",
        "icon": "🛍️",
        "role_description": "你是XX店铺的客服专员，负责回答商品咨询、订单查询、退换货等问题。语气亲切，称呼顾客为'亲'",
        "welcome_message": "亲，欢迎光临！有什么可以帮您的吗？😊",
        "transfer_keywords": ["投诉", "退款", "举报"]
    },
    {
        "id": "restaurant",
        "name": "餐饮客服",
        "icon": "🍽️",
        "role_description": "你是XX餐厅的客服，负责回答菜品推荐、预订座位、外卖配送等问题",
        "welcome_message": "您好！欢迎光临XX餐厅，请问有什么可以帮您？",
        "transfer_keywords": ["投诉", "食物中毒", "过敏"]
    },
    {
        "id": "education",
        "name": "教育培训",
        "icon": "📚",
        "role_description": "你是XX教育机构的课程顾问，负责解答课程咨询、报名流程、上课安排等问题",
        "welcome_message": "您好！欢迎来到XX教育，想了解一下哪方面的课程呢？",
        "transfer_keywords": ["退费", "投诉", "转班"]
    },
    {
        "id": "medical",
        "name": "医疗咨询",
        "icon": "🏥",
        "role_description": "你是XX健康平台的咨询助手，提供健康知识科普和就医指引，不做诊断和处方",
        "welcome_message": "您好！我是健康咨询助手，请问有什么健康问题想咨询？⚠️温馨提示：本服务不提供医疗诊断，如有紧急情况请拨打120",
        "transfer_keywords": ["急诊", "开药", "诊断"]
    },
    {
        "id": "legal",
        "name": "法律咨询",
        "icon": "⚖️",
        "role_description": "你是XX法律咨询平台的助手，提供法律知识普及和维权指引",
        "welcome_message": "您好！我是法律咨询助手，请问遇到了什么法律问题？",
        "transfer_keywords": ["委托", "起诉", "律师"]
    },
    {
        "id": "realestate",
        "name": "房产中介",
        "icon": "🏠",
        "role_description": "你是XX房产的置业顾问，负责房源推荐、看房预约、交易流程咨询",
        "welcome_message": "您好！我是XX房产置业顾问，请问您想了解哪里的房子？",
        "transfer_keywords": ["投诉", "退房", "维权"]
    },
    {
        "id": "travel",
        "name": "旅游客服",
        "icon": "✈️",
        "role_description": "你是XX旅行社的客服，负责旅游线路推荐、行程咨询、预订服务",
        "welcome_message": "您好！欢迎来到XX旅行社，想去哪里玩呢？😊",
        "transfer_keywords": ["投诉", "退票", "行程变更"]
    },
    {
        "id": "general",
        "name": "通用客服",
        "icon": "💬",
        "role_description": "你是一个专业的客服专员，负责回答用户的各类问题，提供耐心细致的服务",
        "welcome_message": "您好！请问有什么可以帮您？",
        "transfer_keywords": ["投诉", "经理"]
    }
]


@router.get("/templates")
async def get_templates():
    """获取行业模板列表"""
    return INDUSTRY_TEMPLATES




@router.get("/staff")
async def get_staff_list(admin_id: Optional[int] = Query(None)):
    """Public endpoint - no auth required. Supports optional admin_id filter."""
    conn = get_db()
    cursor = conn.cursor()
    if admin_id is not None:
        cursor.execute("SELECT * FROM staff WHERE admin_id = ? ORDER BY created_at DESC", (admin_id,))
    else:
        cursor.execute("SELECT * FROM staff ORDER BY created_at DESC")
    staff_list = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return staff_list


@router.post("/staff")
async def create_staff(staff: StaffCreate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    # Process knowledge base
    kb = staff.knowledge_base or ""
    if kb.strip():
        lines = [line.strip() for line in kb.strip().split("\n") if line.strip()]
        kb_json = json.dumps(lines, ensure_ascii=False)
    else:
        kb_json = "[]"

    avatar_color = staff.avatar_color or random.choice(AVATAR_COLORS)
    platform = staff.platform or "通用"

    cursor.execute(
        "INSERT INTO staff (admin_id, name, role_description, knowledge_base, avatar_color, platform) VALUES (?, ?, ?, ?, ?, ?)",
        (admin["admin_id"], staff.name, staff.role_description, kb_json, avatar_color, platform)
    )
    conn.commit()
    staff_id = cursor.lastrowid

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    new_staff = dict(cursor.fetchone())
    conn.close()

    return new_staff


@router.put("/staff/{staff_id}")
async def update_staff(staff_id: int, staff: StaffUpdate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ? AND admin_id = ?", (staff_id, admin["admin_id"]))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    existing_dict = dict(existing)

    # Build update fields
    updates = {}
    if staff.name is not None:
        updates["name"] = staff.name
    if staff.role_description is not None:
        updates["role_description"] = staff.role_description
    if staff.knowledge_base is not None:
        kb = staff.knowledge_base
        if kb.strip():
            lines = [line.strip() for line in kb.strip().split("\n") if line.strip()]
            updates["knowledge_base"] = json.dumps(lines, ensure_ascii=False)
        else:
            updates["knowledge_base"] = "[]"
    if staff.avatar_color is not None:
        updates["avatar_color"] = staff.avatar_color
    if staff.platform is not None:
        updates["platform"] = staff.platform
    if staff.welcome_message is not None:
        updates["welcome_message"] = staff.welcome_message
    if staff.transfer_keywords is not None:
        updates["transfer_keywords"] = staff.transfer_keywords
    if staff.sensitive_words is not None:
        updates["sensitive_words"] = staff.sensitive_words
    if staff.auto_reply_rules is not None:
        updates["auto_reply_rules"] = staff.auto_reply_rules
    if staff.transfer_message is not None:
        updates["transfer_message"] = staff.transfer_message
    if staff.multilingual is not None:
        updates["multilingual"] = staff.multilingual
    if staff.shop_id is not None:
        updates["shop_id"] = staff.shop_id

    if updates:
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [staff_id]
        cursor.execute(f"UPDATE staff SET {set_clause} WHERE id = ?", values)
        conn.commit()

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    updated_staff = dict(cursor.fetchone())
    conn.close()

    return updated_staff


@router.delete("/staff/{staff_id}")
async def delete_staff(staff_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM staff WHERE id = ? AND admin_id = ?", (staff_id, admin["admin_id"]))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    cursor.execute("DELETE FROM staff WHERE id = ?", (staff_id,))
    cursor.execute("DELETE FROM conversation WHERE staff_id = ?", (staff_id,))
    conn.commit()
    conn.close()
    return {"message": "员工已删除"}


@router.get("/staff/{staff_id}/stats")
async def get_staff_stats(staff_id: int):
    """Public endpoint - no auth required."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ?", (staff_id,))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    # Total conversations
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE staff_id = ?", (staff_id,))
    total_conversations = cursor.fetchone()["cnt"]

    # Today conversations
    cursor.execute("""
        SELECT COUNT(*) as cnt FROM conversation 
        WHERE staff_id = ? AND DATE(created_at) = DATE('now', 'localtime')
    """, (staff_id,))
    today_conversations = cursor.fetchone()["cnt"]

    # Total messages
    cursor.execute("SELECT messages FROM conversation WHERE staff_id = ?", (staff_id,))
    total_messages = 0
    for row in cursor.fetchall():
        msgs = json.loads(row["messages"] or "[]")
        total_messages += len(msgs)

    # Today messages
    cursor.execute("""
        SELECT messages FROM conversation 
        WHERE staff_id = ? AND DATE(created_at) = DATE('now', 'localtime')
    """, (staff_id,))
    today_messages = 0
    for row in cursor.fetchall():
        msgs = json.loads(row["messages"] or "[]")
        today_messages += len(msgs)

    # Satisfaction stats
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE staff_id = ? AND rating = 'good'", (staff_id,))
    good_count = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE staff_id = ? AND rating = 'bad'", (staff_id,))
    bad_count = cursor.fetchone()["cnt"]
    rated_count = good_count + bad_count
    satisfaction_rate = round(good_count / rated_count * 100, 1) if rated_count > 0 else 0

    conn.close()

    return {
        "staff_id": staff_id,
        "total_conversations": total_conversations,
        "today_conversations": today_conversations,
        "total_messages": total_messages,
        "today_messages": today_messages,
        "good_count": good_count,
        "bad_count": bad_count,
        "satisfaction_rate": satisfaction_rate
    }


@router.get("/stats/overview")
async def get_stats_overview(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    aid = admin["admin_id"]

    # Total conversations (only for this admin's staff)
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

    # Per-staff ranking (by total messages)
    cursor.execute("SELECT id, name, avatar_color FROM staff WHERE admin_id = ?", (aid,))
    staff_ranking = []
    for s in cursor.fetchall():
        s_dict = dict(s)
        cursor2 = conn.cursor()
        cursor2.execute("SELECT COUNT(*) as cnt FROM conversation WHERE staff_id = ?", (s_dict["id"],))
        conv_count = cursor2.fetchone()["cnt"]

        cursor2.execute("SELECT messages FROM conversation WHERE staff_id = ?", (s_dict["id"],))
        msg_count = 0
        for row in cursor2.fetchall():
            msgs = json.loads(row["messages"] or "[]")
            msg_count += len(msgs)

        staff_ranking.append({
            "id": s_dict["id"],
            "name": s_dict["name"],
            "avatar_color": s_dict["avatar_color"],
            "conversations": conv_count,
            "messages": msg_count
        })

    # Sort by messages descending
    staff_ranking.sort(key=lambda x: x["messages"], reverse=True)

    # Satisfaction stats
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE admin_id = ? AND rating = 'good'", (aid,))
    total_good = cursor.fetchone()["cnt"]
    cursor.execute("SELECT COUNT(*) as cnt FROM conversation WHERE admin_id = ? AND rating = 'bad'", (aid,))
    total_bad = cursor.fetchone()["cnt"]
    total_rated = total_good + total_bad
    total_satisfaction_rate = round(total_good / total_rated * 100, 1) if total_rated > 0 else 0

    conn.close()

    return {
        "total_conversations": total_conversations,
        "today_conversations": today_conversations,
        "total_messages": total_messages,
        "today_messages": today_messages,
        "staff_count": staff_count,
        "staff_ranking": staff_ranking,
        "good_count": total_good,
        "bad_count": total_bad,
        "satisfaction_rate": total_satisfaction_rate
    }


@router.get("/conversations")
async def get_conversations(admin: dict = Depends(get_current_admin)):
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


@router.get("/staff/{staff_id}/conversations")
async def get_staff_conversations(staff_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id = ? AND admin_id = ?", (staff_id, admin["admin_id"]))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    cursor.execute("""
        SELECT c.*, s.name as staff_name, s.avatar_color
        FROM conversation c
        LEFT JOIN staff s ON c.staff_id = s.id
        WHERE c.staff_id = ?
        ORDER BY c.created_at DESC
    """, (staff_id,))
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


@router.get("/conversations/{conv_id}")
async def get_conversation_detail(conv_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversation WHERE id = ? AND admin_id = ?", (conv_id, admin["admin_id"]))
    conv = cursor.fetchone()
    if not conv:
        conn.close()
        raise HTTPException(status_code=404, detail="对话不存在")

    conv_dict = dict(conv)
    conv_dict["messages"] = json.loads(conv_dict.get("messages", "[]"))
    conn.close()
    return conv_dict


@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM conversation WHERE id = ? AND admin_id = ?", (conv_id, admin["admin_id"]))
    conv = cursor.fetchone()
    if not conv:
        conn.close()
        raise HTTPException(status_code=404, detail="对话不存在")

    cursor.execute("DELETE FROM conversation WHERE id = ?", (conv_id,))
    conn.commit()
    conn.close()
    return {"message": "对话已删除"}


@router.get("/settings")
async def get_settings(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings WHERE admin_id = ?", (admin["admin_id"],))
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    return {
        "api_key": settings.get("api_key", ""),
        "model_id": settings.get("model_id", ""),
        "api_base_url": settings.get("api_base_url", ""),
        "global_welcome": settings.get("global_welcome", ""),
        "global_transfer_keywords": settings.get("global_transfer_keywords", "[]"),
        "global_sensitive_words": settings.get("global_sensitive_words", "[]")
    }


@router.put("/settings")
async def update_settings(settings: SettingsUpdate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    aid = admin["admin_id"]

    if settings.api_key is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'api_key', ?)",
            (aid, settings.api_key)
        )
    if settings.model_id is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'model_id', ?)",
            (aid, settings.model_id)
        )
    if settings.api_base_url is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'api_base_url', ?)",
            (aid, settings.api_base_url)
        )
    if settings.global_welcome is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'global_welcome', ?)",
            (aid, settings.global_welcome)
        )
    if settings.global_transfer_keywords is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'global_transfer_keywords', ?)",
            (aid, settings.global_transfer_keywords)
        )
    if settings.global_sensitive_words is not None:
        cursor.execute(
            "INSERT OR REPLACE INTO settings (admin_id, key, value) VALUES (?, 'global_sensitive_words', ?)",
            (aid, settings.global_sensitive_words)
        )

    conn.commit()
    conn.close()
    return {"message": "设置已更新"}
