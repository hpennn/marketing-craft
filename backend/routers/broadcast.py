from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from database import get_db
from routers.auth import get_current_admin
import json

router = APIRouter()


class BroadcastCreate(BaseModel):
    staff_id: int
    message: str
    schedule_time: Optional[str] = None  # ISO format or null for immediate


@router.post("/broadcasts")
async def create_broadcast(broadcast: BroadcastCreate, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    # Verify staff belongs to this admin
    cursor.execute("SELECT * FROM staff WHERE id = ? AND admin_id = ?", (broadcast.staff_id, admin["admin_id"]))
    staff = cursor.fetchone()
    if not staff:
        conn.close()
        raise HTTPException(status_code=404, detail="员工不存在")

    status = "pending"
    cursor.execute(
        "INSERT INTO broadcasts (admin_id, staff_id, message, schedule_time, status) VALUES (?, ?, ?, ?, ?)",
        (admin["admin_id"], broadcast.staff_id, broadcast.message, broadcast.schedule_time, status)
    )
    conn.commit()
    broadcast_id = cursor.lastrowid

    cursor.execute("SELECT * FROM broadcasts WHERE id = ?", (broadcast_id,))
    new_broadcast = dict(cursor.fetchone())
    conn.close()

    return new_broadcast


@router.get("/broadcasts")
async def get_broadcasts(admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT b.*, s.name as staff_name, s.avatar_color
        FROM broadcasts b
        LEFT JOIN staff s ON b.staff_id = s.id
        WHERE b.admin_id = ?
        ORDER BY b.created_at DESC
    """, (admin["admin_id"],))
    broadcasts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return broadcasts


@router.delete("/broadcasts/{broadcast_id}")
async def delete_broadcast(broadcast_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM broadcasts WHERE id = ? AND admin_id = ?", (broadcast_id, admin["admin_id"]))
    broadcast = cursor.fetchone()
    if not broadcast:
        conn.close()
        raise HTTPException(status_code=404, detail="群发任务不存在")

    cursor.execute("DELETE FROM broadcasts WHERE id = ?", (broadcast_id,))
    conn.commit()
    conn.close()
    return {"message": "群发任务已删除"}


@router.post("/broadcasts/{broadcast_id}/execute")
async def execute_broadcast(broadcast_id: int, admin: dict = Depends(get_current_admin)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM broadcasts WHERE id = ? AND admin_id = ?", (broadcast_id, admin["admin_id"]))
    broadcast = cursor.fetchone()
    if not broadcast:
        conn.close()
        raise HTTPException(status_code=404, detail="群发任务不存在")

    broadcast_dict = dict(broadcast)

    if broadcast_dict["status"] == "completed":
        conn.close()
        raise HTTPException(status_code=400, detail="该群发任务已执行")

    # Find all conversations for this staff
    cursor.execute("SELECT * FROM conversation WHERE staff_id = ?", (broadcast_dict["staff_id"],))
    conversations = cursor.fetchall()

    sent_count = 0
    for conv in conversations:
        conv_dict = dict(conv)
        messages = json.loads(conv_dict.get("messages", "[]"))
        # Append broadcast message as assistant
        messages.append({
            "role": "assistant",
            "content": broadcast_dict["message"]
        })
        cursor.execute(
            "UPDATE conversation SET messages = ? WHERE id = ?",
            (json.dumps(messages, ensure_ascii=False), conv_dict["id"])
        )
        sent_count += 1

    # Update broadcast status
    cursor.execute("UPDATE broadcasts SET status = 'completed' WHERE id = ?", (broadcast_id,))
    conn.commit()
    conn.close()

    return {"message": f"群发已执行，共发送 {sent_count} 个会话", "sent_count": sent_count}
