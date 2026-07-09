# PSI Threshold Breach on Feature Set

## Symptoms
- `model_psi_score` for a feature set crosses the 0.2 significant drift
  threshold.
- The breach may be isolated to one or two features within a larger
  feature set rather than affecting all features uniformly.
- Downstream model performance metrics may not yet show visible
  degradation, since PSI is a leading indicator.

## Common Causes
- One or a few features within the set have shifted sharply while the
  rest of the set remains stable, and the aggregate PSI score reflects
  that concentrated shift.
- A genuine change in the upstream data source (new user segment, sensor
  recalibration, market conditions).
- An upstream data quality issue is producing out-of-distribution values
  that are not representative of a true population shift.

## Diagnostic Steps
1. Check Prometheus metric: `model_psi_score{feature_set="<name>"}`
2. Check service logs for: `top drifted features`
3. Identify which individual features contribute most to the aggregate PSI
   score using per-feature PSI breakdowns if available, since remediation
   differs depending on whether one feature or the whole set has shifted.
4. Investigate the upstream data source for the top drifted features to
   determine whether the shift is genuine or a data quality defect.
5. Compare the magnitude and direction of the shift against historical
   seasonal patterns to rule out expected cyclical drift.

## Recommended Actions
- If PSI interpretation places the score at 0.1 to 0.2, treat as slight
  drift and continue monitoring without immediate remediation.
- If the score exceeds 0.2, and the shift is confirmed genuine, consider
  running the model in shadow mode against the new distribution before
  promoting a retrained version to production.
- If a data quality defect is identified in the upstream source, fix the
  defect and re-evaluate PSI after the fix rather than retraining on
  corrupted data.
- Escalate to the upstream data source owner when the drifted features
  originate outside the ML pipeline's direct control.

## Related Alerts
- ModelDriftDetected
- PSIThresholdBreach
