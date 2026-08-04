"""Seed synthetic ML pipeline metrics to Prometheus Pushgateway to trigger
Alertmanager alerts and exercise the IncidentPilot agent end-to-end."""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# ============= Scenario definitions =============

SCENARIOS: dict[str, dict] = {
    "serving_latency_spike": {
        "metric": "model_serving_p99_latency_seconds",
        "value": 3.5,
        "labels": {"service": "model-server", "model": "llama-3b"},
        "log_service": "model-server",
        "log_lines": [
            {"timestamp": "<now>", "level": "WARNING", "message":
             "p99 latency 3.5s exceeds SLO of 2.0s"},
            {"timestamp": "<now>", "level": "WARNING", "message":
             "GPU utilization at 97 percent, possible memory pressure"},
            {"timestamp": "<now>", "level": "ERROR", "message":
             "request queue depth 48, approaching concurrency limit of 50"},
        ],
    },
    "drift_detected": {
        "metric": "model_psi_score",
        "value": 0.35,
        "labels": {"service": "drift-monitor",
                   "feature_set": "network_telemetry"},
        "log_service": "drift-monitor",
        "log_lines": [
            {"timestamp": "<now>", "level": "WARNING", "message":
             "PSI score 0.35 exceeds threshold 0.2 on feature_set "
             "network_telemetry"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "top drifted features: bytes_per_second, packet_loss_rate"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "upstream data source changed schema 2 hours ago"},
        ],
    },
    "retraining_failure": {
        "metric": "ml_retraining_job_success",
        "value": 0,
        "labels": {"service": "retraining-pipeline",
                   "job_id": "retrain-20240601-001"},
        "log_service": "retraining-pipeline",
        "log_lines": [
            {"timestamp": "<now>", "level": "ERROR", "message":
             "SLURM job 20240601-001 killed: OOM on node gpu-node-03"},
            {"timestamp": "<now>", "level": "ERROR", "message":
             "peak memory 79.8 GB exceeded A100 limit of 80 GB"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "last valid checkpoint at epoch 12, step 5400"},
        ],
    },
    "feature_staleness": {
        "metric": "ml_feature_freshness_seconds",
        "value": 7200,
        "labels": {"service": "feast-server",
                   "feature_view": "network_telemetry_fv"},
        "log_service": "feast-server",
        "log_lines": [
            {"timestamp": "<now>", "level": "WARNING", "message":
             "feature view network_telemetry_fv last materialized 7200s ago"},
            {"timestamp": "<now>", "level": "ERROR", "message":
             "Kafka consumer group feast-consumer lag 142000 messages"},
            {"timestamp": "<now>", "level": "WARNING", "message":
             "online store may be serving stale features"},
        ],
    },
    # variants below reuse an existing metric and alert rule, changing only the
    # log evidence, so one alert maps to several candidate root causes that the
    # agent has to disambiguate from the logs
    "retraining_checkpoint_missing": {
        "metric": "ml_retraining_job_success",
        "value": 0,
        "labels": {"service": "retraining-pipeline",
                   "job_id": "retrain-20240612-004"},
        "log_service": "retraining-pipeline",
        "log_lines": [
            {"timestamp": "<now>", "level": "ERROR", "message":
             "FileNotFoundError: checkpoint path /mnt/ckpt/run-004/epoch_18.pt "
             "does not exist"},
            {"timestamp": "<now>", "level": "ERROR", "message":
             "job failed at startup before executing any training steps"},
            {"timestamp": "<now>", "level": "WARNING", "message":
             "storage mount /mnt/ckpt reports empty on node gpu-node-07, "
             "volume may not be mounted"},
        ],
    },
    "retraining_loss_divergence": {
        "metric": "ml_retraining_job_success",
        "value": 0,
        "labels": {"service": "retraining-pipeline",
                   "job_id": "retrain-20240613-005"},
        "log_service": "retraining-pipeline",
        "log_lines": [
            {"timestamp": "<now>", "level": "ERROR", "message":
             "training loss became NaN at epoch 4 step 1120"},
            {"timestamp": "<now>", "level": "WARNING", "message":
             "gradient norm spiked to 4.7e+06 in the steps preceding failure"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "learning rate 0.01 with gradient clipping disabled for this run"},
        ],
    },
    "feature_ttl_exceeded": {
        "metric": "ml_feature_freshness_seconds",
        "value": 5400,
        "labels": {"service": "feast-server",
                   "feature_view": "user_engagement_fv"},
        "log_service": "feast-server",
        "log_lines": [
            {"timestamp": "<now>", "level": "WARNING", "message":
             "feature view user_engagement_fv TTL of 3600s exceeded, entries "
             "expired before the next materialization window"},
            {"timestamp": "<now>", "level": "WARNING", "message":
             "online store returned null for 38 percent of entity lookups"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "materialization job interval 7200s is longer than the "
             "configured TTL, Kafka consumer lag is zero"},
        ],
    },
    "high_error_rate": {
        "metric": "ml_serving_error_rate",
        "value": 0.12,
        "labels": {"service": "model-server", "model": "llama-3b"},
        "log_service": "model-server",
        "log_lines": [
            {"timestamp": "<now>", "level": "ERROR", "message":
             "ValidationError: expected feature bytes_per_second, got "
             "bytes_per_sec -- schema mismatch"},
            {"timestamp": "<now>", "level": "ERROR", "message":
             "12 percent of requests failing with input schema violation"},
            {"timestamp": "<now>", "level": "INFO", "message":
             "feature pipeline deployed schema change at 14:32 UTC"},
        ],
    },
}


def write_log_lines(log_dir: str, log_service: str, log_lines: list[dict]) -> None:
    """
    Write scenario log lines to the service log file, substituting the current timestamp.

    Parameters
    ----------
    log_dir : str
        Directory where log files are written.
    log_service : str
        Service name, used to name the log file.
    log_lines : list[dict]
        Log line dicts with a placeholder timestamp of "<now>".
    """
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"{log_service}.jsonl")
    now_iso = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()

    resolved_lines_list = [
        {**line, "timestamp": now_iso} for line in log_lines
    ]

    with open(log_path, "a") as log_file:
        for line_dict in resolved_lines_list:
            log_file.write(json.dumps(line_dict) + "\n")


def push_metric(pushgateway_url: str, metric_name: str, value: float, labels: dict) -> None:
    """
    Push a single gauge metric to Pushgateway.

    Parameters
    ----------
    pushgateway_url : str
        Base URL of the Pushgateway instance.
    metric_name : str
        Name of the Prometheus gauge metric.
    value : float
        Value to set on the gauge.
    labels : dict
        Label key-value pairs to attach to the metric.
    """
    registry = CollectorRegistry()
    gauge = Gauge(metric_name, metric_name, labelnames=list(labels.keys()), registry=registry)
    gauge.labels(**labels).set(value)
    push_to_gateway(pushgateway_url, job=metric_name, registry=registry)


def run_scenario(scenario_name: str, pushgateway_url: str, log_dir: str) -> None:
    """
    Execute a single incident scenario: write logs and push the triggering metric.

    Parameters
    ----------
    scenario_name : str
        Key into the SCENARIOS dict.
    pushgateway_url : str
        Base URL of the Pushgateway instance.
    log_dir : str
        Directory where log files are written.
    """
    scenario = SCENARIOS[scenario_name]

    write_log_lines(log_dir, scenario["log_service"], scenario["log_lines"])
    push_metric(pushgateway_url, scenario["metric"], scenario["value"], scenario["labels"])

    print(
        f"Pushed {scenario['metric']}={scenario['value']} to Pushgateway. "
        f"Alertmanager will fire in ~60s. Watch Slack for the diagnosis."
    )


# ============= Main =============

if __name__ == "__main__":
    load_dotenv()

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default=None)
    parser.add_argument("--pushgateway-url", default="http://localhost:9091")
    parser.add_argument("--log-dir", default="./logs")
    args = parser.parse_args()

    if args.scenario is None:
        print("Available scenarios:")
        for name in SCENARIOS:
            print(f"  {name}")
        sys.exit(0)

    run_scenario(args.scenario, args.pushgateway_url, args.log_dir)
