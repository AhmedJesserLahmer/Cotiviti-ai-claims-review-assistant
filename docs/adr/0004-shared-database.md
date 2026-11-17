# 0004: One MongoDB with per-collection ownership

**Context.** Database-per-service is the textbook microservice rule, but the three services
read the same claim, patient and provider records, and the dataset is small.

**Decision.** One MongoDB database. Each collection has one writer: `ml-service` seeds the
reference data, `claims-api` writes uploads, jobs and feedback, `ai-agent` writes
`claim_analyses`, and both write the append-only `audit_log`. Other services only read.

**Consequences.** No data synchronization or duplication; simple transactions per writer.
Schema changes to a shared collection need coordination (additive changes only, see the
contract tests). Revisit when a service needs a different store or independent scaling of
its data.
