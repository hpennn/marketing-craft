"""统一LLM客户端 - 支持OpenAI兼容接口"""
import httpx
import os
import json
from typing import Optional

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
LLM_VL_MODEL = os.getenv("LLM_VL_MODEL", "qwen-vl-plus")

async def chat_completion(
    messages: list,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    response_format: Optional[dict] = None
) -> str:
    """调用LLM获取文本回复"""
    if not LLM_API_KEY:
        return "[LLM未配置] 请设置 LLM_API_KEY 环境变量"
    
    payload = {
        "model": model or LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format
    
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json=payload
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def vision_completion(
    image_url: str,
    prompt: str,
    model: Optional[str] = None
) -> str:
    """调用多模态LLM分析图片"""
    if not LLM_API_KEY:
        return "[LLM未配置] 请设置 LLM_API_KEY 环境变量"
    
    messages = [{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": prompt}
        ]
    }]
    
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={
                "model": model or LLM_VL_MODEL,
                "messages": messages,
                "max_tokens": 2000
            }
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def get_embedding(text: str, model: str = "text-embedding-v2") -> list:
    """获取文本embedding向量"""
    if not LLM_API_KEY:
        return [0.0] * 768
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{LLM_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json={"model": model, "input": text}
        )
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]
