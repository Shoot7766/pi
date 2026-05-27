import os
import io
import asyncio
from PIL import Image
from tools.base import BaseSystemTool, RiskLevel
from config.settings import settings
from config.logger import logger

# Import MSS safely
MSS_AVAILABLE = False
try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    logger.warning("mss package not found. Screenshot capture fallback enabled.")

# Import PyAutoGUI safely
PYAUTOGUI_AVAILABLE = False
try:
    import pyautogui
    # Configure safety features
    pyautogui.FAILSAFE = settings.gui_failsafe
    pyautogui.PAUSE = 0.5 # Add half a second delay after each GUI call
    PYAUTOGUI_AVAILABLE = True
except Exception as e:
    logger.warning(f"PyAutoGUI not available in current display environment: {e}")

class SystemScreenshotter(BaseSystemTool):
    def __init__(self):
        super().__init__(
            name="system_screenshotter",
            description="Captures the current active desktop screen and saves it as a high-quality JPEG file.",
            risk_level=RiskLevel.SAFE
        )

    async def capture_screen(self, output_path: str = "d:/ai_robot/pi/storage/screenshot.jpg") -> str:
        """Asynchronously captures active screen and saves it."""
        def _sync_capture():
            if not MSS_AVAILABLE:
                raise ImportError("MSS library not installed.")
            
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with mss.mss() as sct:
                # Capture primary monitor (monitor 1)
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                
                # Convert raw pixels to PIL image and save as compressed JPEG
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                img.save(output_path, "JPEG", quality=75)
            return f"Screenshot saved successfully at: {output_path}"

        try:
            return await self.execute(_sync_capture, "Capture active primary monitor display")
        except Exception as e:
            return f"❌ Screenshot capture failed: {e}"

class DesktopController(BaseSystemTool):
    def __init__(self):
        super().__init__(
            name="desktop_controller",
            description="Controls mouse movements, mouse clicks, and keyboard strokes.",
            risk_level=RiskLevel.MODERATE
        )

    async def click_at(self, x: int, y: int) -> str:
        """Safe mouse click at coordinates (x, y)."""
        def _sync_click():
            if not PYAUTOGUI_AVAILABLE:
                raise RuntimeError("PyAutoGUI GUI interface is not active or available.")
            
            screen_w, screen_h = pyautogui.size()
            if not (0 <= x <= screen_w and 0 <= y <= screen_h):
                raise ValueError(f"Target coordinates ({x}, {y}) out of screen boundaries: ({screen_w}x{screen_h})")
            
            pyautogui.click(x, y)
            return f"Successfully clicked at ({x}, {y})"

        return await self.execute(_sync_click, f"Click mouse at coordinates ({x}, {y})")

    async def type_text(self, text: str) -> str:
        """Safe keystroke typist."""
        def _sync_type():
            if not PYAUTOGUI_AVAILABLE:
                raise RuntimeError("PyAutoGUI GUI interface is not active.")
            
            pyautogui.write(text, interval=0.05)
            return f"Typed input text: '{text[:20]}...'"

        # Typing could potentially execute terminal scripts, so we assess text content
        risk = RiskLevel.CRITICAL if ("rm " in text or "del " in text) else RiskLevel.MODERATE
        self.risk_level = risk
        
        return await self.execute(_sync_type, f"Simulate typing keyboard characters: '{text[:30]}'")
