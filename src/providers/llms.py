from typing import Type
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.settings import Settings


class LLMManager:
    @staticmethod
    def get_llm(model: str):
        return ChatOpenAI(
            model=model,
            temperature=0.3,
            openai_api_key=Settings.OPENAI_API_KEY
        )

    @staticmethod
    def get_structured_llm(model: str, schema: Type[BaseModel]):
        llm = ChatOpenAI(
            model=model,
            temperature=0.3,
            openai_api_key=Settings.OPENAI_API_KEY
        )
        return llm.with_structured_output(schema)
