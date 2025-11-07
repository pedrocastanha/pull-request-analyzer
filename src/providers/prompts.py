from langchain_core.prompts import MessagesPlaceholder, ChatPromptTemplate


class PromptManager:
    def get_agent_prompt(agent_name):
        prompt_text = agent_name.SYSTEM_MESSAGE
        return ChatPromptTemplate.from_messages(
            [
                ("system", prompt_text),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
