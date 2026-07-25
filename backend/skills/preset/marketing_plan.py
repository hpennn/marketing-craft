"""营销方案技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "marketing_plan",
    "name": "营销方案",
    "icon": "📊",
    "description": "生成完整营销方案，含市场分析、渠道策略、预算分配",
    "keywords": ["营销方案", "策划", "推广方案", "营销计划", "方案"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "营销方案生成器", "content": "请描述产品/品牌和目标。\n\n例如：新品牌上线，预算5万，目标3个月获取1万用户"}

    system = """你是一位资深营销策划专家，擅长制定可落地的营销方案。你的方案特点：
1. 市场分析简明扼要，抓住核心洞察
2. 目标人群画像具体可操作
3. 渠道策略有理有据，不贪多求全
4. 内容日历清晰可执行
5. 预算分配合理，标注ROI预期
6. KPI指标SMART化（具体可衡量可达成相关有时限）
7. 执行时间表精确到周
8. 包含风险预案
9. 方案可直接指导执行，不空泛
禁止包含任何域名链接。"""

    user = f"""请根据以下需求制定营销方案：

{product}

请按以下格式输出：
1. 项目概述（背景/目标/周期）
2. 市场分析（行业现状/竞品/机会点）
3. 目标人群画像（2-3个核心人群）
4. 营销策略（核心策略+渠道组合）
5. 内容规划（内容日历/各平台内容方向）
6. 预算分配（各渠道占比+金额）
7. KPI指标（各阶段目标值）
8. 执行时间表（按周排列）
9. 风险预案（可能的风险+应对措施）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"📊 **营销方案**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
