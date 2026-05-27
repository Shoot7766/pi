import asyncio
from typing import List, Dict, Any
from crewai.tools import tool
from tools.desktop_tools import SystemScreenshotter, DesktopController
from tools.system_tools import SafeShellRunner, FileManager
from config.logger import logger

class ToolRegistry:
    """Registry managing instantiated tools."""
    def __init__(self):
        # Instantiate system tools
        self.screenshotter = SystemScreenshotter()
        self.controller = DesktopController()
        self.shell_runner = SafeShellRunner()
        self.file_manager = FileManager()

        # Map by string identifier
        self._registry = {
            "system_screenshotter": self.screenshotter,
            "desktop_controller": self.controller,
            "safe_shell_runner": self.shell_runner,
            "file_manager": self.file_manager
        }

    def get_tool(self, name: str) -> Any:
        return self._registry.get(name)

# Instantiate global singleton registry first so decorated tools can reference it
tool_registry = ToolRegistry()

# --- Define CrewAI Compatible BaseTool Instances using the @tool decorator ---

@tool("safe_shell_runner")
def safe_shell_runner(command: str) -> str:
    """Executes local command-line scripts in an isolated subprocess. Safe commands run immediately, critical ones require admin approval."""
    # Synchronously run the async method since CrewAI works in worker threads
    return asyncio.run(tool_registry.shell_runner.execute_command(command))

@tool("desktop_clicker")
def desktop_clicker(x: int, y: int) -> str:
    """Clicks at coordinates (x, y) on the desktop monitor."""
    return asyncio.run(tool_registry.controller.click_at(int(x), int(y)))

@tool("desktop_keyboard_writer")
def desktop_keyboard_writer(text: str) -> str:
    """Types the specified text characters on the keyboard."""
    return asyncio.run(tool_registry.controller.type_text(text))

@tool("system_screenshotter")
def system_screenshotter(output_path: str = "d:/ai_robot/pi/storage/screenshot.jpg") -> str:
    """Captures the current active desktop screen and saves it as a high-quality JPEG file."""
    return asyncio.run(tool_registry.screenshotter.capture_screen(output_path))

@tool("file_writer")
def file_writer(file_path: str, content: str) -> str:
    """Writes specified text contents into target system file_path."""
    return asyncio.run(tool_registry.file_manager.write_file(file_path, content))

@tool("file_path_deleter")
def file_path_deleter(target_path: str) -> str:
    """Safely removes a targeted system file or folder directory."""
    return asyncio.run(tool_registry.file_manager.remove_path(target_path))

# Dynamic tool selector that resolves tools specifically wrapped for CrewAI
def get_crew_tools_resolved(tool_names: List[str]) -> List[Any]:
    crew_tools = []
    for name in tool_names:
        if name == "system_screenshotter":
            crew_tools.append(system_screenshotter)
        elif name == "desktop_controller":
            crew_tools.extend([desktop_clicker, desktop_keyboard_writer])
        elif name == "safe_shell_runner":
            crew_tools.append(safe_shell_runner)
        elif name == "file_manager":
            crew_tools.extend([file_writer, file_path_deleter])
    return crew_tools
