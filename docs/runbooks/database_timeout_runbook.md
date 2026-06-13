# Runbook: DB-1002 Database Connection Timeout Troubleshooting

## Overview
This runbook describes the procedure to diagnose and resolve database connection timeouts (e.g., `Failed to connect to database: Connection timeout after 30 seconds`) occurring within microservices like `payment-service` trying to reach PostgreSQL.

## Common Root Causes
1. **Network Partition / Security Group Rule**: Core backend services cannot reach the database pod/VM due to network policies (`NetworkPolicy` in Kubernetes) or security group blocks.
2. **Incorrect Credentials**: Service is using expired or incorrect username, password, or database endpoint names.
3. **Database Capacity Exhausted**: The PostgreSQL server has exhausted its connection pool (default `max_connections = 100`) or CPU/Memory limits.
4. **Incorrect DNS / Service Name**: Using a service endpoint name that is invalid, misspelled, or located in a different namespace (e.g. `postgres-db.default.svc.cluster.local` when it should be `postgres.prod`).

## Diagnostics Steps
1. Verify the pod can resolve the database hostname:
   ```bash
   kubectl exec -it <pod-name> -- nslookup postgres-db
   ```
2. Verify TCP connection capability using netcat:
   ```bash
   kubectl exec -it <pod-name> -- nc -zvw3 postgres-db 5432
   ```
3. Check PostgreSQL connection status:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```

## Remediation Steps
1. **Restart Database Pod**: If the database is unresponsive, restart it to clear hung connections.
   ```bash
   kubectl rollout restart deployment postgres-db
   ```
2. **Scale DB Connection Pooler**: If `max_connections` is hit, introduce PgBouncer or increase `max_connections` in `postgresql.conf`.
3. **Correct Credentials**: Update the environment variables or Kubernetes Secrets mapping to the pod (`POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`).
