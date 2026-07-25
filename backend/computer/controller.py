import base64, io, os, time

COMPUTER_ENABLED = os.getenv("COMPUTER_CONTROL_ENABLED", "false").lower() == "true"

class ComputerController:
    def __init__(self):
        self.pyautogui = None
        if COMPUTER_ENABLED:
            try:
                import pyautogui
                self.pyautogui = pyautogui
                pyautogui.FAILSAFE = True
            except ImportError:
                pass

    def is_available(self):
        return self.pyautogui is not None

    def screenshot(self):
        if not self.is_available():
            return {"error": "not enabled, set COMPUTER_CONTROL_ENABLED=true"}
        try:
            img = self.pyautogui.screenshot()
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            return {"image": f"data:image/png;base64,{b64}", "width": img.width, "height": img.height}
        except Exception as e:
            return {"error": str(e)}

    def click(self, x, y, button="left"):
        if not self.is_available():
            return {"error": "not enabled"}
        self.pyautogui.click(x, y, button=button)
        return {"status": "ok", "x": x, "y": y}

    def type_text(self, text):
        if not self.is_available():
            return {"error": "not enabled"}
        if text.isascii():
            self.pyautogui.typewrite(text, interval=0.05)
        return {"status": "ok", "length": len(text)}

    def hotkey(self, *keys):
        if not self.is_available():
            return {"error": "not enabled"}
        self.pyautogui.hotkey(*keys)
        return {"status": "ok", "keys": list(keys)}

    def get_screen_size(self):
        if not self.is_available():
            return {"error": "not enabled"}
        s = self.pyautogui.size()
        return {"width": s.width, "height": s.height}

controller = ComputerController()
