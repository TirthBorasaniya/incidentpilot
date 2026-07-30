"""Tool for querying Prometheus via the HTTP query_range API."""

import json
import os

import httpx
from langchain_core.tools import tool

from src.agent.tools.validation import (
    MAX_PROMQL_CHARS,
    MAX_WINDOW_MINUTES,
    MIN_WINDOW_MINUTES,
    ToolInputError,
    validate_int_range,
    validate_text,
)


@tool
def query_prometheus(promql: str, lookback_minutes: int = 30) -> str:
    """
    Execute a PromQL instant query against Prometheus.

    Parameters
    ----------
    promql : str
        Valid PromQL expression to evaluate.
    lookback_minutes : int
        How many minutes back to set the query time range. Used for
        range queries only. For instant queries, evaluates at now.

    Returns
    -------
    result : str
        JSON-serialized list of metric result dicts, or an error message.
    """
    prometheus_url = os.environ["PROMETHEUS_URL"]

    try:
        promql = validate_text(promql, MAX_PROMQL_CHARS, "promql")
        lookback_minutes = validate_int_range(
            lookback_minutes, MIN_WINDOW_MINUTES, MAX_WINDOW_MINUTES, "lookback_minutes"
        )
    except ToolInputError as error:
        return f"Rejected query_prometheus call: {error}"

    try:
        response = httpx.get(
            f"{prometheus_url}/api/v1/query",
            params={"query": promql, "time": "now"},
        )
        result_list = response.json()["data"]["result"]
        return json.dumps(result_list, indent=2)
    except httpx.RequestError as error:
        return f"Failed to reach Prometheus: {error}"
    except KeyError as error:
        return f"Unexpected Prometheus response shape, missing key: {error}"
