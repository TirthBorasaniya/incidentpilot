# Batch Size Misconfigured for GPU Memory

## Symptoms
- Recurring GPU out-of-memory errors that correlate with specific request
  patterns (larger batches or longer sequences).
- Serving throughput lower than expected for the given hardware tier
  because batch size is set conservatively low to avoid OOM.
- Memory usage graphs show a sawtooth pattern of near-limit usage followed
  by crashes and restarts.

## Common Causes
- Batch size configured without accounting for the model's per-token
  memory footprint at the maximum supported sequence length.
- Dynamic batching configuration allows batch sizes to grow unbounded
  under load instead of capping at a safe maximum.
- The configured batch size was tuned for a different GPU tier (e.g.,
  A100) and later deployed unchanged to a smaller-memory tier (e.g., T4).

## Diagnostic Steps
1. Check Prometheus metric: `gpu_memory_used_bytes{device="<id>"}`
2. Check service logs for: `CUDA out of memory`
3. Estimate memory-to-batch-size using the model's known per-token memory
   footprint multiplied by max sequence length and current batch size.
4. Confirm the GPU tier actually deployed against the tier the batch size
   configuration was tuned for.
5. Review the dynamic batching configuration for an upper bound on batch
   size and queue delay.

## Recommended Actions
- Set an explicit maximum batch size bound in the dynamic batching
  configuration rather than allowing unbounded growth under load.
- Use memory-to-batch-size estimation to select a batch size with headroom
  below the device memory limit, not right at the boundary.
- Recommended starting batch sizes per GPU tier for typical mid-size
  transformer models: T4 (16 GB) around 4 to 8, A10 (24 GB) around 8 to
  16, A100 (40 GB or 80 GB) around 16 to 32, adjusted down for longer
  sequence lengths.
- If the deployment tier changed, retune the batch size for the new tier
  rather than carrying over the previous tier's configuration.

## Related Alerts
- BatchSizeMisconfigured
- RetrainingJobFailed
