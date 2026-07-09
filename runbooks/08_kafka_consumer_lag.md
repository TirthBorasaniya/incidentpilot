# Kafka Consumer Lag in Feature Pipeline

## Symptoms
- Consumer group lag for the feature materialization topic grows steadily
  instead of staying near zero.
- Feature freshness metrics degrade downstream even though the producer
  side of the pipeline appears healthy.
- One or a small number of partitions show disproportionately high lag
  compared to the rest of the group.

## Common Causes
- Partition imbalance where a small number of partitions receive a
  disproportionate share of traffic, overloading the consumers assigned to
  them.
- A consumer instance has crashed or stalled, leaving its partitions
  unprocessed until a rebalance reassigns them.
- Downstream write latency to the online feature store increased, slowing
  consumption even though message read rate is fine.
- Consumer count has not scaled with an increase in topic throughput.

## Diagnostic Steps
1. Check Prometheus metric: `kafka_consumergroup_lag{group="feast-consumer"}`
2. Check service logs for: `lag`
3. Check per-partition lag distribution to distinguish partition imbalance
   from an across-the-board slowdown.
4. Check consumer process health and recent restarts in the consumer
   group.
5. Check the online store write latency to rule out a downstream
   bottleneck rather than a consumption bottleneck.

## Recommended Actions
- If a small number of partitions are lagging, trigger a partition
  rebalance or repartition the topic with a more uniform key distribution.
- If a consumer instance stalled, restart it and confirm the consumer
  group rebalances to reclaim its partitions.
- If the online store write path is the bottleneck, scale write capacity
  or batch writes before addressing consumer count.
- If overall throughput has grown, scale out the consumer group up to the
  partition count and tune the lag alert threshold to reflect the new
  baseline throughput.

## Related Alerts
- FeatureStalenessHigh
- KafkaConsumerLag
