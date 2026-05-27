import re
import uuid
import asyncio
import threading
from enum import Enum
from typing import Dict, Any, List, Optional
from config.settings import settings
from config.logger import logger
from interfaces.telegram.keypads import get_hitl_keyboard

class RiskLevel(Enum):
    SAFE = "SAFE"          # Non-destructive read or safe navigation
    MODERATE = "MODERATE"  # Writes, folder creation, key presses
    CRITICAL = "CRITICAL"  # System commands, deletions, system configuration changes

class SecurityGuard:
    def __init__(self):
        # In-memory dictionary for active HITL verification requests
        # Structure: { request_id: { "prompt": str, "event": threading.Event, "approved": bool, "status": str } }
        self._hitl_queue: Dict[str, Dict[str, Any]] = {}
        
        self.bot = None
        self.main_loop = None
        self.admin_chat_id = None
        
        # Risk assessment keywords
        self.critical_patterns = [
            r"\brm\b", r"\bdel\b", r"\berase\b", r"(?<![-/])\bformat\b(?!-)", 
            r"\bshutdown\b", r"\breboot\b", r"\bkill\b", r"\bkillall\b",
            r"\bsudo\b", r"\bchmod\b", r"\bchown\b", r"\bdd\s+if=",
            r"\bparted\b", r"\bmkfs\b"
        ]

    def is_user_authorized(self, user_id: int) -> bool:
        """Verify if the user is in the authorized admin list."""
        is_auth = user_id in settings.admin_ids
        if not is_auth:
            logger.warning(f"Unauthorized access attempt by User ID: {user_id}")
        return is_auth

    def analyze_command_risk(self, command: str) -> RiskLevel:
        """
        Analyze system commands for potential security risks.
        If strict whitelist is on, anything not matching simple reads is moderate/critical.
        """
        clean_cmd = command.strip().lower()

        # Check for critical system command patterns
        for pattern in self.critical_patterns:
            if re.search(pattern, clean_cmd):
                logger.warning(f"Critical risk pattern detected in command: '{command}'")
                return RiskLevel.CRITICAL

        # Safe system commands (e.g. system info, harmless listings)
        safe_prefixes = ("echo", "dir", "ls", "pwd", "whoami", "hostname", "ver", "systeminfo")
        if clean_cmd.startswith(safe_prefixes):
            return RiskLevel.SAFE

        # Moderate actions (standard commands that aren't critical but aren't strictly read-only)
        return RiskLevel.MODERATE if not settings.strict_command_whitelist else RiskLevel.CRITICAL

    async def request_hitl_approval(self, action_description: str) -> bool:
        """
        Register a HITL authorization request and wait for human response.
        Enforces thread safety using threading.Event.
        """
        request_id = str(uuid.uuid4())
        event = threading.Event()
        
        self._hitl_queue[request_id] = {
            "prompt": action_description,
            "event": event,
            "approved": False,
            "status": "PENDING"
        }

        logger.info(f"Registered HITL Request [{request_id}] for action: '{action_description}'")

        # Send Telegram notification if bot and admin_chat_id are configured
        if self.bot and self.admin_chat_id and self.main_loop:
            async def send_msg():
                try:
                    await self.bot.send_message(
                        chat_id=self.admin_chat_id,
                        text=(
                            f"⚠️ **DIQQAT: Tizim Boshqaruv Ruxsati!**\n\n"
                            f"Amal: `{action_description}`\n\n"
                            f"Ushbu amalni bajarishga ruxsat berasizmi?"
                        ),
                        reply_markup=get_hitl_keyboard(request_id=request_id)
                    )
                except Exception as e:
                    logger.error(f"Failed to send HITL Telegram message: {e}")

            asyncio.run_coroutine_threadsafe(send_msg(), self.main_loop)
        else:
            logger.warning("Telegram Bot context missing in SecurityGuard. Unable to send notification.")

        # Wait on the threading event (blocks the calling thread safely)
        loop = asyncio.get_running_loop()
        
        def wait_for_event():
            return event.wait(timeout=300.0)

        success = await loop.run_in_executor(None, wait_for_event)
        
        if not success:
            logger.warning(f"HITL Request [{request_id}] timed out after 5 minutes.")
            self._hitl_queue.pop(request_id, None)
            return False

        # Retrieve outcome
        req_data = self._hitl_queue.pop(request_id, None)
        if req_data:
            return req_data["approved"]
        return False

    def approve_request(self, request_id: str):
        """Approve a pending verification request."""
        if request_id in self._hitl_queue:
            req = self._hitl_queue[request_id]
            req["status"] = "APPROVED"
            req["approved"] = True
            req["event"].set()
            logger.info(f"HITL Request [{request_id}] APPROVED by Admin.")

    def deny_request(self, request_id: str):
        """Deny a pending verification request."""
        if request_id in self._hitl_queue:
            req = self._hitl_queue[request_id]
            req["status"] = "DENIED"
            req["approved"] = False
            req["event"].set()
            logger.warning(f"HITL Request [{request_id}] DENIED by Admin.")

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Retrieve all currently pending verification tasks."""
        return [
            {"request_id": rid, "prompt": data["prompt"]}
            for rid, data in self._hitl_queue.items()
            if data["status"] == "PENDING"
        ]

# Central security guardian instance
security_guard = SecurityGuard()
