"""
Skill Engine - 技能执行引擎
接收任务 -> 匹配技能 -> 执行 -> 返回结果
支持链式调用（多技能串联）
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

from skills.registry import registry, SkillMeta

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """任务执行结果"""
    task_id: str
    skill_id: str
    skill_name: str
    status: str  # "success", "failed", "pending"
    output: Any = None
    error: Optional[str] = None
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }


class SkillEngine:
    """技能执行引擎"""

    def __init__(self):
        self.registry = registry
        self._task_history: List[TaskResult] = []
        self._task_counter = 0

    async def execute(
        self, skill_id: str, input_data: dict
    ) -> TaskResult:
        """执行指定技能"""
        skill = self.registry.get(skill_id)
        if not skill:
            return TaskResult(
                task_id=self._next_task_id(),
                skill_id=skill_id,
                skill_name="未知技能",
                status="failed",
                error=f"技能 {skill_id} 不存在",
                created_at=datetime.now().isoformat(),
            )

        if not skill.handler:
            return TaskResult(
                task_id=self._next_task_id(),
                skill_id=skill_id,
                skill_name=skill.name,
                status="failed",
                error=f"技能 {skill.name} 未注册处理函数",
                created_at=datetime.now().isoformat(),
            )

        task_id = self._next_task_id()
        result = TaskResult(
            task_id=task_id,
            skill_id=skill_id,
            skill_name=skill.name,
            status="pending",
            created_at=datetime.now().isoformat(),
        )

        try:
            output = await skill.handler(input_data)
            result.status = "success"
            result.output = output
            result.completed_at = datetime.now().isoformat()
        except Exception as e:
            logger.exception(f"技能 {skill_id} 执行失败")
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now().isoformat()

        self._task_history.append(result)
        return result

    async def auto_execute(
        self, user_input: str, files: Optional[list] = None
    ) -> TaskResult:
        """自动匹配技能并执行"""
        skill = self.registry.find_by_keywords(user_input)
        if not skill:
            return TaskResult(
                task_id=self._next_task_id(),
                skill_id="none",
                skill_name="未匹配",
                status="failed",
                error="未找到匹配的技能，请尝试更具体地描述需求",
                created_at=datetime.now().isoformat(),
            )

        input_data = {"text": user_input}
        if files:
            input_data["files"] = files

        return await self.execute(skill.id, input_data)

    async def chain_execute(
        self, skill_ids: List[str], initial_input: dict
    ) -> List[TaskResult]:
        """链式调用多个技能"""
        results = []
        current_input = initial_input

        for skill_id in skill_ids:
            result = await self.execute(skill_id, current_input)
            results.append(result)
            if result.status != "success":
                break
            # 将上一个输出作为下一个输入
            current_input = {"text": "", "previous_output": result.output}

        return results

    def get_task_history(self, limit: int = 50) -> List[dict]:
        """获取任务历史"""
        return [t.to_dict() for t in self._task_history[-limit:]]

    def _next_task_id(self) -> str:
        self._task_counter += 1
        return f"task-{self._task_counter:04d}"


# 全局实例
engine = SkillEngine()
