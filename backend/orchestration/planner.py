"""智能规划器 - LLM拆解任务为多步骤工作流"""
import json
from skills.llm_client import chat_completion
from .workflow import WorkflowStep

async def plan_task(task_description: str) -> list:
    """
    用LLM分析任务，自动拆解为技能步骤
    返回: List[WorkflowStep]
    """
    system = """你是任务规划专家。将用户任务拆解为多个技能步骤。
可用技能：
- doc_generator: 文档生成(Word/PDF/MD)
- spreadsheet: 表格处理(Excel/CSV)
- image_processor: 图片处理(水印/裁剪/缩放)
- ocr: 图片文字识别
- data_extractor: 数据提取(图片/文本→结构化)
- copywriter: 文案生成(小红书/公众号/短视频)

输出JSON数组，每项包含：skill_id, input_mapping(引用上游输出用$step_N.field), output_key"""

    user = f"请拆解这个任务：{task_description}"
    
    try:
        result = await chat_completion(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_object"}
        )
        plan = json.loads(result)
        steps = []
        for item in plan.get("steps", plan if isinstance(plan, list) else []):
            steps.append(WorkflowStep(
                skill_id=item.get("skill_id", ""),
                input_mapping=item.get("input_mapping", {}),
                output_key=item.get("output_key", "")
            ))
        return steps
    except Exception as e:
        return [WorkflowStep(skill_id="doc_generator", input_mapping={"prompt": task_description}, output_key="result")]
