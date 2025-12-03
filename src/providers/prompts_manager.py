from langchain_core.prompts import ChatPromptTemplate
from src.providers.prompts.performance import Performance
from src.providers.prompts.clean_coder import CleanCoder
from src.providers.prompts.security import Security
from src.providers.prompts.logical import Logical
from src.providers.prompts.reviewer import Reviewer
from src.providers.prompts.api_design import APIDesignAnalyst
from src.providers.prompts.error_handling import ErrorHandlingAnalyst


class PromptManager:
    @staticmethod
    def get_agent_prompt(agent_name: str, project_type: str = "java"):
        prompt_classes = {
            "CleanCoder": CleanCoder,
            "Security": Security,
            "Logical": Logical,
            "Performance": Performance,
            "Reviewer": Reviewer,
            "APIDesignAnalyst": APIDesignAnalyst,
            "ErrorHandlingAnalyst": ErrorHandlingAnalyst,
        }

        if agent_name not in prompt_classes:
            raise ValueError(
                f"Agent name '{agent_name}' não encontrado. "
                f"Opções: {list(prompt_classes.keys())}"
            )

        prompt_class = prompt_classes[agent_name]

        if hasattr(prompt_class, "get_prompt"):
            prompt_text = prompt_class.get_prompt(project_type)
        else:
            prompt_text = prompt_class.SYSTEM_PROMPT

        if not prompt_text or prompt_text.strip() == "":
            prompt_text = f"""
            Você é um especialista em análise de código focado em {agent_name}.
            Analise o Pull Request fornecido e forneça insights relevantes.
            """

        return ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                ("human", "{context}"),
            ]
        )
