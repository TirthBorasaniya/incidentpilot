"""Tool for searching structured JSON log files by service and pattern."""

import json
import os
from datetime import datetime, timedelta, timezone

from langchain_core.tools import tool

from src.agent.tools.validation import (
    MAX_PATTERN_CHARS,
    MAX_WINDOW_MINUTES,
    MIN_WINDOW_MINUTES,
    ToolInputError,
    resolve_within_directory,
    validate_int_range,
    validate_service,
    validate_text,
)

MAX_MATCHING_LINES = 20


@tool
def query_logs(service: str, pattern: str, window_minutes: int = 30) -> str:
    """
    Search structured JSON log lines for a pattern within a time window.

    Parameters
    ----------
    service : str
        Service name, which must appear on the known services allowlist. Used
        to locate the log file at {LOG_DIR}/{service}.jsonl.
    pattern : str
        String to search for in the raw log line text.
    window_minutes : int
        Only return log lines from the past window_minutes minutes.

    Returns
    -------
    result : str
        Newline-joined matching log lines, or a message if none found.
    """
    log_dir = os.environ["LOG_DIR"]

    try:
        service = validate_service(service)
        pattern = validate_text(pattern, MAX_PATTERN_CHARS, "pattern")
        window_minutes = validate_int_range(
            window_minutes, MIN_WINDOW_MINUTES, MAX_WINDOW_MINUTES, "window_minutes"
        )
        log_path = resolve_within_directory(log_dir, f"{log_dir}/{service}.jsonl")
    except ToolInputError as error:
        return f"Rejected query_logs call: {error}"

    if not os.path.exists(log_path):
        return f"No log file found for service {service}."

    # naive UTC, matching the timestamps written by the simulation harness
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    cutoff_time = now_utc - timedelta(minutes=window_minutes)
    matching_lines_list: list[str] = []

    with open(log_path, "r") as log_file:
        for raw_line in log_file:
            if len(matching_lines_list) >= MAX_MATCHING_LINES:
                break

            try:
                line_dict = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            line_timestamp = datetime.fromisoformat(line_dict["timestamp"])
            in_window = line_timestamp >= cutoff_time
            matches_pattern = pattern.lower() in raw_line.lower()

            if in_window and matches_pattern:
                matching_lines_list.append(raw_line.strip())

    if not matching_lines_list:
        return f"No matching log lines found for service {service} with pattern {pattern}."

    return "\n".join(matching_lines_list)
