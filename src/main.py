"""FastAPI application exposing the Alertmanager webhook receiver."""

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from langfuse.callback import CallbackHandler

from src.agent.graph import graph
from src.db.incident_log import get_incident, init_db, log_incident
from src.models.webhook import AlertmanagerWebhookPayload, AlertModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(os.environ["DB_PATH"])
    yield


app = FastAPI(lifespan=lifespan)


def run_agent(incident_id: str, alert: AlertModel) -> None:
    """
    Invoke the LangGraph agent for a single alert and persist the final state.

    Parameters
    ----------
    incident_id : str
        Unique identifier for the incident.
    alert : AlertModel
        The Alertmanager alert to diagnose.
    """
    langfuse_handler = CallbackHandler(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ["LANGFUSE_HOST"],
    )

    initial_state = {
        "incident_id": incident_id,
        "alert_name": alert.labels.get("alertname", "unknown"),
        "labels_dict": alert.labels,
        "annotations_dict": alert.annotations,
        "messages": [],
        "tool_outputs_list": [],
        "diagnosis": "",
        "recommended_action": "",
        "iteration_count": 0,
    }

    graph.invoke(initial_state, config={"callbacks": [langfuse_handler]})


@app.post("/webhook/alert", status_code=202)
async def receive_alert(payload: AlertmanagerWebhookPayload, background_tasks: BackgroundTasks):
    """Receive an Alertmanager webhook payload and dispatch the agent in the background."""
    alert = payload.alerts[0]
    incident_id = str(uuid.uuid4())

    log_incident(
        incident_id=incident_id,
        alert_name=alert.labels.get("alertname", "unknown"),
        labels_dict=alert.labels,
        annotations_dict=alert.annotations,
    )

    background_tasks.add_task(run_agent, incident_id, alert)

    return JSONResponse(
        status_code=202, content={"status": "received", "incident_id": incident_id}
    )


@app.get("/incidents/{incident_id}")
async def get_incident_endpoint(incident_id: str):
    """Return the incident record from SQLite."""
    incident = get_incident(incident_id)

    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


@app.get("/health")
async def health():
    """Return a simple liveness confirmation."""
    return {"status": "ok"}
