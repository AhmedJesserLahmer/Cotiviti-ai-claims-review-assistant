# 0005: Audit log uses HMAC signatures and sequence numbers, not a hash chain

**Context.** Decisions must be traceable and tamper-evident. A hash chain (each entry hashes
the previous one) serializes writers: concurrent replicas would have to read the latest
entry inside a transaction.

**Decision.** Each entry gets an atomic, monotonically increasing `seq` from a counter
document and an HMAC-SHA256 signature over its canonical JSON (`AUDIT_HMAC_KEY`).
Verification checks every signature and that no `seq` is missing.

**Consequences.** Edits and forgeries (without the key) and deletions are detected, with no
write serialization. Reordering is not detected beyond `seq`; truncating the newest entries
is only detected against the counter. Writes are fail-open with a critical alert to
favour availability; the database user should only have insert/find on the collection.
