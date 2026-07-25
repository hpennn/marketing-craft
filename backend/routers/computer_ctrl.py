from fastapi import APIRouter
from pydantic import BaseModel
from computer.controller import controller
from computer import vision

router = APIRouter(tags=["computer"])

@router.post("/computer/screenshot")
async def take_screenshot():
    return controller.screenshot()

@router.post("/computer/click")
async def click_position(x: int, y: int, button: str = "left"):
    return controller.click(x, y, button)

@router.post("/computer/type")
async def type_text(text: str):
    return controller.type_text(text)

@router.post("/computer/hotkey")
async def press_hotkey(keys: list):
    return controller.hotkey(*keys)

@router.get("/computer/status")
async def computer_status():
    return {"available": controller.is_available(), "screen_size": controller.get_screen_size() if controller.is_available() else None}

class NLRequest(BaseModel):
    instruction: str

@router.post("/computer/execute")
async def execute_nl(req: NLRequest):
    return await vision.execute_natural_language(req.instruction)

class AnalyzeRequest(BaseModel):
    prompt: str = "describe all interactive elements"

@router.post("/computer/analyze")
async def analyze_screen(req: AnalyzeRequest):
    return await vision.analyze_screen(req.prompt)
