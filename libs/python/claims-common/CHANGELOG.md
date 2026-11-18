# Changelog

## [0.2.0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/compare/claims-common-v0.1.0...claims-common-v0.2.0) (2026-11-18)


### Features

* **ai-agent:** fall back to cached ML signals when ml-service is down ([fbdaee1](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/fbdaee1e379c2e14dd914272bb0e32c265589e03))
* **ai:** add response cache for validated LLM results ([da5f7b6](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/da5f7b60e7fa5a72c5d97311b62759907296a8d4))
* **ai:** stream analysis progress over server-sent events ([4252251](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/42522516c7365d26b7a0b1d87ac73245eea07e22))
* **common:** add resilient async HTTP client for service-to-service calls ([5a99baa](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/5a99baa42057bd939f7bed51413eaf90f6477db3))
* **common:** add service settings base, app factory and health router ([869575c](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/869575c123bbb0b0cfeee279754220c3e7528373))
* **ml-service:** add feature validation and out-of-distribution guard ([6b37920](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/6b37920086ec5fa3c4a94ab4f84c6bfba345a4bd))
* **ml-service:** replace the risk classifier, macro-F1 0.35 -&gt; 0.60 ([7c595d7](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7c595d72889583fdb9c105b1c5ad130cea0fd381))
* **obs:** add OpenTelemetry tracing across services ([784cc9e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/784cc9e88c818b53bd141c7ab34e11b734f5fc7f))
* **obs:** add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state) ([88afe20](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/88afe206ddef9b93b0a097af9764107d67892109))
* **obs:** expose /metrics and add a Prometheus scrape setup ([86730ae](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/86730aee03c9024f76994db04b5b4c9868df23a6))
* **security:** add append-only, tamper-evident audit log ([7996f47](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7996f477929afa44a7911719bd1827eebc47b50e))
* **security:** add HTTP security headers to every API ([10d1812](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/10d1812145319e78af0a2e2a86a8193d642b9b1a))
* **security:** add JWT authentication on claims-api ([83e7e18](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/83e7e185794b91482babb6574b2513c1b3450a95))
* **security:** add per-client rate limiting on analysis endpoints ([07810cb](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/07810cb101107fc75d00ee387163768eebc3295c))
* **security:** authenticate service-to-service calls ([7fe93d8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7fe93d894d1a8d602bb48e73320d64ce6fbf0573))


### Refactoring

* **ai-agent:** move agent, AI layer and ML code out of claims-api ([03c2385](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/03c238596c16d64d44b58d115331d278cced55ed))
* **common:** move JSON logging and request-id middleware to claims-common ([172b1b5](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/172b1b556662d8b9f8316f8d50130305b2a7aba9))
* **common:** move retry and circuit breaker to claims-common ([a24d701](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/a24d701ee2a422cbac5e167baacf550049660dfc))
* **ml-service:** move data generation, training and inference into ml-service ([e2f7fa3](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e2f7fa368cbaa5662e45b0fa998674f4e311a40f))
