# Model Version Mismatch Between Registry and Server

## Symptoms
- The version reported as loaded by the model server does not match the
  version marked as production in the model registry.
- Predictions behave inconsistently with expectations set by the
  registry's documented production model.
- A recent promotion or rollback in the registry did not propagate to one
  or more serving replicas.

## Common Causes
- The server was not restarted or hot-reloaded after a new version was
  promoted in the registry.
- A deployment rolled out partially, leaving some replicas on the old
  version while others picked up the new one.
- The server's model-loading configuration points to a pinned version
  rather than tracking the registry's production alias.

## Diagnostic Steps
1. Check Prometheus metric: `model_serving_loaded_version{service="<name>"}`
2. Check service logs for: `model version`
3. Query the MLflow model registry for the current version tagged
   production for the model name in question.
4. Query each serving replica individually for its currently loaded
   version to identify partial rollout rather than a uniform mismatch.
5. Confirm the deployment configuration's version reference (pinned
   version number versus registry alias) matches the intended operational
   model.

## Recommended Actions
- If replicas are inconsistent due to a partial rollout, complete the
  rollout across all replicas or roll all replicas back to the previous
  consistent version.
- Trigger a hot-reload on affected replicas to pick up the correct
  version: call the server's reload endpoint with the target version, for
  example `POST /reload {"version": "<production_version>"}`.
- If the deployment is pinned to a specific version rather than tracking
  the registry alias, decide deliberately whether pinning or alias
  tracking is the intended operational model, and update configuration to
  match.
- After correcting the mismatch, verify all replicas report the same
  loaded version before closing the incident.

## Related Alerts
- ModelVersionMismatch
- ServingErrorRateHigh
