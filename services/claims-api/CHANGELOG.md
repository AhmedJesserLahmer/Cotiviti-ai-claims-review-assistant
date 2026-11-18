# Changelog

## [0.4.0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/compare/claims-api-v0.3.0...claims-api-v0.4.0) (2026-11-18)


### Features

* **ai:** add AI run metadata audit trail ([3c27c94](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/3c27c948075c0073cbb5003644d2cb70a59f013d))
* **ai:** add async retry with exponential backoff and full jitter ([8407b66](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/8407b66ac039cf32fd5111aecca0c11b16c23d28))
* **ai:** add circuit breaker ([1305466](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/13054666f6b7bde404f3f958d044bc17f8538237))
* **ai:** add ClaimReviewAI facade orchestrating all layers ([64c5086](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/64c50866930f19f5b04325f1e84edf7ed75ef47d))
* **ai:** add deterministic rule-based fallback recommender ([8d9f8b2](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/8d9f8b2509089b1b9e2f9606a29bec66d3847f43))
* **ai:** add environment-driven AI settings ([ffe01fd](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/ffe01fdefd254e9e2ee821d185e9b747b1031e8a))
* **ai:** add Groq provider adapter with error mapping ([2544b17](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/2544b17b1d05251a720b8aa767837cc2fffe8ea1))
* **ai:** add output sanitization guardrail for reasoning ([caed093](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/caed09377413ed7d65cae5f6a3183d648399e97f))
* **ai:** add PII redaction guardrail ([b64197e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/b64197ebadaf7927c616627d7e1e8089084dfd9f))
* **ai:** add policy guardrail cross-checking ML signals ([cfc231d](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/cfc231d49424ba7bee2a3255e827de5c8c7423a4))
* **ai:** add prompt A/B selection through the registry ([cc471e8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/cc471e87975356cf8c3183f913f9cf73dd7733ae))
* **ai:** add prompt-injection guardrail for untrusted fields ([bc81b8c](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/bc81b8c3ec32b3b6072376a458e72828c10327d6))
* **ai:** add resilient LLM client with model fallback chain ([84ab67d](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/84ab67d3702836e3a517f33a53e01147bd708016))
* **ai:** add response cache for validated LLM results ([da5f7b6](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/da5f7b60e7fa5a72c5d97311b62759907296a8d4))
* **ai:** add reviewer feedback endpoint and AI quality analytics ([65943a0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/65943a0102d4499f9e52b43f6a206fc93671e961))
* **ai:** add scripted provider for tests and offline runs ([9164a79](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/9164a791c73e11822cf0038f64795f4ba73469a1))
* **ai:** add structured output schema for recommendations ([944dbf8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/944dbf828311a35fe14abce18e472e88c71874f6))
* **ai:** add timeout guard for LLM calls ([5009e15](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/5009e15175e89215b03d13dd8ffa59b5abec639e))
* **ai:** add tolerant JSON extraction and repair ([7b57743](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7b5774388c31b2b09b2013ea7cf8eb4130713aa5))
* **ai:** add validate-and-repair structured generation ([5f22336](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/5f2233651425de68aeeaeee2b7ea3d23d0a0bde1))
* **ai:** add versioned prompt registry with hardened prompts ([aa88eb8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/aa88eb82b1f07e754585385b4c25f5b44196d84a))
* **ai:** define LLM provider protocol and response types ([32d7016](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/32d701680a2bdec2cce49ad0a48ebd9fb3d36bbe))
* **ai:** scaffold ai_platform package with error taxonomy ([77ddfdc](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/77ddfdcccbd6bce23610439f3ee52cef52fedf74))
* **ai:** stream analysis progress over server-sent events ([4252251](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/42522516c7365d26b7a0b1d87ac73245eea07e22))
* **api:** add liveness and readiness probes ([51793d6](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/51793d67cf508ac2974bf057a792bb274b7b56fd))
* **api:** add structured JSON logging and request IDs ([bfda42a](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/bfda42a3e2208dddc3db3908fa7499878ccd0861))
* **api:** expose and persist AI run metadata on analyses ([539ada6](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/539ada6657167fdaf8b06f86ae196e7ad8153224))
* **api:** make CORS origins configurable ([1838ed1](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/1838ed1cc22647252dbc0b1b57c5f297d0dadb50))
* **claims-api:** add async analysis jobs (202 Accepted + job status) ([801679b](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/801679b32265d9ee8cb0f0738fd7bf1c4bc3c52d))
* **claims-api:** add Redis + arq worker for bulk analysis jobs ([8833893](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/8833893391c55e694c9cf761da37c04f2e8899b0))
* **common:** add service settings base, app factory and health router ([869575c](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/869575c123bbb0b0cfeee279754220c3e7528373))
* **obs:** add OpenTelemetry tracing across services ([784cc9e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/784cc9e88c818b53bd141c7ab34e11b734f5fc7f))
* **obs:** add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state) ([88afe20](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/88afe206ddef9b93b0a097af9764107d67892109))
* **security:** add append-only, tamper-evident audit log ([7996f47](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7996f477929afa44a7911719bd1827eebc47b50e))
* **security:** add JWT authentication on claims-api ([83e7e18](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/83e7e185794b91482babb6574b2513c1b3450a95))
* **security:** add per-client rate limiting on analysis endpoints ([07810cb](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/07810cb101107fc75d00ee387163768eebc3295c))
* **security:** add reviewer and admin roles ([cbee457](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/cbee4571d7174aba73dda827ed195cd4b3b83a97))
* **security:** add upload size limits and CSV formula-injection protection ([013fdb3](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/013fdb3d8e83bd6f76e385969c95061e70a42ca1))
* **security:** authenticate service-to-service calls ([7fe93d8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7fe93d894d1a8d602bb48e73320d64ce6fbf0573))


### Bug Fixes

* **claims-api:** reject uploaded fields longer than the scoring contract ([9ead54b](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/9ead54b7a7ca4ba808680eb84594258670af6a91))


### Refactoring

* **agent:** route LangGraph nodes through ClaimReviewAI ([455e2f0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/455e2f099adf39fc572274ccf3f88d19da77c697))
* **ai-agent:** move agent, AI layer and ML code out of claims-api ([03c2385](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/03c238596c16d64d44b58d115331d278cced55ed))
* **claims-api:** drop ML and LLM dependencies from the gateway ([3261dba](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/3261dba80a9a62f779239be760111c3f5b499c39))
* **common:** move JSON logging and request-id middleware to claims-common ([172b1b5](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/172b1b556662d8b9f8316f8d50130305b2a7aba9))
* **common:** move retry and circuit breaker to claims-common ([a24d701](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/a24d701ee2a422cbac5e167baacf550049660dfc))
* **ml-service:** move data generation, training and inference into ml-service ([e2f7fa3](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e2f7fa368cbaa5662e45b0fa998674f4e311a40f))
* move backend into services/claims-api ([4d1c114](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/4d1c114d2a1db04314c2b4195699fef018e66d94))
