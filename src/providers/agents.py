from chains import ChainManager
from llms import LLMManager


class AgentManager:
    @staticmethod
    def get_agents(tools: str, agent_name: str):
        llm = LLMManager.get_llm(model="gemini-2.5-flash")
        llm_with_tools = llm.bind_tools(tools)
        return ChainManager.get_agent_chain(llm_with_tools, agent_name)
