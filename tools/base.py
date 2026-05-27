from typing import Any, Callable
from core.security import security_guard, RiskLevel
from config.logger import logger

class BaseSystemTool:
    """
    Abstract Base class for all system tools.
    Enforces security checks and Human-In-The-Loop approvals dynamically prior to execution.
    """
    def __init__(self, name: str, description: str, risk_level: RiskLevel):
        self.name = name
        self.description = description
        self.risk_level = risk_level

    async def execute(self, action_func: Callable[[], Any], action_description: str, *args, **kwargs) -> Any:
        """
        Executes a specific code logic block after passing security checks.
        If CRITICAL risk is flagged, it blocks and waits for Telegram HITL confirmation.
        """
        logger.info(f"Tool [{self.name}] requesting execution of action: '{action_description}'")

        # 1. Check Command Risk Level dynamically
        analyzed_risk = self.risk_level
        if analyzed_risk == RiskLevel.CRITICAL:
            logger.warning(f"Critical execution requested. Halting for HITL approval: '{action_description}'")
            
            # Request approval from security guard (this will trigger a Telegram push wait)
            approved = await security_guard.request_hitl_approval(
                action_description=f"Tool: {self.name} | Action: {action_description}"
            )
            
            if not approved:
                logger.warning(f"Execution of action '{action_description}' DENIED by administrator.")
                return f"❌ Execution DENIED by Administrator: {action_description}"
            
            logger.info(f"Execution of action '{action_description}' APPROVED by administrator.")

        # 2. Run target execution block
        try:
            if asyncio.iscoroutinefunction(action_func):
                result = await action_func(*args, **kwargs)
            else:
                result = action_func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing action inside tool [{self.name}]: {e}")
            return f"❌ Tool execution failed: {e}"

# Import asyncio here inside file for internal checks
import asyncio
