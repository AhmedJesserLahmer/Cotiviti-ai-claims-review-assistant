# Changelog

## [0.2.0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/compare/ml-service-v0.1.0...ml-service-v0.2.0) (2026-11-18)


### Features

* **helm:** add model-training CronJob with artifact volume ([49ba9ed](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/49ba9ed8e6f9deb24ba75c816265dbf45a9a642c))
* **ml-service:** add feature validation and out-of-distribution guard ([6b37920](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/6b37920086ec5fa3c4a94ab4f84c6bfba345a4bd))
* **ml-service:** add versioned model registry and /v1/models ([a2d687c](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/a2d687c7e55a29cea1edb65f0c24ae5ed18727a9))
* **ml-service:** replace the risk classifier, macro-F1 0.35 -&gt; 0.60 ([7c595d7](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7c595d72889583fdb9c105b1c5ad130cea0fd381))
* **ml-service:** scaffold services/ml-service ([9ced282](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/9ced282b600ca0c6440d0c3d7f4a794379951c31))
* **obs:** add OpenTelemetry tracing across services ([784cc9e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/784cc9e88c818b53bd141c7ab34e11b734f5fc7f))
* **obs:** add Prometheus metrics (LLM latency, fallbacks, guardrail hits, breaker state) ([88afe20](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/88afe206ddef9b93b0a097af9764107d67892109))
* **security:** authenticate service-to-service calls ([7fe93d8](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/7fe93d894d1a8d602bb48e73320d64ce6fbf0573))


### Bug Fixes

* **ml-service:** make training idempotent and pandas 3 compatible ([4adc590](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/4adc59098a17b1e5c4553240484bf2f04f7665cd))
* **ml-service:** seed MongoDB at startup only when it is empty ([4f0db69](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/4f0db69bae8d4c1475d66a3a2a9b9103fee047d8))


### Refactoring

* **ml-service:** move data generation, training and inference into ml-service ([e2f7fa3](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e2f7fa368cbaa5662e45b0fa998674f4e311a40f))
