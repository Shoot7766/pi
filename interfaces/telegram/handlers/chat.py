from aiogram import Router, types
from core.brain import central_brain
from core.memory.relational import RelationalMemory
from config.logger import logger

router = Router(name="chat_router")

@router.message()
async def handle_chat_message(message: types.Message):
    """
    Core entrypoint for natural language commands.
    Feeds prompt into Central AI Brain and yields real-time agent output.
    """
    prompt = message.text
    if not prompt:
        return

    telegram_id = message.from_user.id
    logger.info(f"NL Command received from Admin {telegram_id}: '{prompt[:40]}...'")

    # 1. Log incoming query to relational memory database
    RelationalMemory.add_chat_message(telegram_id=telegram_id, role="user", content=prompt)

    # 2. Trigger typing action to communicate system latency
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # 3. Inform admin that system reasoning is active
    thinking_msg = await message.answer("🧠 **AI Brain mulohaza yuritmoqda...**\nModullar va agentlar tekshirilmoqda.")

    # 4. Route prompt to central dispatcher brain
    try:
        # Pass bot instance and chat_id so the brain can send HITL keyboards if required
        response = await central_brain.process_prompt(
            prompt=prompt,
            telegram_id=telegram_id,
            bot=message.bot,
            chat_id=message.chat.id
        )
        
        # 5. Save AI response to memory
        RelationalMemory.add_chat_message(telegram_id=telegram_id, role="assistant", content=response)
        
        # 6. Return final Markdown layout (with robust splitting to avoid Telegram MESSAGE_TOO_LONG limits)
        if len(response) > 4000:
            await thinking_msg.edit_text(text=response[:4000], parse_mode="Markdown")
            remaining = response[4000:]
            while len(remaining) > 0:
                chunk = remaining[:4000]
                await message.answer(text=chunk, parse_mode="Markdown")
                remaining = remaining[4000:]
        else:
            await thinking_msg.edit_text(text=response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Brain reasoning failed: {e}")
        await thinking_msg.edit_text(
            text=f"❌ **Brain Orchestration Error:**\nSiz yuborgan buyruqni bajarishda asinxron bog'lanish uzildi.\n\n`{e}`",
            parse_mode="Markdown"
        )
