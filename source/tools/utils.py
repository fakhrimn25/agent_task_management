from typing import *
from pydantic import BaseModel, Field

class OutputAgentTaskManagement(BaseModel):
    message: str = Field(
        default="OK",
        description=(
            "Status message of the content generation request. "
            "Use 'OK' if the request is valid and within scope. "
            "If the request is outside scope, return: "
            "'I'm sorry, but I am designed to generate social media content "
            "in the form of posts or comments.'"
        )
    )
    content: List[str] = Field(
        default_factory=list,
        description=(
            "A list of generated content items. Must always be returned as a list, "
            "even if it contains only one item. "
            "If the user specifies how many, generate exactly that number (up to a maximum of 5 if images are included). "
            "If the request is outside scope, "
            "return an empty list."
        )
    )

class ATMFormat(BaseModel):
    """
    Schema for representing task management input.
    Each field is expected to be a list where each index corresponds
    to one complete task entry.
    """
    name: List[str] = Field(
        description="List of user names (assignees) responsible for the tasks."
    )
    project_name: List[str] = Field(
        description="List of project names associated with each task."
    )
    task: List[str] = Field(
        description=(
            "List of task categories for each sub-task. "
            "Allowed categories include: Research, Project, Maintenance, "
            "Delivery, Pitching, Development, or any other suitable category."
        )
    )
    sub_task: List[str] = Field(
        description="List of detailed sub-tasks being worked on by the user."
    )
    assignor: List[Optional[str]] = Field(
        description="List of assignors (persons who assigned the task). Can be null if not specified."
    )

class CTMFormat(BaseModel):
    name: str = Field(
        description="The name of the user whose tasks should be checked."
    )