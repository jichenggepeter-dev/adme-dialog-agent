from __future__ import annotations

from agents import RunContextWrapper, function_tool

from app.agent_runtime.tool_service import AgentToolService, ToolExecutionContext


@function_tool(strict_mode=True)
def resolve_compound(ctx: RunContextWrapper[ToolExecutionContext], query: str) -> dict:
    """Resolve a name, CID, or SMILES and create mandatory structure confirmation."""
    return AgentToolService(ctx.context).resolve_compound(query)


@function_tool(strict_mode=True)
def get_compound_context(
    ctx: RunContextWrapper[ToolExecutionContext], compound_id: str
) -> dict:
    """Read a session-owned resolved compound and its confirmation status."""
    return AgentToolService(ctx.context).get_compound_context(compound_id)


@function_tool(strict_mode=True)
def get_input_quality_assessment(
    ctx: RunContextWrapper[ToolExecutionContext], compound_id: str
) -> dict:
    """Return deterministic RDKit input-quality checks, not model confidence."""
    return AgentToolService(ctx.context).get_input_quality_assessment(compound_id)


@function_tool(strict_mode=True)
def predict_single_compound(
    ctx: RunContextWrapper[ToolExecutionContext], compound_id: str
) -> dict:
    """Predict a confirmed session-owned compound through the deterministic service."""
    return AgentToolService(ctx.context).predict_single_compound(compound_id)


@function_tool(strict_mode=True)
def get_prediction_results(
    ctx: RunContextWrapper[ToolExecutionContext],
    prediction_id: str,
    categories: list[str] | None = None,
    endpoints: list[str] | None = None,
) -> dict:
    """Read selected enriched results from a session-owned prediction resource."""
    return AgentToolService(ctx.context).get_prediction_results(
        prediction_id, categories, endpoints
    )


@function_tool(strict_mode=True)
def explain_endpoint(
    ctx: RunContextWrapper[ToolExecutionContext], endpoint_name: str
) -> dict:
    """Return only Endpoint Registry metadata and documented limitations."""
    return AgentToolService(ctx.context).explain_endpoint(endpoint_name)


@function_tool(strict_mode=True)
def search_adme_evidence(
    ctx: RunContextWrapper[ToolExecutionContext], query: str, top_k: int = 3
) -> dict:
    """Retrieve claim-linked passages from the approved local FDA evidence corpus."""
    return AgentToolService(ctx.context).search_adme_evidence(query, top_k)


@function_tool(strict_mode=True)
def get_model_information(ctx: RunContextWrapper[ToolExecutionContext]) -> dict:
    """Return deterministic predictor and Endpoint Registry status."""
    return AgentToolService(ctx.context).get_model_information()


@function_tool(strict_mode=True)
def get_batch_job_status(
    ctx: RunContextWrapper[ToolExecutionContext], job_id: str
) -> dict:
    """Read compact status for an existing local batch job."""
    return AgentToolService(ctx.context).get_batch_job_status(job_id)


@function_tool(strict_mode=True)
def get_batch_errors(
    ctx: RunContextWrapper[ToolExecutionContext], job_id: str
) -> dict:
    """Read a bounded error subset and resource ID for an existing batch job."""
    return AgentToolService(ctx.context).get_batch_errors(job_id)


@function_tool(strict_mode=True)
def summarize_batch_results(
    ctx: RunContextWrapper[ToolExecutionContext],
    job_id: str,
    scope: str = "overview",
    selected_compound_ids: list[str] | None = None,
    selected_endpoints: list[str] | None = None,
) -> dict:
    """Summarize an existing batch without ranking compounds."""
    return AgentToolService(ctx.context).summarize_batch_results(
        job_id, scope, selected_compound_ids, selected_endpoints
    )


@function_tool(strict_mode=True)
def get_batch_rows(
    ctx: RunContextWrapper[ToolExecutionContext],
    job_id: str,
    row_numbers: list[int] | None = None,
    compound_ids: list[str] | None = None,
) -> dict:
    """Read up to five exact rows from an existing batch job."""
    return AgentToolService(ctx.context).get_batch_rows(job_id, row_numbers, compound_ids)


@function_tool(strict_mode=True)
def compare_batch_rows(
    ctx: RunContextWrapper[ToolExecutionContext],
    job_id: str,
    row_numbers: list[int],
    endpoints: list[str],
) -> dict:
    """Neutrally compare documented outputs for two to five completed batch rows."""
    return AgentToolService(ctx.context).compare_batch_rows(job_id, row_numbers, endpoints)


@function_tool(strict_mode=True)
def prepare_batch_action(
    ctx: RunContextWrapper[ToolExecutionContext], job_id: str, action_type: str
) -> dict:
    """Prepare a confirmed run or cancellation; never executes the action directly."""
    return AgentToolService(ctx.context).prepare_batch_action(job_id, action_type)


@function_tool(strict_mode=True)
def compare_compounds(
    ctx: RunContextWrapper[ToolExecutionContext],
    prediction_ids: list[str],
    categories: list[str] | None = None,
    endpoints: list[str] | None = None,
) -> dict:
    """Neutrally compare 2 to 5 completed prediction resources."""
    return AgentToolService(ctx.context).compare_compounds(
        prediction_ids, categories, endpoints
    )


ALLOWED_AGENT_TOOLS = [
    resolve_compound,
    get_compound_context,
    get_input_quality_assessment,
    predict_single_compound,
    get_prediction_results,
    explain_endpoint,
    search_adme_evidence,
    get_model_information,
    get_batch_job_status,
    get_batch_errors,
    summarize_batch_results,
    get_batch_rows,
    compare_batch_rows,
    prepare_batch_action,
    compare_compounds,
]
