# Rollback

**Argo CD (production):** set `targetRevision` (and `global.imageTag`) of
`claims-review-prod` back to the previous release tag and sync, or use
*History and Rollback* in the Argo CD UI. Rollbacks are allowed outside the sync window
for release managers (`manualSync: true`).

**Helm (without Argo CD):** `helm -n $NS history claims-review` then
`helm -n $NS rollback claims-review <revision> --wait`.

**Model only:** `POST /v1/models/<previous-version>/activate` on ml-service, or pin
`MODEL_VERSION` in the values. Versions are immutable, so the old one is still there.

**Prompt only:** set the experiment's share to 0 in `AI_PROMPT_TRAFFIC` (takes effect on
restart), or revert the commit that changed the default prompt version.

Data is forward-compatible: new wire fields are optional (contract tests enforce it), so
an older service version can read records written by a newer one.
