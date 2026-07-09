# Model Drift Detected via PSI

## Symptoms
- `model_psi_score` exceeds 0.2 for a monitored feature set.
- Model accuracy or business KPIs trending down without a corresponding
  code or config change in the serving path.
- Increase in downstream complaints or manual review escalations for model
  predictions.

## Common Causes
- Upstream data distribution has genuinely shifted (seasonality, new user
  population, changed sensor calibration, market conditions).
- The feature pipeline changed its schema or encoding (e.g., a categorical
  feature started emitting a new value, or units changed from bytes to
  kilobytes) without the model being retrained on the new distribution.
- A bug in an upstream ETL job is producing malformed or truncated values
  that shift the population statistics rather than reflecting a genuine
  environmental change.
- The reference distribution used to compute PSI is stale relative to a
  reasonable current baseline.

## Diagnostic Steps
1. Check Prometheus metric: `model_psi_score{feature_set="<name>"}`
2. Check service logs for: `top drifted features`
3. Identify which individual features contribute most to the aggregate PSI
   score, since a single degraded feature can dominate the metric.
4. Check whether the upstream feature pipeline deployed a schema or
   transformation change in the same window as the PSI increase.
5. Compare the current feature distribution histogram against the
   reference distribution used at training time.

## Recommended Actions
- PSI between 0.1 and 0.2 indicates slight drift: continue monitoring, no
  immediate action required beyond noting the trend.
- PSI above 0.2 indicates significant drift: treat as an incident. Confirm
  whether the shift is a genuine data change or an upstream pipeline defect
  before deciding on remediation.
- If the drift is a genuine environmental shift, trigger the retraining
  pipeline against a fresh training window that includes the new
  distribution: `python scripts/trigger_retrain.py --job-id <name>
  --window recent`.
- If the drift is caused by an upstream schema bug, file a fix with the
  owning team and do not retrain on the corrupted data until the pipeline
  is repaired.

## Related Alerts
- ModelDriftDetected
- PSIThresholdBreach
