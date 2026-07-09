# Model Serving High Error Rate

## Symptoms
- `ml_serving_error_rate` exceeds 0.05 for a service and model pair.
- Increase in 4xx or 5xx responses from the model serving endpoint.
- Error logs showing validation exceptions rather than infrastructure
  failures (timeouts, connection resets).

## Common Causes
- Input schema mismatch between what the feature pipeline sends and what
  the model server expects, often following an upstream schema change
  (renamed or reformatted feature).
- Tokenizer version mismatch between the training environment and the
  serving environment, producing invalid token sequences.
- Null or missing feature values reaching the server without being handled
  by a default or imputation step.
- A newly deployed model version expects a different input contract than
  the traffic currently being sent to it.

## Diagnostic Steps
1. Check Prometheus metric: `ml_serving_error_rate{service="<name>",model="<name>"}`
2. Check service logs for: `ValidationError`
3. Compare the exact feature names and dtypes in the error messages
   against the model's expected input schema.
4. Check whether the feature pipeline deployed a schema change in the
   window preceding the error rate increase.
5. Confirm the tokenizer or preprocessing artifact version bundled with
   the serving deployment matches the version used at training time.

## Recommended Actions
- If the error is a schema mismatch caused by an upstream rename or
  reformat, coordinate with the feature pipeline owner to either revert
  the change or update the model server's input adapter to match.
- If a tokenizer version mismatch is confirmed, redeploy the server with
  the tokenizer artifact pinned to the training-time version.
- If null values are the cause, add explicit validation and default
  handling at the server's input adapter layer rather than accepting
  malformed requests.
- If the error rate began immediately after a new model version deploy,
  roll back to the previous model version in the registry while the input
  contract mismatch is resolved.

## Related Alerts
- ServingErrorRateHigh
- InputSchemaViolation
- ModelVersionMismatch
