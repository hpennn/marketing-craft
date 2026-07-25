"""社媒内容技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "social_media",
    "name": "社媒内容",
    "icon": "🔗",
    "description": "生成社交媒体帖子，适配微信公众号/微博/抖音等平台",
    "keywords": ["社媒", "社交", "微博", "公众号", "帖子"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "社媒内容生成器", "content": "请描述平台和主题。\n\n例如：微信公众号，分享行业趋势，专业风格"}

    system = """你是一位社交媒体运营专家，擅长为不同平台创作高互动内容。你的内容特点：
1. 标题吸引眼球，符合平台调性
2. 正文结构清晰，适合碎片化阅读
3. 话题标签精准有效
4. 给出最佳发布时间建议
5. 包含互动引导语（提问/投票/评论引导）
6. 适配不同平台风格差异：
   - 微信公众号：深度专业，长文
   - 微博：短平快，话题性强
   - 抖音/快手：口语化，节奏感
   - LinkedIn：专业商务范
7. 配图建议
禁止包含任何域名链接。"""

    user = f"""请根据以下需求创作社交媒体内容：

{product}

请按以下格式输出：
1. 标题/封面文字
2. 正文内容
3. 话题标签（5-8个）
4. 互动引导语
5. 发布时间建议
6. 配图/封面设计建议
7. 不同平台适配版本（至少2个平台）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"🔗 **社媒内容**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
