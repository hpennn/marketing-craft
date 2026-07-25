from skills.llm_client import vision_completion
from .controller import controller
import json

async def analyze_screen(prompt="describe screen elements"):
    screenshot = controller.screenshot()
    if "error" in screenshot:
        return screenshot
    try:
        result = await vision_completion(screenshot["image"], prompt)
        return {"analysis": result, "screenshot": screenshot}
    except Exception as e:
        return {"error": str(e)}

async def execute_natural_language(instruction):
    screenshot = controller.screenshot()
    if "error" in screenshot:
        return screenshot
    try:
        plan_text = await vision_completion(
            screenshot["image"],
            f"Analyze screen and plan actions for: {instruction}. Output JSON with steps array"
        )
        plan = json.loads(plan_text)
        results = []
        for step in plan.get("steps", []):
            action = step.get("action", "")
            params = step.get("params", {})
            if action == "click":
                r = controller.click(params.get("x", 0), params.get("y", 0))
            elif action == "type":
                r = controller.type_text(params.get("text", ""))
            elif action == "hotkey":
                r = controller.hotkey(*params.get("keys", []))
            else:
                r = {"status": "unknown"}
            results.append({"action": action, "result": r})
        return {"plan": plan, "execution": results}
    except Exception as e:
        return {"error": str(e)}
