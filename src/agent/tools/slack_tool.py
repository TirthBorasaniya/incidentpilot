"""Tool for posting incident diagnosis to a Slack channel."""

import os

from langchain_core.tools import tool
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.agent.tools.validation import (
    MAX_SLACK_MESSAGE_CHARS,
    ToolInputError,
    validate_text,
)


@tool
def post_slack(message: str) -> str:
    """
    Post a formatted diagnosis message to the configured Slack channel.

    Parameters
    ----------
    message : str
        The full diagnosis and recommended action text.

    Returns
    -------
    result : str
        Confirmation string or error message.
    """
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_channel = os.environ["SLACK_CHANNEL"]

    try:
        message = validate_text(message, MAX_SLACK_MESSAGE_CHARS, "message")
    except ToolInputError as error:
        return f"Rejected post_slack call: {error}"

    try:
        client = WebClient(token=slack_token)
        client.chat_postMessage(channel=slack_channel, text=message)
        return f"Posted diagnosis to {slack_channel}."
    except SlackApiError as error:
        return f"Failed to post to Slack: {error}"
