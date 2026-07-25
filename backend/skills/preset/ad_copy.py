"""广告创意技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "ad_copy",
    "name": "广告创意",
    "icon": "📢",
    "description": "生成多版本广告文案，含主副标题、CTA、A/B测试建议",
    "keywords": ["广告", "ad", "创意", "banner", "投放"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "广告创意生成器", "content": "请描述产品和投放渠道。\n\n例如：电商Banner广告，突出限时折扣"}

    system = """你是一位资深广告创意总监，擅长撰写高转化率广告文案。你的文案特点：
1. 主标题+副标题组合，层次分明
2. 提供多个版本（长/中/短），适配不同场景
3. CTA按钮文案醒目有力，促进转化
4. 卖点提炼精准，直击用户痛点
5. 提供A/B测试建议，优化投放效果
6. 文案简洁有力，避免冗余
7. 适配不同渠道特点（信息流/搜索/展示/社交）
禁止包含任何域名链接。"""

    user = f"""请为以下需求创作广告创意文案：

{product}

请按以下格式输出：
1. 核心卖点提炼（3-5个）
2. 长版文案（完整描述，适合落地页/详情页）
3. 中版文案（精炼版，适合信息流广告）
4. 短版文案（一句话，适合Banner/标题）
5. CTA按钮文案（3-5个选项）
6. A/B测试建议（标题变体/角度建议）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"📢 **广告创意文案**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
