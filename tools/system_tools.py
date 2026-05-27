import os
import shutil
import asyncio
from tools.base import BaseSystemTool, RiskLevel
from core.security import security_guard
from config.logger import logger

class SafeShellRunner(BaseSystemTool):
    def __init__(self):
        super().__init__(
            name="safe_shell_runner",
            description="Executes local command-line scripts in an isolated subprocess. Safe commands run immediately, critical ones require admin approval.",
            risk_level=RiskLevel.SAFE
        )

    async def execute_command(self, command: str) -> str:
        """Executes a system shell command safely and asynchronously."""
        # 1. Analyze command risk level dynamically
        risk = security_guard.analyze_command_risk(command)
        self.risk_level = risk

        async def _async_run():
            # In Windows, we execute in standard powershell/cmd. In Linux, standard shell.
            # Use shell=True for variable expansion and piping support
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Set a 60-second timeout on commands to prevent hung processes
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                return "❌ Subprocess Execution Error: Command timed out after 60 seconds."

            out_decoded = stdout.decode("utf-8", errors="replace").strip()
            err_decoded = stderr.decode("utf-8", errors="replace").strip()

            result = []
            if out_decoded:
                result.append(out_decoded)
            if err_decoded:
                result.append(f"⚠️ Errors/Warnings:\n{err_decoded}")

            return "\n".join(result) if result else "Success (No output)."

        return await self.execute(_async_run, f"Execute Terminal Shell Command: '{command}'")

class FileManager(BaseSystemTool):
    def __init__(self):
        super().__init__(
            name="file_manager",
            description="Performs directory structures reads, file creations, copies, and safe removals.",
            risk_level=RiskLevel.SAFE
        )

    async def write_file(self, file_path: str, content: str) -> str:
        """Create or edit file contents."""
        self.risk_level = RiskLevel.MODERATE
        
        def _sync_write():
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully created/edited file: {file_path} ({len(content)} bytes)"

        return await self.execute(_sync_write, f"Write text contents to file path: {file_path}")

    async def remove_path(self, target_path: str) -> str:
        """Safe path removal (Force Critical HITL review)."""
        self.risk_level = RiskLevel.CRITICAL
        
        def _sync_remove():
            if not os.path.exists(target_path):
                return f"Path does not exist: {target_path}"
            
            if os.path.isdir(target_path):
                shutil.rmtree(target_path)
                return f"Directory deleted: {target_path}"
            else:
                os.remove(target_path)
                return f"File deleted: {target_path}"

        return await self.execute(_sync_remove, f"Delete system path (file/directory): {target_path}")
