"""产品描述技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "product_desc",
    "name": "产品描述",
    "icon": "🏷️",
    "description": "生成电商产品描述，含卖点、参数、场景、FAQ",
    "keywords": ["产品", "商品", "描述", "详情页", "电商"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "产品描述生成器", "content": "请输入产品信息。\n\n例如：蓝牙耳机，降噪功能，续航30小时，价格299"}

    system = """你是一位电商运营专家，擅长撰写高转化率产品描述。你的描述特点：
1. 核心卖点突出，用数据说话
2. 规格参数清晰完整
3. 使用场景生动具体，帮助消费者代入
4. 模拟真实用户评价风格
5. 包含常见问题FAQ
6. 对比竞品优势（不点名竞品）
7. 适配淘宝/京东/拼多多等主流电商平台风格
8. 文案专业但不生硬，兼顾搜索和阅读体验
禁止包含任何域名链接。"""

    user = f"""请为以下产品撰写电商产品描述：

{product}

请按以下格式输出：
1. 产品标题（含核心关键词，适配电商搜索）
2. 核心卖点（3-5个，每个一句话）
3. 产品详细描述（功能/材质/设计亮点）
4. 规格参数表
5. 使用场景描述（3个场景）
6. 用户好评模拟（3条）
7. FAQ（3-5个常见问题）
8. 产品对比优势"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"🏷️ **产品描述**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
