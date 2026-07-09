# ML Retraining Job Failure

## Symptoms
- `ml_retraining_job_success` reports 0 for a given job_id.
- Scheduled retraining pipeline did not produce a new model artifact or
  registry entry.
- Training job logs show a non-zero exit code or an abrupt termination.

## Common Causes
- SLURM (or equivalent scheduler) killed the job due to exceeding the
  allocated memory on the GPU node (OOM kill).
- Loss divergence during training, often caused by a learning rate that is
  too high or missing gradient clipping.
- The checkpoint path configured for the job does not exist or is not
  mounted, causing a failure when the job attempts to write or resume from
  a checkpoint.
- A dependency or data source the job reads from at startup (training
  data snapshot, feature store export) was unavailable.

## Diagnostic Steps
1. Check Prometheus metric: `ml_retraining_job_success{job_id="<id>"}`
2. Check service logs for: `killed` or `OOM`
3. Check the job scheduler's exit reason and peak memory usage recorded
   for the job, since an OOM kill is distinguishable from an application
   error in the scheduler's own accounting.
4. Check training logs for loss values in the steps immediately preceding
   failure to rule out divergence.
5. Confirm the checkpoint output path exists and the storage volume is
   mounted and writable from the training node.

## Recommended Actions
- If the job was OOM killed, reduce batch size or enable gradient
  checkpointing, then resubmit the job with a smaller memory footprint.
- If loss diverged, restart training from the last valid checkpoint with a
  reduced learning rate and confirm gradient clipping is enabled, per the
  Training Loss Divergence Detected runbook.
- If the checkpoint path was missing, verify the storage mount on the
  training node and correct the job's checkpoint directory configuration
  before resubmitting.
- Restart procedure: resubmit the job referencing the last valid
  checkpoint recorded in the logs, e.g. `sbatch retrain_job.slurm
  --resume-from checkpoints/epoch_12_step_5400.pt`.

## Related Alerts
- RetrainingJobFailed
- CheckpointMissing
- LossDivergence
