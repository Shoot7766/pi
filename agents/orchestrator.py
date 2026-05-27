import asyncio
from typing import Dict, Any, List
from crewai import Crew, Task, Process
from config.settings import settings
from config.logger import logger
from agents.os_agent import OSAgent
from agents.comms_agent import CommsAgent
from agents.security_agent import SecurityAgent

class CrewOrchestrator:
    """
    CrewAI Multi-Agent orchestrator.
    Handles thread-safe asynchronous execution of Crew tasks using thread pooling.
    """
    def __init__(self):
        pass

    def _initialize_claude_llm(self):
        """Loads Anthropic Claude-Sonnet-4-6 for the Central AI Boss (Manager/Orchestrator)"""
        if settings.anthropic_api_key:
            logger.info("Configured Anthropic Claude-Sonnet-4-6 for Central AI Boss.")
            return "anthropic/claude-sonnet-4-6"
        
        # Fallback to GPT-4o if Claude key is missing
        if settings.openai_api_key:
            logger.warning("Claude key missing, falling back to OpenAI GPT-4o for Central Boss.")
            return "openai/gpt-4o"
        return None

    def _initialize_gpt_llm(self):
        """Loads OpenAI GPT-4o for worker agents"""
        if settings.openai_api_key:
            logger.info("Configured OpenAI GPT-4o for other agents.")
            return "openai/gpt-4o"
        
        # Fallback to Claude if OpenAI key is missing
        if settings.anthropic_api_key:
            logger.warning("OpenAI key missing, falling back to Claude-Sonnet-4-6 for other agents.")
            return "anthropic/claude-sonnet-4-6"
        return None

    async def execute_task_async(self, instruction: str) -> str:
        """
        Executes a user request asynchronously by spinning up a Crew execution in a background thread.
        This prevents blocking the Aiogram Telegram bot and FastAPI servers.
        """
        # Expose the API keys dynamically to the OS environment so CrewAI sub-processes can read them
        import os
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        # Instantiate fresh agents specifically for this task to avoid concurrent executor conflicts
        claude_llm = self._initialize_claude_llm()
        gpt_llm = self._initialize_gpt_llm()
        
        # OS agent uses GPT-4.0 (gpt_llm), while the Crew manager (boss) or default uses Claude
        os_agent = OSAgent(llm=gpt_llm).get_agent()

        loop = asyncio.get_running_loop()
        
        # Check if the user is asking to create a customized agent
        clean_instruction = instruction.lower()
        is_dynamic_agent = any(kw in clean_instruction for kw in ["agent yarat", "yangi agent", "agent qil", "create agent"])

        if is_dynamic_agent:
            logger.info("Dynamic agent creation requested. Parsing properties...")
            from crewai import Agent as CrewAgent
            from crewai import Task as CrewTask
            from tools.registry import get_crew_tools_resolved
            
            # Use the LLM (Claude) to parse the custom agent specifications
            parser_agent = CrewAgent(
                role="Information Extractor",
                goal="Accurately extract structured JSON from a text prompt describing a custom AI agent and its task.",
                backstory="You are an expert data parser. You extract agent role, goal, backstory, and task into raw JSON.",
                llm=claude_llm,
                verbose=False
            )
            
            parser_task = CrewTask(
                description=(
                    f"Foydalanuvchi quyidagi matnda yangi agent yaratishni va unga vazifa berishni so'radi: '{instruction}'.\n"
                    f"Ushbu matndan quyidagi ma'lumotlarni aniq ajratib oling va raw JSON formatida qaytaring:\n"
                    f"role: (agentning roli/nomi - masalan, 'Fayl Tahlilchisi')\n"
                    f"goal: (agentning maqsadi - masalan, 'Loyiha kodlarini tekshirish')\n"
                    f"backstory: (agentning o'tmishi/tavsifi - masalan, 'Siz tajribali kod tahlilchisiz...')\n"
                    f"task: (agent bajarishi kerak bo'lgan aniq vazifa - masalan, 'main.py tarkibini o'qish')\n\n"
                    f"QAYTARIQ FORMATI:\n"
                    f'{{"role": "...", "goal": "...", "backstory": "...", "task": "..."}}\n\n'
                    f"Faqat va faqat raw JSON qaytaring, boshqa hech qanday izoh yoki markdown block (```) yozmang!"
                ),
                expected_output="Raw JSON string only.",
                agent=parser_agent
            )
            
            parser_crew = Crew(
                agents=[parser_agent],
                tasks=[parser_task],
                verbose=False
            )
            
            try:
                parser_result = await loop.run_in_executor(None, parser_crew.kickoff)
                parser_result_str = str(parser_result)
                
                import json
                # Clean result of any markdown fences
                clean_json = parser_result_str.replace("```json", "").replace("```", "").strip()
                specs = json.loads(clean_json)
                
                logger.info(f"Successfully parsed dynamic agent specs: {specs}")
                
                # Dynamically instantiate the CrewAI Agent!
                dynamic_agent = CrewAgent(
                    role=specs["role"],
                    goal=specs["goal"],
                    backstory=specs["backstory"] + "\nCRITICAL: Siz har doim foydalanuvchi bilan FAQAT O'ZBEK TILIDA muloqot qilishingiz, barcha tushuntirishlar va hisobotlarni qat'iy O'ZBEK TILIDA yozishingiz shart. Ingliz tilida yoki boshqa tilda javob berish mutlaqo taqiqlanadi!",
                    tools=get_crew_tools_resolved(["safe_shell_runner", "desktop_controller", "system_screenshotter", "file_manager"]),
                    llm=gpt_llm,
                    verbose=True,
                    memory=False
                )
                
                # Dynamically instantiate the CrewAI Task!
                dynamic_task = CrewTask(
                    description=specs["task"] + f"\nCRITICAL: Barcha tushuntirishlar, hisobotlar va yakuniy xulosalar FAQAT va QAT'IY O'ZBEK TILIDA yozilishi shart. Format the output with structured lists, alerts, or code blocks in Uzbek.",
                    expected_output="An elegant markdown response in Uzbek containing structured lists, alerts, or code blocks summarizing execution details.",
                    agent=dynamic_agent
                )
                
                # Wire the dynamic crew together!
                crew = Crew(
                    agents=[dynamic_agent],
                    tasks=[dynamic_task],
                    manager_llm=claude_llm,
                    verbose=True
                )
                
                logger.info(f"Kicking off DYNAMIC CrewAI task for agent: '{specs['role']}'")
                
                result = await loop.run_in_executor(None, crew.kickoff)
                logger.info("Dynamic CrewAI task execution completed successfully.")
                return f"🤖 **Yangi Agent Yaratildi (CrewAI Object: {specs['role']})**\n\n" + str(result)
                
            except Exception as json_err:
                logger.error(f"Failed to parse or run dynamic agent: {json_err}. Falling back to standard flow.")

        # 1. Define specific task for the OS agent
        task_os = Task(
            description=(
                f"Analyze the request: '{instruction}'. Execute the required OS level actions (terminal commands, file management, "
                f"desktop interaction, screenshots) using your tools to achieve the goal.\n"
                f"Once completed, formulate a premium, elegant summary report for the user in beautiful GitHub Markdown.\n"
                f"CRITICAL: Barcha tushuntirishlar, hisobotlar va yakuniy xulosalar FAQAT va QAT'IY O'ZBEK TILIDA yozilishi shart. "
                f"Highlight what succeeded, any warning/error messages, and format the output with structured lists, alerts, or code blocks in Uzbek."
            ),
            expected_output="An elegant markdown response in Uzbek containing structured lists, alerts, or code blocks summarizing execution details.",
            agent=os_agent
        )

        # 2. Wire the crew together with the single task and set Claude as the manager (boss) LLM
        crew = Crew(
            agents=[os_agent],
            tasks=[task_os],
            manager_llm=claude_llm,
            verbose=True
        )

        logger.info(f"Kicking off CrewAI async task: '{instruction[:40]}...'")

        # 3. Offload synchronous execution to a worker thread
        try:
            result = await loop.run_in_executor(None, crew.kickoff)
            logger.info("CrewAI task execution completed successfully.")
            return str(result)
        except Exception as e:
            logger.error(f"CrewAI execution error: {e}")
            return f"❌ **CrewAI Execution Error:** {e}"

    def _initialize_guest_agent(self, llm):
        from crewai import Agent
        from crewai.tools import tool
        
        @tool("notify_boss_tool")
        def notify_boss_tool(guest_username: str, guest_id: int, message_content: str) -> str:
            """
            Delivers a message from a guest user directly to the Boss's private Telegram inbox.
            Arguments:
              guest_username: The Telegram @username of the guest.
              guest_id: The numeric Telegram ID of the guest.
              message_content: The text message/request the guest wants to leave for the Boss.
            """
            from core.security import security_guard
            if not security_guard.bot or not settings.admin_ids:
                return "Xabarni yetkazib bo'lmadi: Tizim konteksti faollashtirilmagan."
            
            admin_chat_id = settings.admin_ids[0]
            async def send_notification():
                text = (
                    f"📬 **Yangi Mehmon Xabari!**\n\n"
                    f"👤 **Mehmon:** @{guest_username} (ID: `{guest_id}`)\n"
                    f"💬 **Xabar:** {message_content}\n\n"
                    f"💡 Siz ushbu foydalanuvchiga Telegram orqali javob yozishingiz mumkin."
                )
                await security_guard.bot.send_message(chat_id=admin_chat_id, text=text, parse_mode="Markdown")
            
            if security_guard.main_loop:
                asyncio.run_coroutine_threadsafe(send_notification(), security_guard.main_loop)
            return "Xabar Boshliqning shaxsiy Telegramiga muvaffaqiyatli yetkazildi!"

        return Agent(
            role="Boshliqning Virtual Yordamchisi va Kotibi",
            goal="Botga yozgan mehmonlarni professional darajada kutib olish, savollariga faqat o'zbek tilida muloyim javob berish va ularning xabarlarini Boshliqqa yetkazish.",
            backstory=(
                "Siz ushbu kompyuter va tizim egasi bo'lgan Boshliqning shaxsiy kotibi va yordamchisiz. "
                "Siz juda odobli, samimiy va professionalsiz. Boshliq hozir band bo'lganligi sababli, "
                "kelgan mehmonlar bilan shaxsan suhbatlashasiz. Sizda kompyuter fayllariga yoki terminalga mutlaqo "
                "kirish huquqi yo'q. Mehmonlar sizdan kompyuterni boshqarishni so'rasa, o'zingizni shunchaki virtual yordamchi "
                "ekanligingizni va xavfsizlik nuqtai nazaridan kirish huquqingiz yo'qligini tushuntiring. "
                "Agarda ular xabar yoki buyurtma qoldirmoqchi bo'lishsa, 'notify_boss_tool' asbobidan foydalanib xabarni "
                "zudlik bilan Boshliqqa yuboring.\n"
                "CRITICAL: Barcha muloqot va tushuntirishlar faqat va qat'iy O'ZBEK TILIDA bo'lishi shart!"
            ),
            tools=[notify_boss_tool],
            llm=llm,
            verbose=True,
            memory=False
        )

    async def execute_guest_task_async(self, instruction: str, username: str, user_id: int) -> str:
        """Runs a secure dynamic task for guest messages using GuestAgent"""
        claude_llm = self._initialize_claude_llm()
        guest_agent = self._initialize_guest_agent(llm=claude_llm)
        
        from crewai import Task
        task_guest = Task(
            description=(
                f"Mehmon @{username} (ID: {user_id}) quyidagi xabarni yubordi: '{instruction}'.\n"
                f"Unga juda samimiy va professional tarzda faqat O'ZBEK TILIDA javob bering. "
                f"Agar u Boshliqqa xabar qoldirmoqchi bo'lsa, 'notify_boss_tool' orqali Boshliqning telegramiga xabarni jo'nating."
            ),
            expected_output="An elegant markdown response in Uzbek welcoming the guest and offering assistance.",
            agent=guest_agent
        )
        
        crew = Crew(
            agents=[guest_agent],
            tasks=[task_guest],
            verbose=True
        )
        
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, crew.kickoff)
            return str(result)
        except Exception as e:
            logger.error(f"Guest CrewAI execution error: {e}")
            return "👋 **Assalomu alaykum!**\n\nBoshliqning shaxsiy yordamchisi tarmoqda. Xabaringiz qabul qilindi, tez orada Boshliq siz bilan bog'lanadi!"

    async def execute_personal_reply_async(self, instruction: str) -> str:
        """
        Executes a personal direct message reply task using a highly optimized,
        conversational CrewAI agent that mimics a real person's communication style.
        """
        import os
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        claude_llm = self._initialize_claude_llm()
        
        from crewai import Agent, Task, Crew
        
        # Define the highly customized Boss AI Responder Agent!
        boss_responder = Agent(
            role="Shaxsiy Telegram Avtomatik Javob Agenti (Boss AI Brain)",
            goal="Foydalanuvchining shaxsiy Telegram profilidan yozilgan xabarlarga xuddi u kabi juda tabiiy, samimiy, norasmiy va oqilona javob qaytarish.",
            backstory=(
                "Siz ushbu Telegram akkaunti egasi (Boshliq) bo'lgan insonning o'zini simulyatsiya qilyapsiz. "
                "Sizning xatti-harakatlaringiz, muloqot ohangingiz va uslubingiz xuddi uniki kabi bo'lishi shart.\n\n"
                "SIZNING MULTI-AGENT PROMPTINGIZ (MUST FOLLOW):\n"
                "1. **Mantiqiy Kontekst**: Kelgan xabar va suhbat tarixining umumiy oqimini juda chuqur tushunib oling.\n"
                "2. **Insoniy Hazil**: Agarda suhbatdosh hazil qilsa, siz ham samimiy hazil-mutoyiba bilan, hazilni davom ettirgan holda qisqa javob yozing.\n"
                "3. **Real Odam Uslubi**: Yozish uslubingiz kitobiy yoki robotdek bo'lmasin. Norasmiy, tabiiy o'zbek tilida gaplashadigan haqiqiy odamdek yozing (masalan, 'raxmat', 'chiqamiz', 'ertaqa', 'ertaga gaplashamiz', 'nima gap', 'bo'ldi aka').\n"
                "4. **Qisqa Yozish (Conciseness)**: Real Telegram foydalanuvchilari hech qachon uzun paragraflarda yozmaydi. Har bir javobingiz maksimal 1-2 ta qisqa gapdan iborat bo'lsin.\n"
                "5. **Suhbatni Davom Ettirish**: Suhbat to'xtab qolmasligi uchun kerak bo'lsa oxirida qisqa, qiziqarli savol qoldiring.\n"
                "6. **AI Ekanligingizni Yashiring**: Hech qachon, hech qanday holatda o'zingizni AI, yordamchi bot, yoki sun'iy intellekt ekanligingizni aytmang yoki bildirmang. O'zingizni xuddi profilingiz egasi (haqiqiy inson) kabi tuting.\n"
                "CRITICAL: Barcha muloqot va javoblar faqat va qat'iy O'ZBEK TILIDA bo'lishi shart!"
            ),
            llm=claude_llm,
            verbose=True,
            memory=False
        )
        
        task_reply = Task(
            description=(
                f"Suhbatdosh sizga quyidagi xabarni yozdi: '{instruction}'.\n"
                f"Unga shaxsiy profilingiz nomidan, yuqoridagi qat'iy qoidalarga rioya qilgan holda qisqa va premium darajadagi tabiiy javob tayyorlang."
            ),
            expected_output="A single short human-like Uzbek chat reply to be sent directly on Telegram.",
            agent=boss_responder
        )
        
        crew = Crew(
            agents=[boss_responder],
            tasks=[task_reply],
            verbose=True
        )
        
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(None, crew.kickoff)
            return str(result)
        except Exception as e:
            logger.error(f"Personal reply CrewAI execution error: {e}")
            return "Salom! Biroz band edim, tez orada o'zim aloqaga chiqaman!"

# Instantiate global orchestrator
crew_orchestrator = CrewOrchestrator()

