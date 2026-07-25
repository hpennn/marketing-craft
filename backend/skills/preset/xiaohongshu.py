"""小红书种草文技能"""
import json
from ..llm_client import chat_completion

SKILL_META = {
    "id": "xiaohongshu",
    "name": "小红书种草文",
    "icon": "❤️",
    "description": "生成小红书风格种草文，吸睛标题+痛点+亮点+标签",
    "keywords": ["小红书", "种草", "笔记", "安利", "推荐"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    """
    输入: {"text": "产品描述"}
    输出: 小红书风格种草文
    """
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "小红书种草文生成器", "content": "请描述您的产品或服务，我将为您生成小红书风格的种草笔记。\n\n例如：一款保湿面霜，适合干皮，价格89元"}

    system = """你是一位资深小红书博主，擅长撰写种草笔记。你的内容特点：
1. 标题必须吸睛，包含emoji，让人忍不住点进来
2. 开头用痛点引入或惊喜发现，制造共鸣
3. 产品亮点用emoji分点展示，简洁有力
4. 使用体验要真实亲切，像闺蜜分享
5. 结尾给出购买建议和适合人群
6. 附上5-8个相关话题标签
7. 语气口语化、亲切、有感染力，多用emoji
8. 字数控制在300-500字
禁止包含任何域名链接。"""

    user = f"""请为以下产品写一篇小红书种草笔记：

{product}

请直接输出种草文内容，包含：
1. 吸睛标题（含emoji）
2. 正文内容（痛点→产品亮点→使用体验→购买建议）
3. 话题标签（#开头）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"❤️ **小红书种草文**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
