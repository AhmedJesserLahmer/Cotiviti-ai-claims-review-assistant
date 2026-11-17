# 0008: Shared-token service authentication before a service mesh

**Context.** ai-agent and ml-service must not accept calls from arbitrary pods (LLM spend,
re-seeding). mTLS through a service mesh is the long-term answer but a large dependency.

**Decision.** NetworkPolicies restrict who can connect, and an `X-Internal-Token` shared
secret (constant-time comparison, from the secret manager) restricts who is let in.
Production refuses to start internal services without it.

**Consequences.** Two independent layers with little operational cost. The token is
shared, so it identifies "an internal service", not which one; rotate it through the secret
manager. Replace with mesh identities (SPIFFE) when a mesh is adopted.
