# Changelog

## [0.2.0](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/compare/chart-v0.1.0...chart-v0.2.0) (2026-11-18)


### Features

* **helm:** add claims-review chart foundation ([8640de9](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/8640de9abbd4191871a2a88371d9ff67738bec2d))
* **helm:** add default-deny NetworkPolicies with explicit allow rules ([62506e9](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/62506e9da8eb1419dae747b8c654e96ae33705ef))
* **helm:** add dev, staging and prod values files ([9c13435](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/9c13435af6ed42307519e7d4fcd223b5df745398))
* **helm:** add HorizontalPodAutoscalers ([cd32047](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/cd32047eedd837edf915ffde346458071fd7c94f))
* **helm:** add in-chart MongoDB and Redis for dev and staging ([4243000](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/4243000c0b1095c8beca3777af9aa4ff3cd6dbca))
* **helm:** add Ingress with TLS via cert-manager ([21a6cf7](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/21a6cf7801ce6c488b05da6cce2556d259f8c7a5))
* **helm:** add model-training CronJob with artifact volume ([49ba9ed](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/49ba9ed8e6f9deb24ba75c816265dbf45a9a642c))
* **helm:** add PodDisruptionBudgets ([ff3d292](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/ff3d29290f8b63230a75f6f4410658f74acd9c60))
* **helm:** add workloads for every component ([c3a3a58](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/c3a3a58163521fbc519ea900633303d485c6172c))
* **helm:** run database seeding as a Helm hook Job ([89cf093](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/89cf09395a9bec57fcfa546abffbaf1490598503))
* **helm:** validate values with a JSON schema ([f9bbb82](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/f9bbb826903377e037e02fcb4c414a544f3d405e))
* **obs:** add ServiceMonitors, PrometheusRule and dashboard ConfigMap to the chart ([dfd290e](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/dfd290e92fbc0b4094868b5d6c663c242eef0449))
* **security:** source secrets from External Secrets Operator ([3c6979c](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/3c6979c831de7996dda592d7f2392ab7a80f8fbd))


### Bug Fixes

* **ai:** move off the Llama models Groq retired ([e5f8044](https://github.com/AhmedJesserLahmer/Cotiviti-ai-claims-review-assistant/commit/e5f8044b47cece8b6ef428d43ebb442f87d944fd))
