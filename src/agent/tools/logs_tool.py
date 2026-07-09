"""Tool for searching structured JSON log files by service and pattern."""

import json
import os
from datetime import datetime, timedelta

from langchain_core.tools import tool

MAX_MATCHING_LINES = 20


@tool
def query_logs(service: str, pattern: str, window_minutes: int = 30) -> str:
    """
    Search structured JSON log lines for a pattern within a time window.

    Parameters
    ----------
    service : str
        Service name, used to locate the log file at
        {LOG_DIR}/{service}.jsonl.
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
    log_path = f"{log_dir}/{service}.jsonl"

    if not os.path.exists(log_path):
        return f"No log file found for service {service}."

    cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
    matching_lines_list = []

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
