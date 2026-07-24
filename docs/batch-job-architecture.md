# Batch Job Architecture

Uploads and jobs use UUID directories under `data/uploads` and `data/jobs`.
Metadata and rows are written as JSON through temporary-file replacement. User
filenames are stored as metadata only and never become filesystem paths.

States are `ready`, `running`, `completed`, `completed_with_errors`, `failed`,
and `cancelled`; validation precedes job creation. Progress is derived from
processed unique canonical SMILES. Predictions map back to every source row.

Execution uses one local daemon thread per run and the process-cached ADMET-AI
model. This is an MVP, not durable production infrastructure: jobs have no
cross-machine coordination, automatic cleanup, resume after process failure, or
hard cancellation of an active third-party model call.
