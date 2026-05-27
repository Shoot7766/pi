from typing import Any, Callable, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config.settings import settings
from config.logger import logger

class AuthMiddleware(BaseMiddleware):
    """
    Aiogram 3.x Authentication Middleware.
    Restricts access to only registered Admin IDs configured in settings.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        username = "Unknown"

        if isinstance(event, Message):
            user_id = event.from_user.id
            username = event.from_user.username or "Unknown"
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
            username = event.from_user.username or "Unknown"

        if user_id is None:
            return

        # Determine administrator status
        is_admin = user_id in settings.admin_ids
        data["is_admin"] = is_admin

        # Callback queries (control panel buttons) are strictly for the admin
        if isinstance(event, CallbackQuery) and not is_admin:
            logger.warning(f"BLOCKED callback query attempt: User '{username}' [ID: {user_id}]")
            await event.answer("⚠️ Ushbu panel va tugmalar faqat administrator (Boshliq) uchun ruxsat etilgan!", show_alert=True)
            return

        # If user is not admin, intercept and route their message to the secure Guest Agent
        if not is_admin:
            logger.info(f"Guest message intercepted from '{username}' [ID: {user_id}]")
            
            if isinstance(event, Message):
                # Trigger typing action to indicate reasoning
                await event.bot.send_chat_action(chat_id=event.chat.id, action="typing")
                
                # Show quick initial status message
                guest_thinking = await event.answer("🔄 **Bog'lanish o'rnatilmoqda...**\nBossning shaxsiy kotibi sizga javob yozmoqda.")
                
                try:
                    # Hand off to secure guest receptionist agent
                    from core.brain import central_brain
                    response = await central_brain.process_guest_prompt(
                        prompt=event.text or "",
                        user_id=user_id,
                        username=username,
                        bot=event.bot
                    )
                    await guest_thinking.edit_text(response, parse_mode="Markdown")
                except Exception as e:
                    logger.error(f"Error processing guest interaction: {e}")
                    await guest_thinking.edit_text(
                        "👋 **Assalomu alaykum!**\n\nBossning shaxsiy yordamchisi tarmoqda. "
                        "Xabaringiz qabul qilindi, tez orada Boshliq sizga javob beradi!",
                        parse_mode="Markdown"
                    )
            return

        # Allow admin messages to pass through to the main chat router (handled by CrewAI OSAgent)
        logger.info(f"ACCESS GRANTED Admin: User '{username}' [ID: {user_id}]")
        return await handler(event, data)
