import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"

    # Security & Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "knoquest-enterprise-secure-session-key-2026-prod-novatech")
    SESSION_MAX_AGE_SECONDS: int = 28800  # 8 hours
    DEV_DEFAULT_PASSWORD: str = os.getenv("DEV_DEFAULT_PASSWORD", "NovaTech@2026!")

    # Execution Mode: true for Azure Foundry & Search; false for local enterprise sandbox
    AZURE_MODE: bool = False

    # Microsoft Foundry Settings
    AZURE_PROJECT_ENDPOINT: str = ""
    AZURE_PROJECT_CONNECTION_STRING: str = ""
    AZURE_MODEL_DEPLOYMENT_NAME: str = "gpt-4o-mini"

    # Azure OpenAI Direct Settings
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    AZURE_EMBEDDING_DEPLOYMENT_NAME: str = "text-embedding-3-large"
    AZURE_EMBEDDING_DIMENSIONS: int = 3072

    # Azure AI Search Settings
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_API_KEY: str = ""
    AZURE_SEARCH_INDEX_NAME: str = "knoquest-novatech-index"

    # Azure Speech Settings
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = "centralindia"

    # Security
    USE_AZURE_CREDENTIAL: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
