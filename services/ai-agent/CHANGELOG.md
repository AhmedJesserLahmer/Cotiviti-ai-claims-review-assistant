# Changelog

## [0.2.0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/compare/ai-agent-v0.1.0...ai-agent-v0.2.0) (2026-11-18)


### Features

* **ai-agent:** fall back to cached ML signals when ml-service is down ([fbdaee1](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/fbdaee1e379c2e14dd914272bb0e32c265589e03))
* **ai-agent:** scaffold services/ai-agent service ([0787da5](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/0787da5fe756177932353756ad232b1f1d32364d))
* **ai:** add confidence calibration and abstain-to-human threshold ([0772362](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/0772362f044e4ea78a14cd015d95ede75bae7344))
* **ai:** add grounding check for numbers cited in reasoning ([d706b2b](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/d706b2b56898c4759088e1aad2ed82a6f904e10c))
* **ai:** add hedged requests to cut tail latency ([64cc34f](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/64cc34f35554683d4cb569c0ba919c7f5f36e3cd))
* **ai:** add LLM-as-judge consistency check for approvals ([82cab8e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/82cab8eb1d798c93eceaeda7abf7de5c8eadeab0))
* **ai:** add offline evaluation harness with golden claim set ([c8d2990](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/c8d29905e9f3a9347c2b1efca10fc387193fe9ee))
* **ai:** add OpenAI-compatible provider for cross-vendor fallback ([fa520f1](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/fa520f19906974dfbaa1c2f6e1cc45bded171fab))
* **ai:** add prompt A/B selection through the registry ([cc471e8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/cc471e87975356cf8c3183f913f9cf73dd7733ae))
* **ai:** add response cache for validated LLM results ([da5f7b6](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/da5f7b60e7fa5a72c5d97311b62759907296a8d4))
* **ai:** add token budget and cost accounting per run ([d00ecd8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/d00ecd89a2aaeeb1f13eb9d62ae9e695376a0b3d))
* **ai:** stream analysis progress over server-sent events ([4252251](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/42522516c7365d26b7a0b1d87ac73245eea07e22))
* **ml-service:** add feature validation and out-of-distribution guard ([6b37920](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/6b37920086ec5fa3c4a94ab4f84c6bfba345a4bd))
* **ml-service:** replace the risk classifier, macro-F1 0.35 -&gt; 0.60 ([7c595d7](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7c595d72889583fdb9c105b1c5ad130cea0fd381))
* **obs:** add OpenTelemetry tracing across services ([784cc9e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/784cc9e88c818b53bd141c7ab34e11b734f5fc7f))
* **obs:** add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state) ([88afe20](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/88afe206ddef9b93b0a097af9764107d67892109))
* **security:** add append-only, tamper-evident audit log ([7996f47](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7996f477929afa44a7911719bd1827eebc47b50e))
* **security:** authenticate service-to-service calls ([7fe93d8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7fe93d894d1a8d602bb48e73320d64ce6fbf0573))


### Bug Fixes

* **ai-agent:** answer 422 when a stored claim cannot be scored ([37be410](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/37be4104e2f3fc9da4e792c0642c5e92003f3b3a))
* **ai:** move off the Llama models Groq retired ([e5f8044](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e5f8044b47cece8b6ef428d43ebb442f87d944fd))
* **ai:** use asyncio.timeout so cancelled hedges end cleanly ([a63d8cf](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/a63d8cf7023ceef8ecebb3e174f5c514a97b46b2))


### Refactoring

* **ai-agent:** move agent, AI layer and ML code out of claims-api ([03c2385](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/03c238596c16d64d44b58d115331d278cced55ed))
* **ml-service:** move data generation, training and inference into ml-service ([e2f7fa3](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e2f7fa368cbaa5662e45b0fa998674f4e311a40f))
