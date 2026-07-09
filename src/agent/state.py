"""TypedDict definition for LangGraph agent state."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    incident_id: str
    alert_name: str
    labels_dict: dict[str, str]
    annotations_dict: dict[str, str]
    messages: Annotated[list[BaseMessage], operator.add]
    tool_outputs_list: list[dict]
    diagnosis: str
    recommended_action: str
    iteration_count: int
