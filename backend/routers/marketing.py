"""AI智能营销平台 - 文案/配图/视频生成路由"""
import os
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# ===== 豆包 API 配置 =====
ARK_API_KEY = os.getenv("ARK_API_KEY", "")
ARK_MODEL_ID = os.getenv("ARK_MODEL_ID", "")
ARK_ENDPOINT = os.getenv("ARK_ENDPOINT", "https://ark.cn-beijing.volces.com/api/v3")

# ===== 平台合规规则 =====
COMPLIANCE_RULE = '\n\n【合规要求】严禁在文案中出现任何域名（如xxx.com/xxx.cn）、URL链接、二维码、微信号等外部引流信息。如需引导用户了解产品，请用"搜索「产品名」即可找到"、"主页有链接"、"评论区告诉我"等话术代替。'

# ===== 平台 Prompt 配置（完整迁移自 smart-marketing）=====
PLATFORM_PROMPTS = {
    "xiaohongshu": {
        "system": "你是一位专业的小红书种草文案写手。风格真实、亲切、有感染力，像朋友分享好物。",
        "format": "输出格式：\n1. 标题（20字以内，吸引眼球）\n2. 正文（200-400字，分段，适当使用emoji）\n3. 话题标签（5-8个，#开头）\n\n要求：开头要有钩子吸引停留，中间突出使用场景和效果，结尾引导互动。"
    },
    "zhihu": {
        "system": "你是一位知乎内容创作者。风格专业、有深度、有理有据，用事实和逻辑说服读者。",
        "format": "输出格式：\n1. 标题（25字以内，引发好奇）\n2. 正文（500-800字，结构化论述）\n3. 总结建议\n\n要求：开头抛出核心观点或问题，中间用案例/数据支撑，结尾给出明确建议。语气专业但不枯燥。"
    },
    "wechat": {
        "system": "你是一位微信公众号内容编辑。风格通俗易懂、有温度、适合转发传播。",
        "format": "输出格式：\n1. 标题（22字以内，吸引点击）\n2. 摘要（50字以内）\n3. 正文（600-1000字，分段清晰，有小标题）\n\n要求：结构清晰，每段不超过4行。善用故事、对比、数据增强说服力。结尾引导关注或转发。"
    },
    "douyin": {
        "system": "你是一位抖音短视频脚本策划。风格生动、节奏快、视觉感强，能在3秒内抓住注意力。",
        "format": "输出格式：\n1. 视频标题（15字以内）\n2. 分镜脚本（3-5个场景，每个包含：画面描述 + 旁白/字幕 + 时长）\n3. 推荐BGM风格\n4. 话题标签（3-5个）\n\n要求：开头3秒必须有强钩子，整体节奏紧凑，结尾引导关注或评论。总时长控制在30-60秒。"
    },
    "bilibili": {
        "system": "你是一位B站UP主内容策划。风格有趣、有梗、接地气，能和观众产生共鸣。",
        "format": "输出格式：\n1. 视频标题（25字以内，可用【】标注分类）\n2. 视频简介（100字以内）\n3. 内容大纲（3-5个段落，每段说明讲什么）\n4. 弹幕互动引导（2-3个）\n5. 标签（5个以内）\n\n要求：标题要有梗或引发好奇，内容要有干货也有趣味，适当埋梗。"
    },
    "weibo": {
        "system": "你是一位微博运营达人。风格简洁有力、话题性强，善于制造讨论。",
        "format": "输出格式：\n1. 正文（140字以内，精炼有力）\n2. 话题标签（3-5个，#话题#格式）\n3. 配图建议（1-2张）\n\n要求：开头抓眼球，信息密度高，有观点或情绪价值，结尾引导转发或评论。"
    },
    "qywechat": {
        "system": "你是一位企业微信运营专家。风格专业可信、简洁高效，适合B端客户沟通。",
        "format": "输出格式：\n1. 推送标题（20字以内）\n2. 正文（300-500字，结构清晰）\n3. CTA（明确的行动引导）\n\n要求：突出产品价值和专业性，用数据说话，语气专业但亲和。适合企业内部或客户群发。"
    },
    "toutiao": {
        "system": "你是一位头条号内容创作者。风格通俗易懂、信息量大，善于抓住热点和用户兴趣。",
        "format": "输出格式：\n1. 标题（30字以内，三段式最佳）\n2. 封面描述建议\n3. 正文（800-1200字，段落短小）\n\n要求：标题信息量大、有悬念或数字，内容信息密度高，段落不超过3行。"
    },
    "jike": {
        "system": "你是一位即刻社区活跃用户。风格轻松随性、有态度、有品味，像朋友间闲聊。",
        "format": "输出格式：\n1. 正文（100-200字，自然随性）\n2. 话题标签（2-3个）\n\n要求：语气随意不做作，有个人态度和品味，像在朋友圈分享。"
    }
}

IMAGE_PROMPT_SYSTEM = """你是一位AI配图提示词专家。根据产品特点和推广内容，生成适合AI绘画工具（如Midjourney、DALL-E、Stable Diffusion、Flux等）的英文提示词。
输出格式：
1. 主图提示词（英文，50-80词，详细描述画面内容、风格、色调、构图）
2. 配图建议（中文，说明这张图适合用在什么位置）
要求：风格清新现代，适合社交媒体传播。避免文字、水印、logo。"""

VIDEO_SCRIPT_SYSTEM = """你是一位短视频脚本策划专家。根据产品信息生成适合AI视频生成工具（如豆包AI）和剪映后期制作的详细分镜脚本。
输出格式：
1. 视频主题（一句话概括）
2. 分镜列表（3-5个分镜），每个分镜包含：
   - 【画面提示词】详细的视觉描述，可直接作为豆包AI视频生成的输入提示词（中文描述，包含主体、场景、光影、色调、运镜方式）
   - 【时长】建议时长（秒）
   - 【旁白/字幕】配文或旁白文案
   - 【运镜】镜头运动建议（如推、拉、摇、移、跟、环绕等）
   - 【音效/BGM】音效或背景音乐建议
3. 豆包AI生成参数建议（画面比例、时长、风格关键词）
4. 剪映制作建议（转场效果、字幕样式、配乐节奏点等）

要求：画面提示词要具体生动、画面感强，可以直接复制到豆包AI视频生成功能中使用。包含场景、光线、色彩、构图、镜头运动等关键信息。"""


class MarketingRequest(BaseModel):
    type: str  # copy | batch | image | video
    product: str
    platforms: Optional[List[str]] = ["xiaohongshu"]
    extra: Optional[str] = ""


async def call_doubao(system_prompt: str, user_prompt: str) -> str:
    """调用豆包 API 生成内容"""
    if not ARK_API_KEY or not ARK_MODEL_ID:
        raise HTTPException(status_code=500, detail="API 配置缺失，请设置 ARK_API_KEY 和 ARK_MODEL_ID")

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{ARK_ENDPOINT}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ARK_API_KEY}",
            },
            json={
                "model": ARK_MODEL_ID,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
                "max_tokens": 2000,
            }
        )
        data = resp.json()
        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        raise Exception(data.get("error", {}).get("message", "API 调用失败"))


@router.post("/marketing/generate")
async def generate_marketing(req: MarketingRequest):
    """统一的营销内容生成接口"""
    results = {}
    user_prompt = f"产品信息：{req.product}\n"
    if req.extra:
        user_prompt += f"额外要求：{req.extra}"

    # 文案生成
    if req.type in ("copy", "batch"):
        selected = req.platforms or ["xiaohongshu"]
        copy_tasks = []
        for p in selected:
            config = PLATFORM_PROMPTS.get(p)
            if not config:
                copy_tasks.append({"platform": p, "content": "不支持的平台"})
                continue
            try:
                content = await call_doubao(
                    config["system"] + "\n\n" + config["format"] + COMPLIANCE_RULE,
                    user_prompt
                )
                copy_tasks.append({"platform": p, "content": content})
            except Exception as e:
                copy_tasks.append({"platform": p, "content": f"生成失败: {str(e)}"})
        results["copy"] = copy_tasks

    # 配图提示词
    if req.type == "image":
        try:
            img_prompt = f"产品/主题：{req.product}\n风格偏好：{req.extra or '现代清新，适合社交媒体'}"
            results["image"] = await call_doubao(IMAGE_PROMPT_SYSTEM, img_prompt)
        except Exception as e:
            results["image"] = f"生成失败: {str(e)}"

    # 视频脚本
    if req.type in ("video", "batch"):
        selected = req.platforms or ["xiaohongshu"]
        video_tasks = []
        for p in selected:
            platform_name = p
            try:
                vp = f"产品/主题：{req.product}\n目标平台：{platform_name}\n"
                if req.extra:
                    vp += f"额外要求：{req.extra}\n"
                vp += "视频时长：30-60秒"
                content = await call_doubao(VIDEO_SCRIPT_SYSTEM, vp)
                video_tasks.append({"platform": p, "content": content})
            except Exception as e:
                video_tasks.append({"platform": p, "content": f"生成失败: {str(e)}"})
        results["video"] = video_tasks

    return {"success": True, "results": results}
