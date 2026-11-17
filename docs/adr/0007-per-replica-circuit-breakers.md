# 0007: Circuit breakers live in process memory

**Context.** A shared breaker (Redis) would let one replica's observations protect all, but
adds a network dependency on the hot path of every LLM call.

**Decision.** Each process keeps its own breaker per provider/model. State is exported as
the `ai_circuit_state` gauge so operators see it fleet-wide.

**Consequences.** With N replicas a dead model costs up to N × threshold failed calls before
every replica stops calling it, which is acceptable for a handful of replicas. One uvicorn
worker per container keeps breaker state and metrics coherent per pod.
