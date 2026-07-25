from fastapi import APIRouter, HTTPException, Request
from models import WebhookPayload
from agent_service import chat_with_ai
import json

router = APIRouter()


@router.post("/webhook")
async def webhook_handler(payload: WebhookPayload):
    try:
        result = await chat_with_ai(
            staff_id=payload.staff_id,
            session_id=payload.session_id,
            user_message=payload.message
        )
        return {
            "success": True,
            "platform": payload.platform,
            "reply": result["reply"],
            "conversation_id": result["conversation_id"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook处理失败: {str(e)}")


@router.post("/webhook/{platform}")
async def platform_webhook(platform: str, request: Request):
    """
    Generic webhook endpoint for different platforms.
    Platforms can send messages in their own format.
    This endpoint adapts to common webhook formats.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的JSON数据")

    # Try to extract message from common formats
    message = (
        body.get("message") or
        body.get("text") or
        body.get("content") or
        body.get("data", {}).get("message", "") or
        body.get("data", {}).get("text", "")
    )

    staff_id = body.get("staff_id")
    session_id = body.get("session_id", f"{platform}-default")

    if not message:
        raise HTTPException(status_code=400, detail="消息内容不能为空")

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_id不能为空")

    try:
        result = await chat_with_ai(
            staff_id=staff_id,
            session_id=session_id,
            user_message=message
        )
        return {
            "success": True,
            "platform": platform,
            "reply": result["reply"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook处理失败: {str(e)}")
