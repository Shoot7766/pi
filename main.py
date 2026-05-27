import sys
import asyncio

# Reconfigure stdout/stderr to handle UTF-8 emojis on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

import uvicorn
from aiogram import Bot, Dispatcher
from config.settings import settings
from config.logger import logger
from core.memory.relational import init_db
from interfaces.telegram.middlewares.auth import AuthMiddleware
from interfaces.telegram.handlers import base, control, chat
from interfaces.api.server import app

async def start_fastapi():
    """Initializes and runs the FastAPI server concurrently."""
    config = uvicorn.Config(
        app=app,
        host=settings.fastapi_host,
        port=settings.fastapi_port,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    logger.info(f"Starting FastAPI Gateway on http://{settings.fastapi_host}:{settings.fastapi_port}")
    await server.serve()

async def start_telegram_bot():
    """Initializes and runs the Aiogram 3.x Telegram Bot."""
    if settings.telegram_bot_token == "YOUR_TOKEN" or not settings.telegram_bot_token:
        logger.error("Telegram Bot Token is not configured. Telegram bot service will not start.")
        return

    # Initialize bot and dispatcher
    bot = Bot(token=settings.telegram_bot_token)
    
    # Configure security guard bot context
    from core.security import security_guard
    security_guard.bot = bot
    security_guard.main_loop = asyncio.get_running_loop()
    if settings.admin_ids:
        security_guard.admin_chat_id = settings.admin_ids[0]

    dp = Dispatcher()

    # 1. Register security/authentication middleware
    dp.message.outer_middleware(AuthMiddleware())
    dp.callback_query.outer_middleware(AuthMiddleware())

    # 2. Register modular command handlers
    dp.include_router(base.router)
    dp.include_router(control.router)
    # Chat router acts as fallback catch-all, so we include it last
    dp.include_router(chat.router)

    logger.info("Aiogram 3.x Telegram Bot initialized. Beginning polling loop.")
    try:
        # Delete webhook before polling to clear conflicts
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Telegram Bot error encountered during polling: {e}")
    finally:
        await bot.session.close()

async def start_userbot():
    """Initializes and runs the Telegram Userbot service concurrently."""
    from core.userbot import userbot_service
    if userbot_service.is_configured():
        logger.info("Telegram Userbot is configured. Starting background client...")
        try:
            await userbot_service.start()
        except Exception as e:
            logger.error(f"Telegram Userbot error encountered during background run: {e}")
    else:
        logger.info("Telegram Userbot is not fully configured (keys or session missing). Skipping userbot startup.")

async def main():
    logger.info("Initializing Central AI Boss Core System...")
    
    # 1. Initialize local databases
    init_db()

    # 2. Start Services Concurrently as independent event loop tasks
    fastapi_task = asyncio.create_task(start_fastapi())
    bot_task = asyncio.create_task(start_telegram_bot())
    userbot_task = asyncio.create_task(start_userbot())

    await asyncio.gather(fastapi_task, bot_task, userbot_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Central AI Boss halted by User.")
    except Exception as e:
        logger.critical(f"Unhandled critical crash during main boot: {e}")

