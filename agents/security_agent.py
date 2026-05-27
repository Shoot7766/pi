from crewai import Agent
from config.settings import settings
from config.logger import logger

class SecurityAgent:
    """Specialized Agent for system permissions, security analysis, and command approval auditing."""
    
    def __init__(self, llm=None):
        self.llm = llm

    def get_agent(self) -> Agent:
        return Agent(
            role="Cybersecurity and Permissions Auditor",
            goal="Thoroughly inspect proposed terminal commands, explain security risks, and verify safety bounds before system execution on Windows.",
            backstory=(
                "You are an elite system security auditor. You analyze system commands (CMD, PowerShell), "
                "file modifications, and GUI actions. You evaluate if they are safe, explain their exact consequences "
                "in simple terms, and verify if they are destructive or safe to proceed. You work alongside the "
                "administrator to keep the desktop operating system completely secure."
            ),
            llm=self.llm,
            verbose=True,
            memory=False
        )
