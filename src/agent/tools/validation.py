"""Input validation helpers applied at the tool boundary, since tool arguments
are produced by the LLM and are therefore untrusted."""

import os

# ============= Constants =============

# services the agent is allowed to read logs for; an allowlist removes the
# path traversal class of bug rather than patching one instance of it
KNOWN_SERVICES_SET = frozenset(
    {
        "model-server",
        "drift-monitor",
        "retraining-pipeline",
        "feast-server",
    }
)

MAX_PROMQL_CHARS = 1000
MAX_PATTERN_CHARS = 200
MAX_QUERY_CHARS = 500
MAX_SLACK_MESSAGE_CHARS = 35000

MIN_WINDOW_MINUTES = 1
MAX_WINDOW_MINUTES = 1440


class ToolInputError(ValueError):
    """Raised when an LLM-supplied tool argument fails validation."""


# ============= Validators =============


def validate_service(service: str) -> str:
    """
    Check a service name against the allowlist of known services.

    Parameters
    ----------
    service : str
        Service name supplied by the model.

    Returns
    -------
    service : str
        The validated service name, unchanged.

    Raises
    ------
    ToolInputError
        If the service is not a string or is not on the allowlist.
    """
    if not isinstance(service, str):
        raise ToolInputError("service must be a string")

    if service not in KNOWN_SERVICES_SET:
        allowed = ", ".join(sorted(KNOWN_SERVICES_SET))
        raise ToolInputError(
            f"unknown service {service!r}, allowed services are: {allowed}"
        )

    return service


def resolve_within_directory(base_dir: str, candidate_path: str) -> str:
    """
    Resolve a path and assert it stays inside a base directory.

    Defence in depth behind the allowlist, so a future caller that skips
    validate_service still cannot escape the log directory via symlinks or
    relative segments.

    Parameters
    ----------
    base_dir : str
        Directory the resolved path must remain inside.
    candidate_path : str
        Path to resolve and check.

    Returns
    -------
    resolved_path : str
        The fully resolved absolute path.

    Raises
    ------
    ToolInputError
        If the resolved path escapes base_dir.
    """
    resolved_base = os.path.realpath(base_dir)
    resolved_path = os.path.realpath(candidate_path)

    if resolved_path != resolved_base and not resolved_path.startswith(
        resolved_base + os.sep
    ):
        raise ToolInputError("resolved path escapes the permitted directory")

    return resolved_path


def validate_text(value: str, max_chars: int, field_name: str) -> str:
    """
    Check that a free-text argument is a string of bounded length.

    Parameters
    ----------
    value : str
        Text supplied by the model.
    max_chars : int
        Maximum permitted length.
    field_name : str
        Name of the argument, used in the error message.

    Returns
    -------
    value : str
        The validated text, unchanged.

    Raises
    ------
    ToolInputError
        If the value is not a string, is empty, or exceeds max_chars.
    """
    if not isinstance(value, str):
        raise ToolInputError(f"{field_name} must be a string")

    if not value.strip():
        raise ToolInputError(f"{field_name} must not be empty")

    if len(value) > max_chars:
        raise ToolInputError(
            f"{field_name} exceeds the {max_chars} character limit"
        )

    return value


def validate_int_range(value: int, minimum: int, maximum: int, field_name: str) -> int:
    """
    Check that an integer argument falls within an inclusive range.

    Parameters
    ----------
    value : int
        Integer supplied by the model.
    minimum : int
        Lowest permitted value.
    maximum : int
        Highest permitted value.
    field_name : str
        Name of the argument, used in the error message.

    Returns
    -------
    value : int
        The validated integer.

    Raises
    ------
    ToolInputError
        If the value is not an integer or falls outside the range.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ToolInputError(f"{field_name} must be an integer")

    if value < minimum or value > maximum:
        raise ToolInputError(
            f"{field_name} must be between {minimum} and {maximum}"
        )

    return value
