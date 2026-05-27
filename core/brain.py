import asyncio
from aiogram import Bot
from config.logger import logger
from core.security import security_guard, RiskLevel
from core.memory.relational import RelationalMemory
from core.memory.semantic import semantic_memory
from agents.orchestrator import crew_orchestrator
from tools.registry import tool_registry
from interfaces.telegram.keypads import get_hitl_keyboard

class CentralBrain:
    """
    Central AI Boss brain coordinator.
    Acts as the primary reasoning router, routing requests to fast local execution,
    semantic search query retrievals, or CrewAI multi-agent orchestration.
    """
    
    async def process_prompt(self, prompt: str, telegram_id: int, bot: Bot = None, chat_id: int = None) -> str:
        logger.info(f"Processing NLP Prompt: '{prompt[:40]}...'")

        # 1. Retrieve historical and semantic memories
        chat_context = RelationalMemory.get_chat_history(telegram_id, limit=5)
        semantic_context = semantic_memory.query_memories(prompt, limit=2)
        
        logger.info(f"Retrieved {len(chat_context)} chat messages and {len(semantic_context)} semantic memories.")

        # 2. Local fast routing optimization
        # Avoid heavy LLM/CrewAI loops for fast trivial commands
        clean_prompt = prompt.strip().lower()
        
        if clean_prompt in ("salom", "hi", "hello", "assalomu alaykum", "assalom", "assalamu alaykum", "yozdim"):
            logger.info("Fast-path: Greeting command.")
            return (
                "👋 **Assalomu alaykum, muhtaram Boshliq!**\n\n"
                "Markaziy AI Boss operating system boshqaruv paneli faol va ishga tayyor! 🚀\n\n"
                "Men sizga kompyuteringizni xavfsiz boshqarishda, loyihalarni tahlil qilishda va orqa fonda ishlarni avtomatlashtirishda yordam beraman.\n\n"
                "🤖 **Mavjud agentlar:**\n"
                "1. 🛡️ **Security Guard Agent** — Har bir buyruq xavfsizligini ta'minlaydi.\n"
                "2. ⚙️ **OS Control Agent** — Konsol buyruqlari, fayllar va skrinshotlarni boshqaradi.\n"
                "3. 📊 **Comms & Report Agent** — Premium Markdown hisobotlar tayyorlaydi.\n\n"
                "Boshlash uchun istalgan buyruqni bering yoki pastdagi menyudan foydalaning!"
            )

        if clean_prompt in ("qanaqa agentlar bor", "kim bor", "agentlar", "help", "yordam", "info"):
            logger.info("Fast-path: Help/Info command.")
            return (
                "🤖 **Markaziy AI Boss Tizimidagi Faol Agentlar:**\n\n"
                "1. 🛡️ **Cybersecurity Auditor Agent** — Barcha buyruqlar va ruxsatnomalar xavfsizligini tekshiradi.\n"
                "2. ⚙️ **OS Control & Automation Agent** — Kompyuter tizimi buyruqlari, fayllari va skrinshotlarini boshqaradi.\n"
                "3. 📊 **Information Aggregator & Comms Agent** — Tizim holati bo'yicha premium tahliliy hisobotlar yozadi.\n\n"
                "💡 Men kompyuteringizni xavfsiz masofadan boshqarish, skrinshot olish, xavfli buyruqlarni taqiqlash yoki loyihalarni tahlil qilishga har doim tayyorman!"
            )

        if clean_prompt in ("screenshot", "ekran rasm", "ekranni ko'rsat"):
            logger.info("Fast-path: Screen capture command.")
            screenshotter = tool_registry.get_tool("system_screenshotter")
            output_path = "d:/ai_robot/pi/storage/screenshot.jpg"
            res = await screenshotter.capture_screen(output_path)
            
            # Proactively upload via telegram if bot context exists
            if bot and chat_id:
                import os
                from aiogram.types import FSInputFile
                if os.path.exists(output_path):
                    photo = FSInputFile(output_path)
                    await bot.send_photo(chat_id=chat_id, photo=photo, caption="🖥 Boshliq, tezkor ekran surati:")
                    return "📸 Ekran rasmi yuborildi."
            return f"✅ Ekran rasmi saqlandi: {res}"

        if clean_prompt in ("status", "tizim holati", "sysinfo"):
            logger.info("Fast-path: Sysinfo command.")
            shell = tool_registry.get_tool("safe_shell_runner")
            import os
            cmd = "hostname && ver" if os.name == "nt" else "uname -a && uptime"
            output = await shell.execute_command(cmd)
            return f"📋 **Tezkor Tizim Holati:**\n\n```\n{output}\n```"

        # 3. Multi-Agent Reasoning Orchestration (CrewAI)
        # For complex, multi-step, reasoning requests, spin up the native PiCrew
        try:
            logger.info("Routing request to native PiCrew...")
            
            # Combine semantic context into instruction for agents
            enhanced_instruction = prompt
            if semantic_context:
                knowledges = "\n".join([f"- {k['document']}" for k in semantic_context])
                enhanced_instruction += f"\n\n[Ma'lumotlar Bazasi]:\n{knowledges}"

            loop = asyncio.get_running_loop()
            from pi.crew import PiCrew
            
            def run_crew():
                res = PiCrew().crew().kickoff(inputs={"message": enhanced_instruction})
                return str(res)

            result = await loop.run_in_executor(None, run_crew)
            
            # Add results to semantic memory for subsequent recall
            semantic_memory.add_memory(
                text=f"Request: {prompt} | Output: {result[:100]}...",
                metadata={"type": "execution_record"}
            )
            
            return result
        except Exception as e:
            logger.error(f"Native PiCrew orchestration failed: {e}")
            return f"❌ **Multi-Agent Orchestration Failed:** {e}"

    async def process_guest_prompt(self, prompt: str, user_id: int, username: str, bot: Bot) -> str:
        """
        Securely handles incoming guest queries without granting access to any OS control tools.
        Delegates reasoning to the secure GuestAgent within CrewAI.
        """
        logger.info(f"Processing secure guest prompt from @{username} [ID: {user_id}]")
        return await crew_orchestrator.execute_guest_task_async(prompt, username, user_id)

# Instantiate global Brain coordinator
central_brain = CentralBrain()
