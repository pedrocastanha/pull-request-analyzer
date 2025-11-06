class LLMManager:
    @staticmethod
    def get_openai_llm(model: str):
        return ChatOpenAI(
            model=model,
            temperature=0.3,
            api_key=os.getenv("OPENAI_API_KEY"),
        )