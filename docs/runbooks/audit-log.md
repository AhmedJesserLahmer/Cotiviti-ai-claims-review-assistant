# Audit log write failures

**Alert:** `AuditLogWriteFailures`: at least one audit entry failed to write in 10 minutes.

**Meaning:** decisions and reviews are still served (writes are fail-open) but some are not
recorded. This is a compliance incident: treat it as high priority.

1. Logs: `kubectl -n $NS logs deploy/claims-review-ai-agent | grep "audit write failed"`
   (also claims-api). The `error` field usually shows a MongoDB problem (auth, disk, primary
   election).
2. Fix MongoDB, then verify the chain: `GET /admin/audit/verify` (admin token). Gaps in
   `missing_seqs` correspond to the failed writes; record the incident window.
3. Reconstruct missing `ai.decision` entries from `claim_analyses` (each stores its
   `ai_metadata.run_id`) for the incident window and attach them to the incident report.
   Do not insert reconstructed entries into `audit_log`: it must stay append-only and
   machine-written.
4. If `bad_signatures` is non-empty, entries were modified: escalate to security.
