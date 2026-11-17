# 0009: Filesystem model registry on a shared volume

**Context.** Models need versioning, metrics, rollback and promotion. MLflow or a cloud
registry would provide that with another service to run.

**Decision.** `ml/registry.py` stores immutable `models/<version>/` directories with a
`manifest.json` (holdout metrics, data hash, feature profile) and an atomic `CURRENT`
pointer, on a ReadWriteMany volume shared by the training CronJob and ml-service.
Scheduled training never activates a version by itself; a person promotes it.

**Consequences.** No extra infrastructure; every prediction reports `model_version`, and
rollback is a pointer change. Missing: experiment tracking UI and lineage beyond the
manifest. Migrate to MLflow if several models or teams need it.
