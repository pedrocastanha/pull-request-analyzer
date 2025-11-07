from chains import ChainManager
from llms import LLMManager


class AgentManager:
    @staticmethod
    def get_agents(tools: str):
        llm = LLMManager.get_openai_llm(model="gpt-4.1-mini")
        llm_with_tools = llm.bind_tools(tools)
        return ChainManager.get_agent_chain(llm_with_tools)
