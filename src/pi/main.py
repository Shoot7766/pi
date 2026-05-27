# src/pi/main.py

import sys
import os
import asyncio

# Inject absolute source and project root paths to resolve module imports natively
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

if root_path not in sys.path:
    sys.path.insert(0, root_path)
if src_path not in sys.path:
    sys.path.insert(1, src_path)

from pi.crew import PiCrew

# Reconfigure stdout/stderr to handle UTF-8 emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

from config.logger import logger
from core.memory.relational import init_db

async def run_services():
    """Boots all background listeners (Aiogram, FastAPI, Userbot) concurrently."""
    from main import start_fastapi, start_telegram_bot, start_userbot
    
    # 1. Initialize DB
    init_db()

    # 2. Concurrently gather the servers
    fastapi_task = asyncio.create_task(start_fastapi())
    bot_task = asyncio.create_task(start_telegram_bot())
    userbot_task = asyncio.create_task(start_userbot())

    logger.info("CrewAI CLI Daemon started successfully. Listening for commands...")
    await asyncio.gather(fastapi_task, bot_task, userbot_task)

def run():
    """
    Standard entrypoint for 'crewai run'.
    Boots the entire unified Telegram bot and dynamic CrewAI agent platform.
    """
    try:
        asyncio.run(run_services())
    except KeyboardInterrupt:
        logger.info("CrewAI CLI Daemon halted by User.")
    except Exception as e:
        logger.critical(f"Unhandled critical crash during crewai run boot: {e}")

if __name__ == "__main__":
    run()
