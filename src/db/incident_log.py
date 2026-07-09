"""SQLite-backed incident log for persisting agent runs."""

import json
import os
import sqlite3

# ============= Constants =============

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS incidents (
    id          TEXT PRIMARY KEY,
    alert_name  TEXT NOT NULL,
    alert_labels    TEXT NOT NULL,
    alert_annotations   TEXT NOT NULL,
    diagnosis       TEXT,
    recommended_action  TEXT,
    runbooks_used   TEXT,
    tool_calls_log  TEXT,
    status      TEXT DEFAULT 'open',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def _get_db_path() -> str:
    """One-line helper returning the configured database path."""
    return os.environ["DB_PATH"]


# ============= Public API =============


def init_db(db_path: str) -> None:
    """
    Create the incidents table if it does not already exist.

    Parameters
    ----------
    db_path : str
        Filesystem path to the SQLite database file.
    """
    connection = sqlite3.connect(db_path)
    connection.execute(CREATE_TABLE_SQL)
    connection.commit()
    connection.close()


def log_incident(
    incident_id: str,
    alert_name: str,
    labels_dict: dict,
    annotations_dict: dict,
) -> None:
    """
    Insert the initial incident record before the agent has produced a diagnosis.

    Parameters
    ----------
    incident_id : str
        Unique identifier for the incident.
    alert_name : str
        Name of the fired Prometheus alert.
    labels_dict : dict
        Alert labels as key-value pairs.
    annotations_dict : dict
        Alert annotations as key-value pairs.
    """
    connection = sqlite3.connect(_get_db_path())
    connection.execute(
        """
        INSERT INTO incidents (id, alert_name, alert_labels, alert_annotations)
        VALUES (?, ?, ?, ?)
        """,
        (incident_id, alert_name, json.dumps(labels_dict), json.dumps(annotations_dict)),
    )
    connection.commit()
    connection.close()


def update_incident(
    incident_id: str,
    diagnosis: str,
    recommended_action: str,
    runbooks_used_list: list,
    tool_calls_list: list,
) -> None:
    """
    Update an incident record with the agent's final diagnosis and evidence.

    Parameters
    ----------
    incident_id : str
        Unique identifier for the incident being updated.
    diagnosis : str
        Root cause diagnosis text produced by the agent.
    recommended_action : str
        Recommended remediation action produced by the agent.
    runbooks_used_list : list
        Titles of runbooks consulted during diagnosis.
    tool_calls_list : list
        Log of tool calls made during the agent run.
    """
    connection = sqlite3.connect(_get_db_path())
    connection.execute(
        """
        UPDATE incidents
        SET diagnosis = ?, recommended_action = ?, runbooks_used = ?,
            tool_calls_log = ?, status = 'resolved'
        WHERE id = ?
        """,
        (
            diagnosis,
            recommended_action,
            json.dumps(runbooks_used_list),
            json.dumps(tool_calls_list),
            incident_id,
        ),
    )
    connection.commit()
    connection.close()


def get_incident(incident_id: str) -> dict | None:
    """
    Retrieve an incident record by id.

    Parameters
    ----------
    incident_id : str
        Unique identifier for the incident to retrieve.

    Returns
    -------
    incident_dict : dict | None
        Incident record as a dict, or None if not found.
    """
    connection = sqlite3.connect(_get_db_path())
    connection.row_factory = sqlite3.Row
    cursor = connection.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return dict(row)
