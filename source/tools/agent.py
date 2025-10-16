import os
import sys
import srsly
from typing import *
from configparser import ConfigParser
from langchain_core.messages import BaseMessage
from langchain.tools.base import StructuredTool
from langgraph.prebuilt import create_react_agent
from langchain.schema.runnable.config import RunnableConfig

path_this = os.path.dirname(os.path.abspath(__file__))
path_project = os.path.dirname(os.path.join(path_this, ".."))
path_root = os.path.dirname(os.path.join(path_this, "../.."))
sys.path.extend([path_root, path_project, path_this])

from tools import (
    BaseTaskManagement, 
    SpreadsheetTool
)
from tools.utils import (
    ATMFormat,
    CTMFormat
)

class AgentTaskManagement(BaseTaskManagement):
    """
    """

    config: ClassVar[ConfigParser] = ConfigParser()
    config.read(os.path.join(path_root, "config.conf"))

    llm: Any
    checkpoint: Optional[Any] = None

    async def _run(self, command: str, callbacks: list = []):
        """
        Execute the agent using a natural language command as input.

        Args:
            command (str): The natural language input/query to process.

        Returns:
            dict: The final result from the agent after processing the command.
        """
        async def pre_model_hook(state: dict, **kwargs) -> dict:
            """
            Hook executed before model inference. Prepares a list of recent messages
            for use as input to the language model.

            Args:
                state (dict): The current agent state including full message history.
                **kwargs: Additional optional keyword arguments.

            Returns:
                dict: Dictionary with key 'llm_input_messages' containing recent messages.
            """
            messages: List[BaseMessage] = state["messages"]

            cleaned_messages = []
            i = 0
            while i < len(messages):
                msg = messages[i]

                if msg.type == "assistant" and getattr(msg, "tool_calls", None):
                    cleaned_messages.append(msg)
                    if i + 1 < len(messages) and messages[i + 1].type == "tool":
                        cleaned_messages.append(messages[i + 1])
                        i += 1 
                elif msg.type in ["user", "assistant"]:
                    cleaned_messages.append(msg)
                i += 1

            last_messages = cleaned_messages[-6:] if len(cleaned_messages) > 6 else cleaned_messages
            return {"llm_input_messages": last_messages}

        task_management = SpreadsheetTool()
        tools = [
            StructuredTool.from_function(
                name="add_task_management",
                func=task_management.input_task_management,
                description=(
                    "Tool for adding task management entries to Google Spreadsheet.\n\n"
                    "Expected input fields:\n"
                    "- name: List[str] → List of user names (assignees) responsible for the tasks.\n"
                    "- project_name: List[str] → List of project names associated with each task.\n"
                    "- task: List[str] → List of task categories for each sub-task. "
                    "Allowed categories: Research, Project, Maintenance, Delivery, "
                    "Pitching, Development, or any other suitable category.\n"
                    "- sub_task: List[str] → List of detailed sub-tasks being worked on by the user.\n"
                    "- assignor: List[Optional[str]] → List of assignors (task givers). "
                    "Can be null if not specified."
                ),
                coroutine=task_management.input_task_management,
                args_schema=ATMFormat
            ),
            StructuredTool.from_function(
                name="check_task_management",
                func=task_management.get_undone_task,
                description=(
                    "Tool to check whether a user still has any unfinished tasks. "
                    "Input should be the name of the user."
                ),
                coroutine=task_management.get_undone_task,
                args_schema=CTMFormat
            )
        ]

        path_json = os.path.join(path_root, self.config["default"]["agent_system_messages_path_general"])
        prompts = srsly.read_json(path_json)
        agent_executor = create_react_agent(
            model=self.llm,
            tools=tools,
            checkpointer=self.checkpoint,
            pre_model_hook=pre_model_hook,
            prompt=prompts["agent_task"]["system_message"],
            # response_format=OutputAgentTaskManagement
        )

        config = {"configurable": {"thread_id": "task_tim_john"}}
        config_stream = RunnableConfig(callbacks=callbacks, **config) if callbacks else config
        async for step in agent_executor.astream(
            {"messages": [{"role":"user","content":command}]},
            config=config_stream,
            stream_mode="values"
        ):
            final_answer = step.get("messages")[-1].content if step.get("messages") else None
        return final_answer