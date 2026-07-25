from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    staff_id: int
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    staff_id: int


class StaffCreate(BaseModel):
    name: str
    role_description: str
    knowledge_base: Optional[str] = ""
    avatar_color: Optional[str] = "#6366f1"
    platform: Optional[str] = "通用"


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role_description: Optional[str] = None
    knowledge_base: Optional[str] = None
    avatar_color: Optional[str] = None
    platform: Optional[str] = None
    welcome_message: Optional[str] = None
    transfer_keywords: Optional[str] = None
    sensitive_words: Optional[str] = None
    auto_reply_rules: Optional[str] = None
    transfer_message: Optional[str] = None
    shop_id: Optional[int] = None
    multilingual: Optional[int] = None


class StaffResponse(BaseModel):
    id: int
    name: str
    role_description: str
    knowledge_base: str
    avatar_color: str
    platform: Optional[str] = "通用"
    welcome_message: Optional[str] = ""
    transfer_keywords: Optional[str] = "[]"
    sensitive_words: Optional[str] = "[]"
    auto_reply_rules: Optional[str] = "[]"
    transfer_message: Optional[str] = "正在为您转接人工客服，请稍候..."
    shop_id: Optional[int] = None
    multilingual: Optional[int] = 0
    created_at: str


class ConversationResponse(BaseModel):
    id: int
    staff_id: int
    staff_name: Optional[str] = ""
    session_id: str
    last_message: Optional[str] = ""
    avatar_color: Optional[str] = "#6366f1"
    created_at: str


class ConversationDetailResponse(BaseModel):
    id: int
    staff_id: int
    session_id: str
    messages: list
    created_at: str


class SettingsUpdate(BaseModel):
    api_key: Optional[str] = None
    model_id: Optional[str] = None
    api_base_url: Optional[str] = None
    global_welcome: Optional[str] = None
    global_transfer_keywords: Optional[str] = None
    global_sensitive_words: Optional[str] = None


class SettingsResponse(BaseModel):
    api_key: str
    model_id: str
    api_base_url: str


class WebhookPayload(BaseModel):
    platform: str
    staff_id: int
    message: str
    session_id: Optional[str] = "webhook-default"


class SubscriptionCreate(BaseModel):
    plan: str  # free, basic, pro, enterprise


class SubscriptionResponse(BaseModel):
    id: Optional[int] = None
    plan: str
    plan_name: Optional[str] = ""
    conversations_used: Optional[int] = 0
    conversations_limit: Optional[int] = 100
    staff_limit: Optional[int] = 1
    expires_at: Optional[str] = None
    status: Optional[str] = "active"


class PaymentCallback(BaseModel):
    out_trade_no: str
    result_code: Optional[str] = "SUCCESS"
    total_fee: Optional[int] = None
