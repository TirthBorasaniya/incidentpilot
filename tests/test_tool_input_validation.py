"""Tests asserting that LLM-supplied tool arguments are validated at the tool
boundary, in particular that path traversal in the service name is rejected."""

import json
import os

import pytest

os.environ.setdefault("LOG_DIR", "/tmp/incidentpilot-test-logs")

from src.agent.tools.logs_tool import query_logs
from src.agent.tools.validation import (
    KNOWN_SERVICES_SET,
    ToolInputError,
    resolve_within_directory,
    validate_int_range,
    validate_service,
    validate_text,
)

# ============= Fixtures =============

TRAVERSAL_ATTEMPTS_LIST = [
    "../../etc/passwd",
    "../../../etc/hosts",
    "..%2f..%2fetc%2fpasswd",
    "/etc/passwd",
    "model-server/../../../etc/passwd",
    "....//....//etc/passwd",
    "model-server\x00../../etc/passwd",
    "~/.ssh/id_rsa",
]


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    """Point LOG_DIR at a temporary directory holding one known service log."""
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    log_line = json.dumps(
        {"timestamp": "2099-01-01T00:00:00", "level": "ERROR", "message": "boom"}
    )
    (tmp_path / "model-server.jsonl").write_text(log_line + "\n")
    return tmp_path


# ============= Path traversal =============


@pytest.mark.parametrize("hostile_service", TRAVERSAL_ATTEMPTS_LIST)
def test_query_logs_rejects_traversal_in_service(hostile_service, log_dir):
    """A traversal attempt in service is rejected rather than read."""
    result = query_logs.invoke(
        {"service": hostile_service, "pattern": "root", "window_minutes": 30}
    )

    assert result.startswith("Rejected query_logs call:")
    assert "unknown service" in result


@pytest.mark.parametrize("hostile_service", TRAVERSAL_ATTEMPTS_LIST)
def test_traversal_never_reaches_the_filesystem(hostile_service, log_dir):
    """The rejection happens before any file outside LOG_DIR is opened."""
    with pytest.raises(ToolInputError):
        validate_service(hostile_service)


def test_escaping_path_is_caught_by_containment_check(tmp_path):
    """resolve_within_directory rejects a path that leaves the base directory."""
    with pytest.raises(ToolInputError, match="escapes the permitted directory"):
        resolve_within_directory(str(tmp_path), f"{tmp_path}/../outside.jsonl")


def test_containment_check_allows_paths_inside_base(tmp_path):
    """A path inside the base directory resolves normally."""
    resolved = resolve_within_directory(str(tmp_path), f"{tmp_path}/model-server.jsonl")

    assert resolved.startswith(os.path.realpath(str(tmp_path)))


# ============= Allowlist =============


def test_known_services_are_accepted():
    """Every allowlisted service passes validation unchanged."""
    for service in KNOWN_SERVICES_SET:
        assert validate_service(service) == service


def test_query_logs_reads_an_allowlisted_service(log_dir):
    """A valid service on the allowlist is read normally."""
    result = query_logs.invoke(
        {"service": "model-server", "pattern": "boom", "window_minutes": 60}
    )

    assert "boom" in result


def test_non_string_service_is_rejected():
    """A non-string service is rejected before any path is built."""
    with pytest.raises(ToolInputError, match="must be a string"):
        validate_service(None)


# ============= Other tool arguments =============


def test_text_length_is_bounded():
    """Over-long free text is rejected."""
    with pytest.raises(ToolInputError, match="character limit"):
        validate_text("x" * 101, 100, "pattern")


def test_empty_text_is_rejected():
    """Empty or whitespace-only text is rejected."""
    with pytest.raises(ToolInputError, match="must not be empty"):
        validate_text("   ", 100, "pattern")


def test_int_range_is_enforced():
    """Out-of-range integers are rejected at both ends."""
    with pytest.raises(ToolInputError, match="between 1 and 60"):
        validate_int_range(0, 1, 60, "window_minutes")

    with pytest.raises(ToolInputError, match="between 1 and 60"):
        validate_int_range(61, 1, 60, "window_minutes")


def test_bool_is_not_accepted_as_int():
    """A bool must not slip through the integer check."""
    with pytest.raises(ToolInputError, match="must be an integer"):
        validate_int_range(True, 1, 60, "window_minutes")


def test_query_logs_rejects_out_of_range_window(log_dir):
    """An out-of-range window_minutes is rejected with a descriptive message."""
    result = query_logs.invoke(
        {"service": "model-server", "pattern": "boom", "window_minutes": 99999}
    )

    assert result.startswith("Rejected query_logs call:")
    assert "window_minutes" in result
