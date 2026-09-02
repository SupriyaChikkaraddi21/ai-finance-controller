import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from core.models import AIAnalysis

from ..models import (
    Batch,
    AuditLog,
)

from .agent_loop import run_agent_loop
from .reporting import build_authoritative_controller_report


load_dotenv()


MODEL_NAME = "gemini-3.5-flash-lite"
AGENT_VERSION = "v1"


# ============================================================
# GEMINI CLIENT
# ============================================================

def get_client():

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=120000,
            client_args={
                "trust_env": False,
            },
        ),
    )
def run_controller_agent(
    batch_id
):
    """
    Run the Finance Controller Agent.

    Python gathers and verifies the deterministic financial
    state first. Gemini then performs controller-level
    reasoning over that verified state.

    The deterministic reconciliation engine remains the
    source of financial truth.
    """

    # --------------------------------------------------------
    # GET BATCH
    # --------------------------------------------------------

    batch = Batch.objects.get(
        id=batch_id
    )

    # --------------------------------------------------------
    # START AUDIT LOG
    # --------------------------------------------------------

    AuditLog.objects.create(
        batch=batch,
        action="MANUAL_REVIEW",
        message=(
            "Finance Controller Agent started."
        ),
        metadata={
            "agent_version": AGENT_VERSION,
            "model": MODEL_NAME,
        },
    )

    # --------------------------------------------------------
    # GEMINI CLIENT
    # --------------------------------------------------------

    client = get_client()

    # --------------------------------------------------------
    # REAL AGENT INVESTIGATION
    #
    # Gemini decides which deterministic tools to call.
    # Python executes those tools and returns their results.
    #
    # The deterministic database remains the source of truth.
    # --------------------------------------------------------

    agent_result = run_agent_loop(
        client,
        batch_id,
    )

    final_response = agent_result[
        "final_response"
    ]

    tool_trace = agent_result[
        "tool_trace"
    ]

    # Only successfully verified exceptions count as investigated.
    # Inspecting evidence, AI analysis, or risk alone does not
    # establish completed investigation coverage.
    inspected_reconciliation_ids = {
        trace.get("arguments", {}).get(
            "reconciliation_id"
        )
        for trace in tool_trace
        if (
            trace.get("type") == "TOOL_CALL"
            and trace.get("tool") == "verify_analysis"
            and trace.get("status") == "SUCCESS"
            and isinstance(trace.get("result"), dict)
            and trace.get("result", {}).get("verified") is True
            and trace.get("arguments", {}).get(
                "reconciliation_id"
            ) is not None
        )
    }

    # Existing persisted AI analyses are valid investigation
    # evidence for the controller report. They do not require
    # another Gemini call. Deterministic verification remains
    # authoritative for the final resolution.
    persisted_analysis_ids = set(
        AIAnalysis.objects.filter(
            reconciliation__transaction__batch_id=batch_id
        ).values_list(
            "reconciliation_id",
            flat=True,
        )
    )

    inspected_reconciliation_ids.update(
        persisted_analysis_ids
    )

    tool_call_count = agent_result[
        "tool_call_count"
    ]

    model_call_count = agent_result[
        "model_call_count"
    ]

    llm_status = agent_result.get(
        "llm_status",
        "AVAILABLE",
    )

    llm_error = agent_result.get(
        "llm_error"
    )

    investigation = agent_result.get(
        "investigation",
        {
            "exceptions_available": 0,
            "exceptions_inspected": 0,
            "evidence_inspected": 0,
            "analyses_inspected": 0,
            "analyses_verified": 0,
            "risks_assessed": 0,
            "investigation_coverage": 0,
            "uninspected_exceptions": 0,
        },
    )

    report = build_authoritative_controller_report(
        batch_id=batch_id,
        inspected_reconciliation_ids=(
            inspected_reconciliation_ids
        ),
        investigation=investigation,
        final_response=final_response,
        tool_trace=tool_trace,
        tool_call_count=tool_call_count,
        model_call_count=model_call_count,
        llm_status=llm_status,
        llm_error=llm_error,
    )

    # --------------------------------------------------------
    # COMPLETION AUDIT LOG
    # --------------------------------------------------------

    AuditLog.objects.create(
        batch=batch,
        action="MANUAL_REVIEW",
        message=(
            "Finance Controller Agent completed."
        ),
        metadata={
            "agent_version": AGENT_VERSION,
            "model": MODEL_NAME,
            "model_calls": model_call_count,
            "tool_calls": tool_call_count,
            "exceptions": (
                investigation.get(
                    "exceptions_available",
                    0,
                )
            ),
            "exceptions_investigated": (
                report[
                    "agent"
                ][
                    "exceptions_investigated"
                ]
            ),
            "exceptions_analyzed": (
                report[
                    "agent"
                ][
                    "exceptions_analyzed"
                ]
            ),
            "investigation_coverage": (
                report[
                    "agent"
                ][
                    "investigation_coverage"
                ]
            ),
            "manual_review_required": (
                report[
                    "agent"
                ][
                    "manual_review_required"
                ]
            ),
        },
    )

    # --------------------------------------------------------
    # RETURN FINAL REPORT
    # --------------------------------------------------------

    return report
