from crewai import Agent
from config.settings import settings
from config.logger import logger
from tools.registry import tool_registry

class CommsAgent:
    """Specialized Agent for summarizing, report formulation, and multi-channel system alerts."""
    
    def __init__(self, llm=None):
        self.llm = llm

    def get_agent(self) -> Agent:
        from tools.registry import get_crew_tools_resolved
        comms_tools = get_crew_tools_resolved(["file_manager"])
        
        return Agent(
            role="Information Aggregator and Communicator",
            goal="Condense complex data, generate markdown reports, write telegram responses, and summarize execution telemetry.",
            backstory=(
                "You are an elegant information synthesizer. You take command outputs, log files, system statistics, "
                "or raw user questions, and convert them into beautifully structured, actionable reports. "
                "You translate developer jargon into concise bullet points, highlighting warnings or success criteria."
            ),
            tools=comms_tools,
            llm=self.llm,
            verbose=True,
            memory=False
        )
