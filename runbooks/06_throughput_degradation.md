# Model Serving Throughput Degradation

## Symptoms
- Requests per second served by the model endpoint drops while incoming
  request volume stays constant or increases.
- Request queue depth grows steadily rather than staying near zero.
- Clients observe increased end-to-end latency even when per-request
  compute time is unchanged.

## Common Causes
- The serving process has hit its configured concurrency limit and is
  queuing excess requests rather than rejecting or scaling.
- CPU or GPU saturation on the serving node limits how many requests can
  be processed per second regardless of queue management.
- Replica count is fixed and traffic has grown beyond what the current
  replica count can sustain.
- A slow downstream dependency is holding worker threads or processes open
  longer than expected, reducing effective concurrency.

## Diagnostic Steps
1. Check Prometheus metric: `model_serving_queue_depth{service="<name>"}`
2. Check service logs for: `queue depth`
3. Check CPU and GPU utilization on the serving nodes to distinguish
   resource saturation from a concurrency configuration limit.
4. Check the current replica count against historical traffic-to-replica
   ratios to determine if scaling is warranted.
5. Check downstream dependency latency to rule out worker starvation
   caused by slow calls elsewhere.

## Recommended Actions
- If the concurrency limit is the bottleneck and resources have headroom,
  raise the configured concurrency limit for the serving process.
- If CPU or GPU is saturated, scale out by adding replicas rather than
  raising concurrency limits, since the latter will not help once compute
  is the constraint.
- If replica count has not kept pace with traffic growth, increase the
  replica count and confirm the load balancer is distributing traffic
  evenly across replicas.
- If a downstream dependency is holding workers open, apply a stricter
  timeout on that call and treat the dependency's slowness as a separate
  incident.

## Related Alerts
- ThroughputDegradation
- ServingLatencyHigh
