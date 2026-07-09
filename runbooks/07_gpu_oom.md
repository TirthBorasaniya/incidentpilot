# GPU Out of Memory During Inference

## Symptoms
- Serving process crashes or restarts with a CUDA out-of-memory error in
  logs.
- Intermittent request failures that correlate with larger batch sizes or
  longer input sequences.
- `nvidia-smi` shows memory usage climbing to the device limit shortly
  before a crash.

## Common Causes
- Batch size configured too large for the available GPU memory given the
  model's activation memory footprint at the maximum sequence length.
- Model loaded in full precision (FP32) instead of a lower precision
  (FP16 or INT8) that the deployment was designed to use, roughly doubling
  or quadrupling memory usage.
- Memory fragmentation from long-running processes that have not released
  cached allocations between requests.
- Multiple model instances or processes co-located on the same GPU without
  memory limits, competing for the same pool.

## Diagnostic Steps
1. Check Prometheus metric: `gpu_memory_used_bytes{device="<id>"}`
2. Check service logs for: `CUDA out of memory`
3. Check the configured batch size and max sequence length against the
   model's known memory-per-token footprint.
4. Confirm the precision mode the model was loaded in (FP32, FP16, INT8)
   against the intended deployment configuration.
5. Check whether other processes share the same GPU device and are
   consuming memory concurrently.

## Recommended Actions
- Clear GPU cache and restart the serving process to release fragmented
  memory: this is a short-term mitigation, not a fix, if the root cause is
  batch size or precision.
- Reduce the max batch size configuration to fit within available memory,
  using the memory-to-batch-size estimation in the Batch Size
  Misconfigured for GPU Memory runbook.
- If the model is loaded in the wrong precision, correct the deployment
  configuration to load in the intended precision (e.g., set
  `torch_dtype=torch.float16`).
- If multiple processes share a GPU, isolate them with per-process memory
  fraction limits (e.g., `torch.cuda.set_per_process_memory_fraction`) or
  move to dedicated devices.

## Related Alerts
- RetrainingJobFailed
- BatchSizeMisconfigured
