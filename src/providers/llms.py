from langchain_google_genai import GoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.settings import Settings


class LLMManager:
    @staticmethod
    def get_llm(model: str):
        return GoogleGenerativeAI(
            model=model,
            temperature=0.3,
            api_key=Settings.GOOGLE_GENAI_API_KEY,
        )

        # return ChatOpenAI(
        #     model=model,
        #     temperature=0.3,
        #     api_key=os.getenv("OPENAI_API_KEY"),
        # )
