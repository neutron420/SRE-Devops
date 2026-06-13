# Runbook: MEM-2004 Container OOMKilled (Out of Memory) Troubleshooting

## Overview
This runbook covers how to respond when a Kubernetes container is terminated with the reason `OOMKilled` (Exit Code 137). This indicates the container exceeded the memory limit specified in its resource configurations.

## Common Root Causes
1. **Memory Leak**: The application (e.g. Node.js, Python, Java) continually allocates memory without freeing it, leading to a steady, linear increase in memory usage.
2. **Under-provisioned Resource Limits**: The container resource memory limit in Kubernetes is set too low for normal runtime load spikes.
3. **Heavy Processing / Memory Spikes**: Large batch jobs or file uploads are processed entirely in memory rather than streamed.
4. **JVM Misconfiguration**: For Java containers, the Max Heap Size (`-Xmx`) is configured higher than or too close to the Kubernetes memory limit, leaving no room for non-heap native memory.

## Diagnostic Steps
1. Inspect the Pod description to verify exit code 137:
   ```bash
   kubectl describe pod <pod-name>
   ```
2. Retrieve historical Prometheus memory metrics:
   ```promql
   container_memory_working_set_bytes{container="<container-name>"}
   ```
3. Extract error stack traces from logs prior to termination (look for heap dumps, `OutOfMemoryError`, or system kills).

## Remediation Steps
1. **Increase Memory Resource Limits**: If the service needs more memory for normal operations, update the Deployment spec:
   ```yaml
   resources:
     limits:
       memory: "1Gi"
     requests:
       memory: "512Mi"
   ```
2. **Implement Streaming**: If processing large datasets (e.g. analytical records), refactor the code to process records in small chunks or streams rather than loading the entire batch into memory.
3. **Adjust JVM Max Heap Size**: Set `-XX:MaxRAMPercentage=75.0` or `-Xmx` to 75% of the container memory limit.
4. **Trigger Rollover**: Force restart the pod to clear immediate leak exhaustion.
   ```bash
   kubectl rollout restart deployment analytics-service
   ```
