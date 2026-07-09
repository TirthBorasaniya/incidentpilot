# Feast Feature TTL Exceeded

## Symptoms
- Feature values served from the online store are older than the
  configured TTL for their feature view.
- Feast returns null or default values for entities that should have
  recent feature data, because the TTL window has expired without a
  refresh.
- Model predictions show degraded quality attributable to stale or
  missing feature values rather than a model or code regression.

## Common Causes
- The TTL configured for a feature view is shorter than the actual
  materialization cadence, so entries expire before the next scheduled
  refresh.
- Materialization jobs are running on schedule but are not completing fast
  enough to refresh all entities within the TTL window.
- The feature view's TTL was set generically at repository creation and
  never tuned to the feature's real update frequency.

## Diagnostic Steps
1. Check Prometheus metric: `ml_feature_freshness_seconds{feature_view="<name>"}`
2. Check service logs for: `TTL`
3. Compare the configured TTL value in the feature view definition against
   the actual materialization job interval.
4. Check whether materialization jobs are completing within their
   scheduled window or falling behind.
5. Assess the risk of serving stale data from the online store for
   entities near or past their TTL boundary.

## Recommended Actions
- If TTL is shorter than the materialization cadence, either increase the
  TTL to match a realistic refresh interval or increase materialization
  frequency, whichever better matches the feature's actual staleness
  tolerance.
- Force an immediate materialization to refresh entities that have
  exceeded TTL: `feast materialize-incremental $(date -u
  +%Y-%m-%dT%H:%M:%S)`.
- If materialization jobs are falling behind schedule, address job
  performance (see Kafka Consumer Lag in Feature Pipeline if the source is
  stream-based) before adjusting TTL.
- Document the chosen TTL and materialization cadence together in the
  feature view definition so future changes account for both.

## Related Alerts
- FeatureStalenessHigh
- FeastTTLExceeded
