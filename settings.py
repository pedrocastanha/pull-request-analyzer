import os
from typing import ClassVar
from pydantic import BaseModel

class SharedSettings(BaseModel):
    """Configuração geral do sistema"""

    GEMINI_API_KEY: ClassVar[str | None] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: ClassVar[str | None] = os.getenv("GEMINI_MODEL")
    GEMINI_TEMPERATURE: ClassVar[str | None] = os.getenv("GEMINI_TEMPERATURE")

    SERPAPI_API_KEY: ClassVar[str | None] = os.getenv("SERPAPI_API_KEY")
    SERPAPI_BASE_URL: ClassVar[str] = os.getenv("SERPAPI_BASE_URL")

    PINECONE_INDEX_NAME: ClassVar[str | None] = os.getenv("PINECONE_INDEX_NAME")
    PINECONE_API_KEY: ClassVar[str | None] = os.getenv("PINECONE_API_KEY")


    llm_max_tokens: ClassVar[int] = 4000

    github_token: ClassVar[str | None] = os.getenv("GITHUB_TOKEN")
    anthropic_api_key: ClassVar[str | None] = os.getenv("ANTHROPIC_API_KEY")

    github_max_files: ClassVar[int] = 50
    github_max_file_size: ClassVar[int] = 1024 * 1024
    github_rate_limit: ClassVar[int] = 60

    analysis_timeout: ClassVar[int] = 300
    parallel_analyses: ClassVar[bool] = True
    save_detailed_logs: ClassVar[bool] = True

    enabled_categories: ClassVar[list[str]] = ["security", "quality", "performance", "tests"]