# Data privacy

TalentMatch AI defaults to a local mock provider. In this mode, pasted text stays between the browser, local API process, and configured database; it is not sent to an external model.

Uploaded file bytes are processed transiently in memory and discarded. Saved jobs and candidate resume versions retain normalized text, extraction metadata, structured results, source evidence, recruiter actions, and non-sensitive audit metadata so contextual history and exports work. The Docker volume persists the SQLite database until explicitly removed.

Real-provider analysis requires an explicit transmission confirmation that names the selected provider. Keys entered through Provider settings remain in an expiring API-process memory session. The response contains a masked key and opaque session identifier, never the full key; the browser stores that session identifier in `sessionStorage`. The key is not written to the database. Operators may supply system keys through environment variables instead and are responsible for their secret-management controls. The MVP does not offer persistent user-key storage.

The Privacy screen saves the retention period used by `POST /api/privacy/retention/run`; it does not schedule that endpoint. Operators who require automatic retention must configure an external scheduler. When invoked, retention deletes comparisons older than the cutoff and then removes job and candidate records that have no remaining comparisons. Delete all data permanently removes saved jobs, candidates, resume versions, comparisons, analysis runs, and audit events. Deleting a job removes its linked analyses but retains candidate records. Deleting a candidate removes its resume versions and linked analyses but retains jobs.

Resume data must not be placed in logs, analytics, issue reports, or public sample files. Repository examples are fictional. Operators are responsible for lawful processing, access controls, retention periods, deletion requests, provider terms, and applicable employment and privacy law.

This tool provides evidence-based decision support. It should not be used as the sole basis for employment decisions.
