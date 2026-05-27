import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Telegram Bot Token
    telegram_bot_token: str = Field(default="YOUR_TOKEN", validation_alias="TELEGRAM_BOT_TOKEN")
    
    # Authorized Users
    admin_ids_str: str = Field(default="123456789", validation_alias="ADMIN_IDS")

    @property
    def admin_ids(self) -> List[int]:
        try:
            return [int(x.strip()) for x in self.admin_ids_str.split(",") if x.strip()]
        except ValueError:
            return []

    # API Keys
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")

    # Telegram API for Userbot
    telegram_api_id: str = Field(default="", validation_alias="TELEGRAM_API_ID")
    telegram_api_hash: str = Field(default="", validation_alias="TELEGRAM_API_HASH")
    userbot_delay_seconds: int = Field(default=60, validation_alias="USERBOT_DELAY_SECONDS")
    composio_api_key: str = Field(default="", validation_alias="COMPOSIO_API_KEY")



    # Local Database URLs
    database_url: str = Field(default="sqlite:///d:/ai_robot/pi/storage/db.sqlite3", validation_alias="DATABASE_URL")
    chromadb_dir: str = Field(default="d:/ai_robot/pi/storage/chroma", validation_alias="CHROMADB_DIR")

    # FastAPI settings
    fastapi_host: str = Field(default="127.0.0.1", validation_alias="FASTAPI_HOST")
    fastapi_port: int = Field(default=8000, validation_alias="FASTAPI_PORT")

    # Security Controls
    gui_failsafe: bool = Field(default=True, validation_alias="GUI_FAILSAFE")
    strict_command_whitelist: bool = Field(default=True, validation_alias="STRICT_COMMAND_WHITELIST")

# Instantiate settings
settings = Settings()

# Ensure storage directory exists
os.makedirs("d:/ai_robot/pi/storage", exist_ok=True)
