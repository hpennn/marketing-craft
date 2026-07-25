from fastapi import APIRouter
from pydantic import BaseModel
from orchestration.planner import plan_task
from orchestration.workflow import engine
from skills.registry import registry

router = APIRouter(tags=["workflow"])

class PlanRequest(BaseModel):
    task: str

class ExecuteRequest(BaseModel):
    task: str
    input_data: dict = {}

@router.post("/workflows/plan")
async def plan_workflow(req: PlanRequest):
    steps = await plan_task(req.task)
    return {"task": req.task, "steps": [{"skill_id": s.skill_id, "output_key": s.output_key} for s in steps]}

@router.post("/workflows/execute")
async def execute_workflow(req: ExecuteRequest):
    steps = await plan_task(req.task)
    
    async def skill_executor(skill_id, input_data):
        skill = registry.get_skill(skill_id)
        if not skill:
            raise Exception(f"Unknown skill: {skill_id}")
        return await skill["module"].execute(input_data)
    
    result = await engine.execute_workflow(steps, req.input_data, skill_executor)
    return {"workflow_id": result.workflow_id, "status": result.status, "steps_executed": result.steps_executed, "results": {k: str(v)[:500] for k, v in result.results.items()}, "error": result.error}

@router.get("/workflows/history")
async def workflow_history():
    return engine.get_history()
