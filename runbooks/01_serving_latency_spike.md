# Model Serving P99 Latency Spike

## Symptoms
- `model_serving_p99_latency_seconds` exceeds 2.0s for at least one minute.
- Client-facing timeouts or retries increasing on upstream services.
- Grafana serving dashboard shows a step change or gradual climb in p99,
  not necessarily matched by a p50 increase.
- GPU utilization pinned near 100 percent on the serving node.

## Common Causes
- Batch size configured too large for the request rate, causing requests to
  queue while waiting to fill a batch window.
- GPU memory pressure forcing repeated allocation and eviction, which shows
  up as latency spikes correlated with `nvidia-smi` memory usage near the
  device limit.
- A downstream dependency (feature store lookup, tokenizer service, cache)
  has itself degraded and the model server is blocked waiting on it.
- A newly deployed model version is larger or less optimized than the
  previous version (e.g., missing quantization, different precision).

## Diagnostic Steps
1. Check Prometheus metric: `model_serving_p99_latency_seconds{service="model-server"}`
2. Check service logs for: `queue depth`
3. Compare current p99 against the 24-hour baseline using
   `model_serving_p99_latency_seconds[24h]` to determine whether this is a
   new regression or a recurring pattern tied to traffic peaks.
4. Check GPU utilization and memory via node exporter metrics or
   `nvidia-smi` on the serving host if accessible.
5. Check whether a new model version was deployed in the last hour by
   comparing the `model` label value against the MLflow registry's current
   production version.

## Recommended Actions
- If queue depth is high and batch size is the cause, reduce the configured
  max batch size or lower the batching window timeout in the serving
  config (e.g., Triton `dynamic_batching.max_queue_delay_microseconds`).
- If GPU memory pressure is confirmed, restart the serving process to clear
  fragmented memory, then reduce max batch size before restarting.
- If a downstream dependency is slow, check its own latency metrics and
  escalate to that service's on-call rather than treating this as a model
  serving issue.
- If a recent model version deploy correlates with the spike, roll back to
  the previous model version in the registry and reload:
  `mlflow models serve --model-uri models:/<model_name>/<previous_version>`
  or trigger the server's hot-reload endpoint with the prior version tag.

## Related Alerts
- ServingLatencyHigh
