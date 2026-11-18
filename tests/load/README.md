# Load tests (k6)

`analysis.js` runs two scenarios at once: browsing (ramping virtual users) and AI analyses
at a fixed arrival rate. Thresholds are the SLOs; k6 exits non-zero when one is missed.

```bash
docker compose up -d          # or point API_URL at staging
k6 run tests/load/analysis.js
ANALYSES_PER_MINUTE=60 LIVE_LLM=true API_URL=https://api... TOKEN=... k6 run tests/load/analysis.js
```

Run it against staging, not production: analyses cost LLM tokens. Expect `rate_limited`
to grow when one client exceeds `RATE_LIMIT_ANALYZE_PER_MINUTE`; that is the limiter
working, not an error.
