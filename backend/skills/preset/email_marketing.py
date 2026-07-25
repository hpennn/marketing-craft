"""邮件营销技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "email_marketing",
    "name": "邮件营销",
    "icon": "📧",
    "description": "生成营销邮件，含主题行、正文、CTA、P.S.",
    "keywords": ["邮件", "edm", "营销邮件", "email", "群发"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "邮件营销生成器", "content": "请描述营销目的。\n\n例如：新品发布通知，面向老客户，包含优惠码"}

    system = """你是一位邮件营销专家，擅长撰写高打开率、高转化率的营销邮件。你的邮件特点：
1. 主题行吸引打开（提供多个版本）
2. 预览文本精心设计，辅助主题行
3. 正文结构清晰：开场→价值→CTA
4. CTA按钮文案明确有力
5. P.S.追加关键信息（提升阅读率最高的区域）
6. 语气适配目标受众
7. 避免触发垃圾邮件过滤的写法
8. 包含个性化称呼建议
禁止包含任何域名链接。"""

    user = f"""请根据以下需求撰写营销邮件：

{product}

请按以下格式输出：
1. 邮件主题行（3-5个版本）
2. 预览文本
3. 邮件正文（含称呼/开场/核心内容/CTA/结尾）
4. CTA按钮文案（2-3个选项）
5. P.S.追加信息
6. 发送建议（最佳发送时间/注意事项）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"📧 **邮件营销**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
