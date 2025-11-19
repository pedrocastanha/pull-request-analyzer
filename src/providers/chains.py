from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.providers.prompts_manager import PromptManager


class ChainManager:
    @staticmethod
    def get_agent_chain(llm, agent_name):
        agent_prompt = PromptManager.get_agent_prompt(agent_name)
        return agent_prompt | llm

    @staticmethod
    def get_agent_executor(llm, tools, agent_name):
        base_prompt = PromptManager.get_agent_prompt(agent_name)

        prompt_with_tools = ChatPromptTemplate.from_messages(
            [
                ("system", base_prompt.messages[0].prompt.template),
                ("human", "{context}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(
            llm=llm, tools=tools, prompt=prompt_with_tools
        )

        return AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            handle_parsing_errors=True,
            max_iterations=5
        )
