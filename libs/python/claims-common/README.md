# claims-common

Shared Python library for every service in `services/`.

| Module | Purpose |
|---|---|
| `claims_common.logging` | JSON logs, request-id middleware |
| `claims_common.settings` | `ServiceSettings` base class |
| `claims_common.app` | `create_app()` FastAPI factory with logging, CORS and probes |
| `claims_common.health` | liveness/readiness router factory |
| `claims_common.resilience` | retry with backoff + jitter, circuit breaker |
| `claims_common.http` | resilient service-to-service HTTP client |
| `claims_common.contracts` | API models shared between services |

Install in a service image:

```dockerfile
COPY libs/python/claims-common /opt/claims-common
RUN pip install /opt/claims-common
```

For local tests each service adds `../../libs/python/claims-common/src` to its pytest
`pythonpath`.
