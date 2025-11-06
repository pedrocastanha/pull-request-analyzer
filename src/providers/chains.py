from prompts import PromptManager


class ChainManager:
    @staticmethod
    def get_agent_chain(llm_with_tools, agent_name):
        agent_promp = PromptManager.get_agent_prompt(agent_name)
        return agent_promp | llm_with_tools