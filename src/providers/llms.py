from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.settings import Settings


class LLMManager:
    @staticmethod
    def get_llm(model: str):
        # return ChatOpenAI(
        #     model = model,
        #     temperature=0.3,
        #     openai_api_key= Settings.OPENAI_API_KEY
        # )
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.3,
            google_api_key=Settings.GOOGLE_GENAI_API_KEY,
        )
