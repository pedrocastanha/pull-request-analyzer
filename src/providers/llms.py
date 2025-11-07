import os

from langchain_google_genai import GoogleGenerativeAI
from langchain_openai import ChatOpenAI

class LLMManager:
    @staticmethod
    def get_openai_llm(model: str):
        return GoogleGenerativeAI(
            model=model,
            temperature=0.3,
            api_key=os.getenv("GOOGLE_GENAI_API_KEY"),
        )

        # return ChatOpenAI(
        #     model=model,
        #     temperature=0.3,
        #     api_key=os.getenv("OPENAI_API_KEY"),
        # )