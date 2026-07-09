# Feature Store Staleness Detected

## Symptoms
- `ml_feature_freshness_seconds` exceeds 3600 for a feature view.
- Online store serves feature values that no longer reflect recent
  upstream events.
- Model predictions degrade in ways consistent with using outdated
  contextual features rather than a code or model regression.

## Common Causes
- The Feast TTL for the affected feature view is configured too long
  relative to how often the feature actually changes, masking staleness
  until it is severe.
- The ingestion or materialization job that populates the online store has
  stalled or crashed.
- A Kafka consumer feeding the materialization pipeline has fallen behind
  and is blocking new events from reaching the online store.
- A scheduled materialization job was not triggered due to an orchestrator
  failure (Airflow DAG not running, cron misconfiguration).

## Diagnostic Steps
1. Check Prometheus metric: `ml_feature_freshness_seconds{feature_view="<name>"}`
2. Check service logs for: `last materialized`
3. Check the Kafka consumer group lag for the topic feeding this feature
   view, since consumer lag is a common root cause of staleness.
4. Check the materialization job scheduler (Airflow, cron) for missed or
   failed runs in the affected window.
5. Confirm the Feast TTL configuration for the feature view matches the
   expected update cadence.

## Recommended Actions
- If a Kafka consumer is lagging, address the lag first per the Kafka
  Consumer Lag in Feature Pipeline runbook, since materialization cannot
  catch up while the consumer is behind.
- If the materialization job stalled, restart it manually:
  `feast materialize-incremental $(date -u +%Y-%m-%dT%H:%M:%S)`.
- If the TTL is misconfigured relative to actual update frequency, adjust
  the `ttl` field in the feature view definition and redeploy the feature
  repository.
- As an immediate mitigation while root cause is addressed, force a manual
  materialization to refresh the online store: `feast materialize
  <start_date> <end_date>`.

## Related Alerts
- FeatureStalenessHigh
- KafkaConsumerLag
- FeastTTLExceeded
