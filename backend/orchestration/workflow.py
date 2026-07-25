"""工作流定义与执行引擎"""
import json
import time
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class WorkflowStep:
    skill_id: str
    input_mapping: dict = field(default_factory=dict)  # 从上游步骤映射
    output_key: str = ""  # 输出存储的key

@dataclass  
class WorkflowResult:
    workflow_id: str
    status: str  # pending/running/completed/failed
    steps_executed: int
    results: dict = field(default_factory=dict)
    error: Optional[str] = None
    started_at: float = 0
    completed_at: float = 0

class WorkflowEngine:
    """工作流执行引擎"""
    
    def __init__(self):
        self.history: List[WorkflowResult] = []
    
    async def execute_workflow(self, steps: List[WorkflowStep], initial_input: dict, skill_executor) -> WorkflowResult:
        """执行工作流"""
        workflow_id = f"wf_{int(time.time())}"
        result = WorkflowResult(workflow_id=workflow_id, status="running", steps_executed=0, started_at=time.time())
        context = {"__initial__": initial_input}
        
        for i, step in enumerate(steps):
            try:
                # 构建输入
                step_input = self._resolve_input(step.input_mapping, context)
                
                # 执行技能
                output = await skill_executor(step.skill_id, step_input)
                
                # 存储输出
                if step.output_key:
                    context[step.output_key] = output
                else:
                    context[f"step_{i}"] = output
                
                result.steps_executed = i + 1
                
            except Exception as e:
                result.status = "failed"
                result.error = f"Step {i+1} ({step.skill_id}) failed: {str(e)}"
                break
        else:
            result.status = "completed"
        
        result.results = context
        result.completed_at = time.time()
        self.history.append(result)
        return result
    
    def _resolve_input(self, mapping: dict, context: dict) -> dict:
        """解析输入映射"""
        resolved = {}
        for key, source in mapping.items():
            if isinstance(source, str) and source.startswith("$"):
                # 引用上下文变量
                path = source[1:].split(".")
                value = context
                for p in path:
                    if isinstance(value, dict):
                        value = value.get(p)
                    else:
                        value = None
                        break
                resolved[key] = value
            else:
                resolved[key] = source
        return resolved
    
    def get_history(self) -> list:
        return [{"id": r.workflow_id, "status": r.status, "steps": r.steps_executed, "time": r.completed_at - r.started_at} for r in self.history[-20:]]

engine = WorkflowEngine()
