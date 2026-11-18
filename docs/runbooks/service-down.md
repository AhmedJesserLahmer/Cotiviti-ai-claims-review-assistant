# Service down

**Alert:** `ServiceDown`: Prometheus cannot scrape claims-api, ai-agent or ml-service.

1. `kubectl -n $NS get pods -l app.kubernetes.io/component=<component>`
2. CrashLoopBackOff: `kubectl -n $NS logs <pod> --previous`. Production refuses to start
   without `AUTH_ENABLED`, `JWT_SECRET`, `INTERNAL_TOKEN` or `AUDIT_HMAC_KEY`: check the
   release Secret / ExternalSecret status (`kubectl -n $NS get externalsecret`).
3. ml-service unready: no active model (`/health/ready` → `checks.model`). Activate a
   version (`POST /v1/models/<version>/activate`) or let the init container seed the
   registry volume.
4. Pods running but not scraped: NetworkPolicy `allow-metrics` must match the monitoring
   namespace label (`networkPolicy.monitoringNamespaceSelector`).
