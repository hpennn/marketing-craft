from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from models import ChatRequest, ChatResponse
from agent_service import chat_with_ai, check_transfer_keywords, check_auto_reply, filter_sensitive_words
import json

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        # Filter sensitive words from user message first
        filtered_message = filter_sensitive_words(request.staff_id, request.message)

        # Check transfer keywords
        transfer_result = check_transfer_keywords(request.staff_id, filtered_message)
        if transfer_result["should_transfer"]:
            return ChatResponse(
                reply=transfer_result["message"],
                session_id=request.session_id,
                staff_id=request.staff_id
            )

        # Check auto reply rules
        auto_reply = check_auto_reply(request.staff_id, filtered_message)
        if auto_reply["matched"]:
            # Still save to conversation
            from database import get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversation WHERE staff_id = ? AND session_id = ?",
                (request.staff_id, request.session_id)
            )
            conv = cursor.fetchone()
            if conv:
                messages = json.loads(conv["messages"])
                conv_id = conv["id"]
            else:
                messages = []
                # Get admin_id from staff record
                cursor.execute("SELECT admin_id FROM staff WHERE id = ?", (request.staff_id,))
                staff_row = cursor.fetchone()
                chat_admin_id = staff_row["admin_id"] if staff_row else 0
                cursor.execute(
                    "INSERT INTO conversation (admin_id, staff_id, session_id, messages) VALUES (?, ?, ?, ?)",
                    (chat_admin_id, request.staff_id, request.session_id, "[]")
                )
                conn.commit()
                conv_id = cursor.lastrowid

            messages.append({"role": "user", "content": filtered_message})
            messages.append({"role": "assistant", "content": auto_reply["reply"]})
            cursor.execute(
                "UPDATE conversation SET messages = ? WHERE id = ?",
                (json.dumps(messages, ensure_ascii=False), conv_id)
            )
            conn.commit()
            conn.close()

            return ChatResponse(
                reply=auto_reply["reply"],
                session_id=request.session_id,
                staff_id=request.staff_id
            )

        # Normal AI chat
        result = await chat_with_ai(
            staff_id=request.staff_id,
            session_id=request.session_id,
            user_message=filtered_message
        )

        # Filter sensitive words from AI reply
        filtered_reply = filter_sensitive_words(request.staff_id, result["reply"])

        return ChatResponse(
            reply=filtered_reply,
            session_id=result["session_id"],
            staff_id=result["staff_id"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天服务异常: {str(e)}")


class RateRequest(BaseModel):
    rating: str  # "good" or "bad"


@router.post("/rate/{session_id}")
async def rate_conversation(session_id: str, request: RateRequest):
    """Rate a conversation (good/bad)"""
    if request.rating not in ("good", "bad"):
        raise HTTPException(status_code=400, detail="rating must be 'good' or 'bad'")
    
    from database import get_db
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM conversation WHERE session_id = ?", (session_id,))
    conv = cursor.fetchone()
    if not conv:
        conn.close()
        raise HTTPException(status_code=404, detail="对话不存在")
    
    cursor.execute("UPDATE conversation SET rating = ? WHERE session_id = ?", (request.rating, session_id))
    conn.commit()
    conn.close()
    
    return {"message": "评价成功", "rating": request.rating}
