"""短视频脚本技能"""
from ..llm_client import chat_completion

SKILL_META = {
    "id": "video_script",
    "name": "短视频脚本",
    "icon": "🎬",
    "description": "生成短视频脚本，含hook、台词、画面描述、BGM建议",
    "keywords": ["视频", "短视频", "脚本", "抖音", "拍摄"],
    "input_type": "textarea",
    "output_type": "text",
}

async def execute(input_data: dict) -> dict:
    product = input_data.get("text", "").strip()
    if not product:
        return {"message": "短视频脚本生成器", "content": "请描述视频主题和需求。\n\n例如：30秒产品展示，风格活泼，目标抖音平台"}

    system = """你是一位资深短视频编导，擅长制作爆款短视频脚本。你的脚本特点：
1. 开头3秒必须有强力hook，抓住观众注意力
2. 内容节奏紧凑，每个镜头都有明确目的
3. 台词口语化、有感染力，适合口播
4. 画面描述清晰具体，方便拍摄执行
5. BGM建议匹配内容情绪
6. 结尾有明确的CTA（关注/点赞/评论引导）
7. 标注精确时间轴
8. 适配目标平台风格（抖音/快手/视频号/B站）
禁止包含任何域名链接。"""

    user = f"""请为以下需求创作短视频脚本：

{product}

请按以下格式输出：
1. 视频基本信息（时长/平台/风格）
2. 分镜脚本（时间轴 | 画面描述 | 台词/旁白 | BGM/音效）
3. 拍摄建议（设备/场景/注意事项）
4. 发布建议（标题/封面/话题标签）"""

    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}]
        )
        if result.startswith("[LLM未配置]"):
            return {"error": result}
        formatted = f"🎬 **短视频脚本**\n\n{result}"
        return {"content": formatted}
    except Exception as e:
        return {"error": str(e)}
