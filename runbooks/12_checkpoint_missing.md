# Training Checkpoint Not Found

## Symptoms
- Training or resume job fails immediately at startup with a file-not-found
  or path error referencing the checkpoint location.
- A retraining job that was expected to resume from a prior epoch instead
  fails before any training steps execute.
- Storage mount for the checkpoint directory reports as empty or
  inaccessible from the training node.

## Common Causes
- The checkpoint path in the job configuration does not match where
  checkpoints were actually written, often after a configuration change or
  environment migration.
- The storage volume containing checkpoints is not mounted on the node the
  job was scheduled to, particularly after a scheduler reassigns the job
  to a different node.
- A prior job was killed before it wrote its first checkpoint, so no valid
  checkpoint exists yet despite the resume logic expecting one.
- Checkpoint retention or cleanup logic deleted the expected checkpoint
  before the resume job ran.

## Diagnostic Steps
1. Check Prometheus metric: `ml_retraining_job_success{job_id="<id>"}`
2. Check service logs for: `checkpoint`
3. Check the exact checkpoint path referenced in the job configuration
   against the actual contents of the storage volume.
4. Confirm the storage volume is mounted and readable from the node
   assigned to the job.
5. Check checkpoint retention policy logs to rule out premature cleanup of
   the expected checkpoint.

## Recommended Actions
- If the path is misconfigured, correct the checkpoint directory reference
  in the job configuration to match the actual storage location.
- If the storage volume is not mounted on the assigned node, fix the node
  scheduling constraint or mount configuration so the job lands on a node
  with access to the checkpoint volume.
- If no valid checkpoint exists because the prior run never wrote one,
  restart training from scratch or from the last known good checkpoint
  recorded in job history.
- Resume procedure once the correct checkpoint is located: `sbatch
  retrain_job.slurm --resume-from <correct_checkpoint_path>`.

## Related Alerts
- RetrainingJobFailed
- CheckpointMissing
