# Training Loss Divergence Detected

## Symptoms
- Training loss increases sharply or becomes NaN partway through a
  training run.
- Gradient norms spike to very large values in the steps preceding
  divergence.
- The retraining job reports failure or produces a model checkpoint that
  performs far worse than the previous production model.

## Common Causes
- Learning rate configured too high for the current batch size or model
  architecture, causing unstable updates.
- Gradient explosion due to missing or insufficiently aggressive gradient
  clipping.
- Batch normalization or another stabilizing layer disabled or
  misconfigured in a recent architecture change.
- A change in the input data distribution (see Model Drift Detected via
  PSI) introducing outlier values that destabilize training.

## Diagnostic Steps
1. Check Prometheus metric: `ml_retraining_job_success{job_id="<id>"}`
2. Check service logs for: `loss`
3. Check gradient norm logs in the steps immediately before divergence to
   confirm gradient explosion versus a data-related cause.
4. Confirm the learning rate and gradient clipping configuration used for
   the failed run against known-stable values from prior successful runs.
5. Confirm batch normalization or other stabilizing layers are enabled per
   the intended architecture configuration.

## Recommended Actions
- Reduce the learning rate and restart training from the last valid
  checkpoint before divergence occurred.
- Enable or tighten gradient clipping (e.g., clip gradient norm to 1.0) if
  it was missing or too permissive.
- If batch normalization was disabled by a recent change, re-enable it and
  re-run a short validation training pass before committing to a full run.
- If the divergence correlates with a data distribution shift, address the
  upstream drift per the Model Drift Detected via PSI runbook before
  retraining again.

## Related Alerts
- RetrainingJobFailed
- LossDivergence
