
import os
from typing import Dict, Any
from pydantic import BaseModel
import yaml


class Config(BaseModel):
    """Configuração geral do sistema"""

    github_token: str
    anthropic_api_key: str

    github_max_files: int = 50
    github_max_file_size: int = 1024 * 1024
    github_rate_limit: int = 60

    llm_model: str = "claude-3-sonnet-20240229"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4000

    analysis_timeout: int = 300
    parallel_analyses: bool = True
    save_detailed_logs: bool = True

    enabled_categories: list = ["security", "quality", "performance", "tests"]

    @classmethod
    def from_env(cls) -> "Config":
        """Carrega configuração das variáveis de ambiente"""
        return cls(
            github_token=os.getenv("GITHUB_TOKEN", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            llm_model=os.getenv("LLM_MODEL", "claude-3-sonnet-20240229"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
            github_max_files=int(os.getenv("GITHUB_MAX_FILES", "50"))
        )

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Carrega configuração de arquivo YAML"""
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)

        env_config = cls.from_env()
        data.update({
            "github_token": env_config.github_token,
            "anthropic_api_key": env_config.anthropic_api_key
        })

        return cls(**data)

import logging
import sys
from pathlib import Path
from rich.logging import RichHandler
from datetime import datetime


def setup_logger(
        name: str = "pr_analyzer",
        level: str = "INFO",
        log_file: bool = True
) -> logging.Logger:
    """Configura o sistema de logging com Rich"""
    logger = logging.getLogger(name)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    logger.setLevel(getattr(logging, level.upper()))

    rich_handler = RichHandler(
        rich_tracebacks=True,
        tracebacks_show_locals=True
    )
    rich_handler.setFormatter(
        logging.Formatter(
            fmt="%(message)s",
            datefmt="[%X]"
        )
    )
    logger.addHandler(rich_handler)

    if log_file:
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")
        log_filepath = logs_dir / f"pr_analyzer_{timestamp}.log"

        file_handler = logging.FileHandler(log_filepath)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(file_handler)

    return logger