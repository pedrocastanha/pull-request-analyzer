from langchain_core.prompts import ChatPromptTemplate
from src.providers.prompts.performance import Performance
from src.providers.prompts.clean_coder import CleanCoder
from src.providers.prompts.security import Security
from src.providers.prompts.logical import Logical
from src.providers.prompts.reviewer import Reviewer


class PromptManager:
    @staticmethod
    def get_agent_prompt(agent_name: str):
        prompt_classes = {
            "CleanCoder": CleanCoder,
            "Security": Security,
            "Logical": Logical,
            "Performance": Performance,
            "Reviewer": Reviewer,
        }

        if agent_name not in prompt_classes:
            raise ValueError(
                f"Agent name '{agent_name}' não encontrado. "
                f"Opções: {list(prompt_classes.keys())}"
            )

        prompt_class = prompt_classes[agent_name]
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
