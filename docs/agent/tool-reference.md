# Agent Tool Reference

Only the following strict function tools are registered:

| Tool | Deterministic dependency | Key policy |
| --- | --- | --- |
| `resolve_compound` | Existing compound resolver + input quality service | Always creates confirmation; never predicts |
| `get_compound_context` | Session resource/business state | Session-owned, compact, confirmation-aware |
| `get_input_quality_assessment` | RDKit deterministic helper | Not model confidence or an AD score |
| `predict_single_compound` | Neutral prediction service | Confirmed compound and exact canonical match required |
| `get_prediction_results` | Session prediction resource | Filtered enriched metadata; no automatic probability interpretation |
| `explain_endpoint` | Endpoint Registry | Unknown/unverified metadata remains neutral |
| `search_adme_evidence` | Approved local FDA evidence index | Claim-linked citations; explicit partial, conflict, stale, missing, and prohibited states |
| `get_model_information` | Predictor status + Registry | Provenance and limitations retained |
| `get_batch_job_status` | Existing batch repository | Read-only compact status |
| `get_batch_errors` | Existing batch rows + resource store | Read-only bounded subset and resource ID |
| `summarize_batch_results` | Existing batch repository | No ranking, winner, or hidden invalid rows |
| `compare_compounds` | Neutral comparison service | Exactly 2-5 completed predictions; no winner |

All tool outputs use a stable envelope with tool name, status, compact data, optional resource ID, stable error code/message, and provenance.

The initial tool set does not include batch run/cancel, export, shell, file, web, MCP, code execution, Registry mutation, deletion, or arbitrary network access.

Large raw predictions and batch error collections are referenced through bounded session resources instead of being copied unconditionally into model context.
