"""智能体对话API - 前端智能体直接调用LLM，支持图片上传，含积分检查"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import json
import uuid

from credits_database import register_user, get_user_credits, deduct_credits

router = APIRouter()

# 积分消耗配置
CREDIT_COST_TEXT = 30    # 纯文字对话
CREDIT_COST_IMAGE = 50   # 含图片对话


class AgentChatRequest(BaseModel):
    role: str
    custom_prompt: Optional[str] = ""
    messages: List[dict] = []
    session_id: Optional[str] = ""
    images: Optional[List[str]] = []  # base64 data URLs
    user_id: Optional[str] = ""  # 设备ID，用于积分检查


class AgentChatResponse(BaseModel):
    reply: str
    session_id: str
    remaining_credits: int = -1


@router.post("/agent-chat", response_model=AgentChatResponse)
async def agent_chat(request: AgentChatRequest, fastapi_request: Request = None):
    """智能体对话接口，支持多模态（图片+文字），含积分检查"""
    from skills.llm_client import chat_completion, vision_completion, LLM_VL_MODEL
    import httpx, os

    # 优先使用Token认证获取user_id
    effective_user_id = request.user_id
    if fastapi_request:
        auth_header = fastapi_request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            from auth_database import verify_token
            user_info = verify_token(token)
            if user_info:
                effective_user_id = f"user_{user_info['user_id']}"

    has_images = bool(request.images)

    # ===== 积分检查 =====
    remaining_credits = -1
    if effective_user_id:
        # 确保用户已注册
        register_user(effective_user_id)

        # 确定消耗积分数
        cost = CREDIT_COST_IMAGE if has_images else CREDIT_COST_TEXT
        credits = get_user_credits(effective_user_id)

        if credits < cost:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": "积分不足，请充值后继续使用",
                    "required": cost,
                    "remaining": credits,
                }
            )

    # Build system prompt
    system_prompt = f"你是一个专业的AI智能助手。\n\n你的角色定位：{request.role}"
    if request.custom_prompt:
        system_prompt += f"\n\n详细设定：{request.custom_prompt}"
    system_prompt += "\n\n请以这个角色身份回答用户问题，保持专业、友好。回答简洁实用，不要废话。支持Markdown格式。"
    if has_images:
        system_prompt += "\n\n用户发送了图片，请仔细分析图片内容并结合文字一起回答。"

    if has_images:
        # Multi-modal: use vision model
        # Build multi-modal messages
        api_messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous text messages as context
        for msg in request.messages[-10:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add the latest user message with images
        last_user_content = []
        # Add images
        for img_data_url in request.images:
            last_user_content.append({
                "type": "image_url",
                "image_url": {"url": img_data_url}
            })
        # Add text from last message if exists
        last_msg = request.messages[-1] if request.messages else None
        text_content = last_msg["content"] if (last_msg and last_msg.get("role") == "user") else "请分析这张图片"
        last_user_content.append({"type": "text", "text": text_content})
        
        api_messages.append({"role": "user", "content": last_user_content})

        try:
            LLM_API_KEY = os.getenv("LLM_API_KEY", "")
            LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            
            payload = {
                "model": LLM_VL_MODEL,
                "messages": api_messages,
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json=payload
                )
                resp.raise_for_status()
                reply = resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"抱歉，图片分析暂时不可用，请稍后再试。\n\n错误信息：{str(e)}"
    else:
        # Text-only: use regular model
        api_messages = [{"role": "system", "content": system_prompt}]
        for msg in request.messages[-20:]:
            api_messages.append({"role": msg["role"], "content": msg["content"]})

        try:
            reply = await chat_completion(
                messages=api_messages,
                temperature=0.7,
                max_tokens=1500
            )
        except Exception as e:
            reply = f"抱歉，AI服务暂时不可用，请稍后再试。\n\n错误信息：{str(e)}"

    session_id = request.session_id or str(uuid.uuid4())[:12]

    # ===== 对话成功后扣积分 =====
    if effective_user_id:
        cost = CREDIT_COST_IMAGE if has_images else CREDIT_COST_TEXT
        cost_desc = "智能体对话(含图片)" if has_images else "智能体对话(文字)"
        deduct_credits(effective_user_id, cost, cost_desc)
        remaining_credits = get_user_credits(effective_user_id)

    return AgentChatResponse(reply=reply, session_id=session_id, remaining_credits=remaining_credits)
