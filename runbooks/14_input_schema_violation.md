# Input Schema Violation on Model Server

## Symptoms
- Model server logs show validation errors referencing unexpected feature
  names or types.
- A percentage of requests fail consistently while others succeed,
  suggesting a subset of traffic sends a different schema than the rest.
- Error rate increase correlates with a recent feature pipeline
  deployment.

## Common Causes
- The feature pipeline renamed, added, or removed a feature without
  updating the model server's expected input contract.
- A dtype mismatch between what the feature pipeline sends (e.g., string)
  and what the model expects (e.g., float).
- Multiple upstream producers send slightly different schema versions
  concurrently during a rollout, so only a fraction of requests fail.
- Schema validation was not enforced strictly enough at the server
  boundary, allowing malformed requests to reach the model instead of
  being rejected with a clear error earlier.

## Diagnostic Steps
1. Check Prometheus metric: `ml_serving_error_rate{service="<name>"}`
2. Check service logs for: `ValidationError`
3. Compare the exact feature names and dtypes present in error logs
   against the model server's documented expected schema.
4. Check the feature pipeline's deployment history for schema changes in
   the window preceding the error increase.
5. Determine whether the mismatch affects all traffic or a specific
   producer or client version to isolate a partial rollout.

## Recommended Actions
- Coordinate with the feature pipeline owner to either revert the schema
  change or update the model server's input adapter to accept the new
  schema.
- Add or tighten explicit schema validation at the server's input boundary
  so future mismatches produce a clear rejection rather than an internal
  error.
- If the mismatch stems from a partial rollout, pause the rollout until
  all producers agree on a single schema version.
- Once corrected, monitor `ml_serving_error_rate` to confirm it returns
  below the 0.05 threshold before closing the incident.

## Related Alerts
- InputSchemaViolation
- ServingErrorRateHigh
