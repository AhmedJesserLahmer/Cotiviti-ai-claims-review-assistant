# claims-api error budget burn

**Alerts:** `ClaimsApiErrorBudgetFastBurn` (page), `ClaimsApiErrorBudgetSlowBurn` (ticket).
SLO: 99.5% of claims-api requests succeed (non-5xx) over 30 days.

1. *HTTP 5xx ratio by service* in Grafana: is it claims-api itself or a dependency?
   503 with "AI agent is unavailable" → ai-agent; "ML scoring is temporarily unavailable"
   → ml-service ([service-down.md](service-down.md)).
2. Traces (Jaeger/Tempo): filter `service.name=claims-api`, `http.status_code>=500`.
3. Recent deploy? Roll back ([rollback.md](rollback.md)).
4. MongoDB: readiness of claims-api fails when MongoDB is unreachable, which removes pods
   from the load balancer; check the database first if all pods are unready.
