# src/pi/crew.py

import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from config.settings import settings
from tools.registry import get_crew_tools_resolved

@CrewBase
class PiCrew():
    """Pi core automation crew"""
    
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    def __init__(self) -> None:
        # Dynamically inject API keys into the OS environment so CrewAI can read them
        if settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
        if settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

    def _get_manager_llm(self):
        """Loads Anthropic Claude-Sonnet-4-6 for the Central Boss Manager/Reasoner"""
        if settings.anthropic_api_key:
            return "anthropic/claude-sonnet-4-6"
        if settings.openai_api_key:
            return "openai/gpt-4o"
        return None

    def _get_worker_llm(self):
        """Loads OpenAI GPT-4o for worker agents"""
        if settings.openai_api_key:
            return "openai/gpt-4o"
        if settings.anthropic_api_key:
            return "anthropic/claude-sonnet-4-6"
        return None

    @agent
    def boss_ai(self) -> Agent:
        return Agent(
            config=self.agents_config['boss_ai'],
            llm=self._get_manager_llm(),
            tools=get_crew_tools_resolved(["safe_shell_runner", "desktop_controller", "system_screenshotter", "file_manager"]),
            verbose=True,
            memory=True
        )

    @agent
    def reply_sender_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['reply_sender_agent'],
            llm=self._get_worker_llm(),
            verbose=True,
            memory=True
        )

    @task
    def analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config['analysis_task'],
            agent=self.boss_ai()
        )

    @task
    def reply_task(self) -> Task:
        return Task(
            config=self.tasks_config['reply_task'],
            agent=self.reply_sender_agent()
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Pi automation crew"""
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )
