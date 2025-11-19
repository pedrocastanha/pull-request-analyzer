from typing import List
from src.providers.chains import ChainManager
from src.providers.llms import LLMManager
from src.utils.callbacks import ToolMonitorCallback


class AgentManager:
    @staticmethod
    def get_agents(tools: List, agent_name: str):
        llm = LLMManager.get_llm(model="gpt-4.1")
        return ChainManager.get_agent_executor(llm, tools, agent_name)

    @staticmethod
    def get_callback(verbose: bool = True) -> ToolMonitorCallback:
        return ToolMonitorCallback(verbose=verbose)
