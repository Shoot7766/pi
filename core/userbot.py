import asyncio
import os
from telethon import TelegramClient, events
from config.settings import settings
from config.logger import logger
from core.brain import central_brain

class TelegramUserbot:
    """
    Background Telegram Userbot Service.
    Connects using personal credentials and session, listens to direct messages,
    and automatically replies on behalf of the user when they are offline/inactive.
    """
    def __init__(self):
        self.session_path = "d:/ai_robot/pi/storage/userbot.session"
        self.client = None
        # Track scheduled reply tasks: { chat_id: asyncio.Task }
        self.pending_replies = {}

    def is_configured(self) -> bool:
        """Checks if session file and API keys are set up."""
        session_exists = os.path.exists(self.session_path) or os.path.exists(self.session_path + ".dat")
        keys_configured = bool(settings.telegram_api_id and settings.telegram_api_hash)
        return session_exists and keys_configured

    async def start(self):
        """Starts the Telethon client in the background."""
        if not self.is_configured():
            logger.warning("Telegram Userbot is NOT fully configured (missing API keys or session file). Skipping startup.")
            return

        api_id = int(settings.telegram_api_id)
        api_hash = settings.telegram_api_hash
        
        logger.info("Initializing Telegram Userbot client...")
        self.client = TelegramClient(self.session_path, api_id, api_hash)
        
        # Register handlers
        self._register_handlers()
        
        # Connect client without blocking (main.py will run this in background)
        await self.client.connect()
        if not await self.client.is_user_authorized():
            logger.error("Userbot session exists but is not authorized. Please run 'py -3.10 scratch/setup_userbot.py' first.")
            await self.client.disconnect()
            return
            
        me = await self.client.get_me()
        logger.info(f"Telegram Userbot started successfully as {me.first_name} {me.last_name or ''} (@{me.username or 'No Username'})")
        
        # Keep client running in background
        await self.client.run_until_disconnected()

    def _register_handlers(self):
        """Registers Telethon event handlers."""
        
        @self.client.on(events.NewMessage(incoming=True))
        async def handle_incoming_message(event):
            # Skip if it is not a private chat, or is channel/group
            if not event.is_private or event.is_channel or event.is_group:
                return

            sender = await event.get_sender()
            
            # Skip if sender is a bot or self to prevent infinite loops
            if not sender or getattr(sender, 'bot', False):
                return

            
            me = await self.client.get_me()
            if sender.id == me.id:
                return

            chat_id = event.chat_id
            message_text = event.text or ""
            
            logger.info(f"Userbot: Incoming message from {sender.first_name} [ID: {sender.id}] in chat {chat_id}: '{message_text[:30]}'")

            # Cancel any existing pending reply task for this chat to reset the timer on a new message
            if chat_id in self.pending_replies:
                self.pending_replies[chat_id].cancel()
                logger.debug(f"Userbot: Reset timer for chat {chat_id} due to new incoming message.")

            # Schedule a new auto-reply task
            task = asyncio.create_task(self._scheduled_auto_reply(chat_id, sender, message_text, event.id))
            self.pending_replies[chat_id] = task

        @self.client.on(events.NewMessage(outgoing=True))
        async def handle_outgoing_message(event):
            chat_id = event.chat_id
            # If we send a message manually (or through another client), cancel any scheduled auto-reply
            if chat_id in self.pending_replies:
                self.pending_replies[chat_id].cancel()
                del self.pending_replies[chat_id]
                logger.info(f"Userbot: Cancelled auto-reply for chat {chat_id} because Admin manually replied.")

    async def _scheduled_auto_reply(self, chat_id: int, sender, prompt: str, trigger_msg_id: int):
        """Waits for the configured delay, checks if still unanswered, and replies."""
        delay = settings.userbot_delay_seconds
        logger.info(f"Userbot: Scheduled auto-reply in {delay} seconds for chat {chat_id}")
        
        try:
            await asyncio.sleep(delay)
            
            # Double check last message in chat to ensure no reply was made
            # Telethon get_messages(limit=1) gets the most recent message in the chat
            messages = await self.client.get_messages(chat_id, limit=1)
            if not messages:
                return
                
            last_message = messages[0]
            me = await self.client.get_me()
            
            # If the last message is from us, we have already replied manually or via another app
            if last_message.sender_id == me.id:
                logger.info(f"Userbot: Skipped auto-reply in chat {chat_id} because a reply was already sent.")
                return

            logger.info(f"Userbot: No reply found in chat {chat_id} after {delay}s. Generating AI response...")
            
            # Trigger typing action in the chat
            async with self.client.action(chat_id, 'typing'):
                # Route directly to our specialized conversational CrewAI agent!
                from agents.orchestrator import crew_orchestrator
                response = await crew_orchestrator.execute_personal_reply_async(
                    instruction=prompt
                )
                
                # Clean response of any accidental bot markers
                clean_response = response.replace("👋 **Assalomu alaykum, muhtaram Boshliq!**", "").strip()
                if clean_response.startswith("🤖 **Yangi Agent Yaratildi"):
                    clean_response = "Assalomu alaykum! Hozirda biroz band edim. Xabaringizni qabul qildim, tez orada siz bilan bog'lanaman!"


                # Send response as a reply to the trigger message
                await self.client.send_message(
                    chat_id, 
                    clean_response,
                    reply_to=trigger_msg_id
                )
                logger.info(f"Userbot: Sent auto-reply to {sender.first_name} [ID: {chat_id}]")
                
        except asyncio.CancelledError:
            logger.debug(f"Userbot: Auto-reply task cancelled for chat {chat_id}")
        except Exception as e:
            logger.error(f"Userbot: Failed to execute auto-reply: {e}")
        finally:
            # Clean up pending reference
            self.pending_replies.pop(chat_id, None)

# Instantiate global Userbot service
userbot_service = TelegramUserbot()
