# IncidentPilot

IncidentPilot is an ML-pipeline-specific incident response agent. When a Prometheus
alert fires for drift, latency, retraining failure, feature staleness, or a high
serving error rate, a LangGraph agent gathers evidence from Prometheus, service logs,
and a runbook corpus, then posts a root cause diagnosis to Slack and logs the incident
to SQLite.


## Architecture

```
                    ┌──────────────┐      ┌────────────────┐
                    │  Pushgateway │◄─────│ simulate_incident│
                    └──────┬───────┘      └────────────────┘
                           │ scrape
                           ▼
┌──────────────┐    ┌──────────────┐      ┌───────────────┐
│   Grafana    │◄───│  Prometheus  │─────►│ Alertmanager  │
└──────────────┘    └──────────────┘      └───────┬───────┘
                                                   │ webhook
                                                   ▼
                                        ┌─────────────────────┐
                                        │  FastAPI receiver   │
                                        │ /webhook/alert       │
                                        └──────────┬──────────┘
                                                   │ background task
                                                   ▼
                                        ┌─────────────────────┐
                                        │  LangGraph agent     │
                                        │  analyze → tools →   │
                                        │  synthesize           │
                                        └──────────┬──────────┘
                             ┌─────────────────────┼─────────────────────┐
                             ▼                     ▼                     ▼
                    ┌────────────────┐   ┌──────────────────┐  ┌─────────────────┐
                    │ query_prometheus│   │ query_logs        │  │ search_runbooks  │
                    └────────────────┘   └──────────────────┘  └────────┬─────────┘
                                                                          ▼
                                                                  ┌──────────────┐
                                                                  │    Qdrant     │
                                                                  └──────────────┘
                             │
                             ▼
                    ┌────────────────┐        ┌──────────────┐       ┌───────────────┐
                    │   post_slack    │───────►│    Slack      │       │   Langfuse     │
                    └────────────────┘        └──────────────┘       │  (trace of run) │
                             │                                        └───────────────┘
                             ▼
                    ┌────────────────┐
                    │  SQLite log     │
                    └────────────────┘
```


## Prerequisites

- Docker and Docker Compose
- A Groq API key (https://console.groq.com)
- A Slack bot token with `chat:write` scope, invited to the target channel
- A Langfuse account (cloud or self-hosted) with a public/secret key pair


## Setup

1. Clone the repository and `cd` into it.
2. Copy `.env.example` to `.env` and fill in `GROQ_API_KEY`, `SLACK_BOT_TOKEN`,
   `SLACK_CHANNEL`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST`
   (use `https://us.cloud.langfuse.com` if your Langfuse project is on the US region).
3. Build and start the stack:
   ```
   docker compose build
   docker compose up -d
   ```
4. Index the runbook corpus into Qdrant (run from the host, against `localhost`):
   ```
   pip install fastembed qdrant-client python-dotenv
   QDRANT_URL=http://localhost:6333 python scripts/index_runbooks.py
   ```


## Running a simulation

```
python scripts/simulate_incident.py --scenario drift_detected
```

This writes synthetic log lines and pushes a metric to Pushgateway. Prometheus
evaluates its alert rules on a 30 second interval; once the alert fires, Alertmanager
sends a webhook to IncidentPilot, which runs the agent in the background.

Available scenarios: `serving_latency_spike`, `drift_detected`, `retraining_failure`,
`feature_staleness`, `high_error_rate`.


## What to observe

- **Slack**: the configured channel receives a formatted diagnosis message
  (root cause, evidence, recommended action, runbooks consulted).
- **Langfuse**: a trace of the agent run, showing each LLM call and tool
  invocation in sequence, is visible in your Langfuse project dashboard.
- **SQLite**: query the incident record via the API:
  ```
  curl http://localhost:8000/incidents/<incident_id>
  ```
  or inspect `data/incidents.db` directly with the `sqlite3` CLI.


## Incident scenarios

| Scenario                | Alert fired          | What the agent diagnoses |
|--------------------------|-----------------------|---------------------------|
| `serving_latency_spike`  | ServingLatencyHigh     | P99 latency spike correlated with GPU memory pressure and growing request queue depth; recommends reducing batch size or rolling back the model version. |
| `drift_detected`         | ModelDriftDetected      | PSI score breach on a feature set, tied to an upstream schema change; recommends retraining on the current data distribution. |
| `retraining_failure`     | RetrainingJobFailed     | Training job killed by an OOM condition on the GPU node; recommends resuming from the last valid checkpoint with a reduced memory footprint. |
| `feature_staleness`      | FeatureStalenessHigh    | Feature view has not been materialized recently, traced to Kafka consumer lag blocking the online store refresh; recommends a manual materialization. |
| `high_error_rate`        | ServingErrorRateHigh    | Elevated serving error rate traced to an input schema mismatch between the feature pipeline and the model server; recommends aligning the input contract or rolling back. |


## Stack

| Component               | Role                                              | Why chosen |
|--------------------------|----------------------------------------------------|------------|
| FastAPI                 | Webhook receiver and incident API                  | Lightweight, async-native, minimal boilerplate for a small HTTP surface. |
| LangGraph                | Agent orchestration (analyze/tools/synthesize loop) | Explicit state graph gives deterministic control over tool-calling iteration and routing. |
| Groq (llama-3.1-8b-instant) | LLM for diagnosis synthesis                     | Fast, free-tier-friendly inference suitable for a personal project with no paid cloud dependency. |
| Qdrant + fastembed        | Runbook semantic search                            | Local vector store with no external embedding API required; runs fully in Docker. |
| Prometheus + Alertmanager + Pushgateway | Metrics, alerting, and synthetic incident triggering | Standard, well-documented alerting stack; Pushgateway lets a script simulate failures without a real exporter. |
| Grafana                  | Metrics visualization                              | Pairs directly with the existing Prometheus datasource for ad hoc inspection. |
| SQLite                   | Incident log persistence                           | Zero-configuration embedded database, sufficient for a single-instance personal project. |
| Langfuse                  | LLM observability and tracing                       | Free-tier cloud tracing for inspecting the agent's tool-call sequence per incident. |
| Slack                    | Diagnosis delivery                                  | Familiar incident-response notification channel with a simple bot API. |
