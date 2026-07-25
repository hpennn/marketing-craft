"""SEO优化文章技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "seo_article",
    "name": "SEO优化文章",
    "icon": "🔍",
    "description": "生成SEO优化文章，含标题结构、关键词布局、meta建议",
    "keywords": ["seo", "搜索引擎", "优化文章", "关键词", "排名"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "SEO优化文章生成器", "content": "请输入关键词和主题。\n\n例如：关键词'保湿面霜推荐'，写一篇1500字测评"}

    system = """你是一位SEO内容专家，擅长撰写搜索引擎优化文章。你的文章特点：
1. 标题包含核心关键词，吸引点击（H1）
2. 使用清晰的H2/H3标题层级结构
3. 关键词自然分布，密度2-3%，不堆砌
4. 开头100字内出现核心关键词
5. 包含meta description建议（150-160字符）
6. 内容有价值、有深度，满足搜索意图
7. 包含FAQ段落（覆盖长尾关键词）
8. 适当建议内链位置
9. 段落简短，可读性强
10. 符合搜索引擎最新优化规范
禁止包含任何域名链接。"""

    user = f"""请根据以下需求撰写一篇SEO优化文章：

{product}

请按以下格式输出：
1. Meta信息（title标签、meta description、建议URL slug）
2. 文章正文（含H1/H2/H3标题结构）
3. FAQ板块（3-5个常见问题）
4. SEO优化说明（关键词分布、内链建议、图片alt建议）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"🔍 **SEO优化文章**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
