import json
import os

from google import genai
from google.genai import types
from dotenv import load_dotenv

from django.db import transaction

from ..models import (
    Batch,
    AuditLog,
)

from .tools import (
    get_batch_summary,
    get_batch_exceptions,
    get_transaction_evidence,
    get_ai_analysis,
    verify_ai_analysis,
    build_controller_report,
    assess_exception_risk,

)
from core.ai_analysis_service import analyze_exception

from .prompts import (
    CONTROLLER_SYSTEM_PROMPT,
    CONTROLLER_TASK_PROMPT,
)


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
        api_key=api_key
    )


# ============================================================
# AGENT TOOLS
# ============================================================

def inspect_batch(
    batch_id: int
):

    return get_batch_summary(
        batch_id
    )


def inspect_exceptions(
    batch_id: int
):

    return get_batch_exceptions(
        batch_id
    )


def inspect_evidence(
    reconciliation_id: int
):

    return get_transaction_evidence(
        reconciliation_id
    )


def inspect_ai_analysis(
    reconciliation_id: int
):

    return get_ai_analysis(
        reconciliation_id
    )


def verify_analysis(
    reconciliation_id: int
):

    return verify_ai_analysis(
        reconciliation_id
    )
def assess_risk(
    reconciliation_id: int
):
    return assess_exception_risk(
        reconciliation_id
    )


# ============================================================
# TOOL DECLARATIONS
# ============================================================

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="inspect_batch",
                description=(
                    "Inspect deterministic financial "
                    "metrics for a reconciliation batch."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "batch_id"
                    ],
                },
            ),

            types.FunctionDeclaration(
                name="inspect_exceptions",
                description=(
                    "Retrieve deterministic exceptions "
                    "for a reconciliation batch."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "batch_id": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "batch_id"
                    ],
                },
            ),

            types.FunctionDeclaration(
                name="inspect_evidence",
                description=(
                    "Inspect complete financial evidence "
                    "for one reconciliation exception."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "reconciliation_id": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "reconciliation_id"
                    ],
                },
            ),

            types.FunctionDeclaration(
                name="inspect_ai_analysis",
                description=(
                    "Retrieve an existing AI analysis "
                    "for an exception."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "reconciliation_id": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "reconciliation_id"
                    ],
                },
            ),

            types.FunctionDeclaration(
                name="verify_analysis",
                description=(
                    "Verify whether an AI classification "
                    "is supported by deterministic evidence."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "reconciliation_id": {
                            "type": "integer"
                        }
                    },
                    "required": [
                        "reconciliation_id"
                    ],
                },
            ),
            types.FunctionDeclaration(
    name="assess_risk",
    description=(
        "Assess the operational and financial risk "
        "of one reconciliation exception. "
        "Use this to determine investigation priority "
        "and whether manual review may be required."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "reconciliation_id": {
                "type": "integer"
            }
        },
        "required": [
            "reconciliation_id"
        ],
    },
),
        ]
    )
]


# ============================================================
# TOOL DISPATCH
# ============================================================

def execute_tool(
    name,
    arguments,
):

    if name == "inspect_batch":

        return inspect_batch(
            arguments["batch_id"]
        )

    if name == "inspect_exceptions":

        return inspect_exceptions(
            arguments["batch_id"]
        )

    if name == "inspect_evidence":

        return inspect_evidence(
            arguments["reconciliation_id"]
        )

    if name == "inspect_ai_analysis":

        return inspect_ai_analysis(
            arguments["reconciliation_id"]
        )

    if name == "verify_analysis":

        return verify_analysis(
            arguments["reconciliation_id"]
        )
    if name == "assess_risk":

        return assess_risk(
            arguments["reconciliation_id"]
            )
    raise ValueError(
        f"Unknown agent tool: {name}"
    )


# ============================================================
# RUN AGENT
# ============================================================
# ============================================================
# RUN AGENT
# ============================================================

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
            "agent_version": "v2",
            "model": MODEL_NAME,
        },
    )

    # --------------------------------------------------------
    # GEMINI CLIENT
    # --------------------------------------------------------

    client = get_client()

    # --------------------------------------------------------
    # BUILD DETERMINISTIC CONTROLLER STATE
    #
    # Python gathers the financial evidence FIRST.
    #
    # Gemini does not determine financial truth.
    # --------------------------------------------------------

    summary = get_batch_summary(
        batch_id
    )

    exceptions = get_batch_exceptions(
        batch_id
    )
    analyses = []

    for exception in exceptions:

        reconciliation_id = (
            exception[
                "reconciliation_id"
            ]
        )

        # ------------------------------------------------
        # CHECK WHETHER AI ANALYSIS ALREADY EXISTS
        # ------------------------------------------------

        ai_analysis = get_ai_analysis(
            reconciliation_id
        )

        # ------------------------------------------------
        # GENERATE AI ANALYSIS IF MISSING
        # ------------------------------------------------
        if not ai_analysis["available"]:

            try:

                analyze_exception(
                    reconciliation_id
                )

                # Fetch the newly created analysis
                ai_analysis = get_ai_analysis(
                    reconciliation_id
                )

            except Exception as error:

                risk = assess_risk(
                    reconciliation_id
                )

                analyses.append(
                    {
                        "reconciliation_id": (
                            reconciliation_id
                        ),
                        "transaction_id": (
                            exception[
                                "transaction_id"
                            ]
                        ),
                        "deterministic_exception": (
                            exception[
                                "exception_type"
                            ]
                        ),
                        "classification": None,
                        "confidence": None,
                        "resolution": (
                            "MANUAL_REVIEW"
                        ),
                        "verified": False,
                        "reason": (
                            "AI analysis unavailable: "
                            + str(error)
                        ),
                        "risk_level": (
                            risk["risk_level"]
                        ),
                        "risk_reasons": (
                            risk["reasons"]
                        ),
                    }
                )

                # AI failure must never stop the
                # deterministic controller.
                continue
        # ------------------------------------------------
        # ASSESS EXCEPTION RISK
        # ------------------------------------------------

        risk = assess_risk(
            reconciliation_id
        )

        # ------------------------------------------------
        # VERIFY AI ANALYSIS
        # ------------------------------------------------

        verification = verify_ai_analysis(
            reconciliation_id
        )
        # ------------------------------------------------
        # STORE VERIFIED ANALYSIS
        # ------------------------------------------------

        analyses.append(
            {
                "reconciliation_id": (
                    reconciliation_id
                ),
                "transaction_id": (
                    exception[
                        "transaction_id"
                    ]
                ),
                "deterministic_exception": (
                    exception[
                        "exception_type"
                    ]
                ),
                "classification": (
                    ai_analysis[
                        "classification"
                    ]
                ),
                "confidence": (
                    ai_analysis[
                        "confidence"
                    ]
                ),
                "resolution": (
                    verification[
                        "resolution"
                    ]
                ),
                "verified": (
                    verification[
                        "verified"
                    ]
                ),
                "reason": (
                    verification[
                        "reason"
                    ]
                ),
                "risk_level": (
                    risk["risk_level"]
                ),
                "risk_reasons": (
                    risk["reasons"]
                ),

            }
        )
    # --------------------------------------------------------
    # BUILD VERIFIED CONTROLLER STATE
    #
    # Python is authoritative for all financial counts.
    # Gemini is responsible only for interpretation,
    # prioritization, and recommendations.
    # --------------------------------------------------------

    exception_counts = {}

    for exception in exceptions:
        exception_type = (
            exception["exception_type"]
            or "UNKNOWN"
        )

        exception_counts[exception_type] = (
            exception_counts.get(
                exception_type,
                0
            ) + 1
        )

    confirmed_count = sum(
        1
        for analysis in analyses
        if analysis["resolution"] == "CONFIRMED"
    )

    manual_review_count = sum(
        1
        for analysis in analyses
        if analysis["resolution"] == "MANUAL_REVIEW"
    )

    controller_state = {
        "batch": summary,

        "authoritative_exception_counts": {
            "total": len(exceptions),
            "by_type": exception_counts,
            "confirmed": confirmed_count,
            "manual_review_required": (
                manual_review_count
            ),
        },

        "exceptions": exceptions,

        "verified_analyses": analyses,
    }
    # --------------------------------------------------------
    # DETERMINISTIC RISK GROUPS
    # Python calculates these counts.
    # Gemini only explains and prioritizes them.
    # --------------------------------------------------------

    high_risk_exceptions = [
        analysis
        for analysis in analyses
        if analysis["risk_level"] == "HIGH"
    ]

    medium_risk_exceptions = [
        analysis
        for analysis in analyses
        if analysis["risk_level"] == "MEDIUM"
    ]

    risk_summary = {
        "high_risk_count": len(
            high_risk_exceptions
        ),
        "medium_risk_count": len(
            medium_risk_exceptions
        ),
        "high_risk_reconciliation_ids": [
            analysis["reconciliation_id"]
            for analysis in high_risk_exceptions
        ],
        "medium_risk_reconciliation_ids": [
            analysis["reconciliation_id"]
            for analysis in medium_risk_exceptions
        ],
    }
    # --------------------------------------------------------
    # GEMINI CONTROLLER PROMPT
    #
    # Gemini receives verified financial state.
    # It does NOT modify or invent financial facts.
    # --------------------------------------------------------

    prompt = (
        CONTROLLER_SYSTEM_PROMPT
        + "\n\n"
        + CONTROLLER_TASK_PROMPT.format(
            batch_id=batch_id
        )
        + "\n\n"
        "You are the Finance Controller Agent.\n\n"

        "The following financial state has already been "
        "calculated by deterministic backend logic.\n\n"

        "IMPORTANT: The deterministic backend is the "
        "SOURCE OF TRUTH for every financial number, "
        "count, exception type, transaction ID, and "
        "resolution status.\n\n"
        "AUTHORITATIVE DETERMINISTIC FACTS:\n"
        + json.dumps(
            {
                "batch": summary,
                "exception_counts": {
                    "total": len(exceptions),
                    "by_type": exception_counts,
                    "confirmed": confirmed_count,
                    "manual_review_required": (
                        manual_review_count
                    ),
                },
                "risk_summary": risk_summary,
            },
            indent=2,

        )
        + "\n\n"

        "FULL VERIFIED EXCEPTION DATA:\n"
        + json.dumps(
            exceptions,
            indent=2,
        )
        + "\n\n"

        "VERIFIED AI ANALYSES:\n"
        + json.dumps(
            analyses,
            indent=2,
        )
        + "\n\n"

        "STRICT CONTROLLER RULES:\n"
        "1. The deterministic backend is the sole source of truth "
        "for all financial facts.\n"

        "2. Never recalculate, recount, estimate, or infer "
        "deterministic financial numbers.\n"

        "3. Never independently count reconciliation IDs in the "
        "provided lists.\n"

        "4. Never change the authoritative total exception count, "
        "exception-type counts, confirmed count, manual-review "
        "count, or risk counts.\n"

        "5. When mentioning a group of exceptions, use the exact "
        "group count supplied by the backend. Do not calculate "
        "the count from the ID ranges yourself.\n"

        "6. Never invent transaction IDs, reconciliation IDs, "
        "exception types, risk levels, or financial amounts.\n"

        "7. Clearly distinguish CONFIRMED exceptions from "
        "MANUAL_REVIEW exceptions.\n"

        "8. The backend risk_level and risk_reasons are "
        "authoritative. Never downgrade HIGH risk to MEDIUM or "
        "LOW. Never upgrade LOW risk without explicit "
        "deterministic evidence.\n"

        "9. You may explain operational implications and "
        "recommend investigation priorities, but you must not "
        "alter financial facts.\n"

        "10. If evidence is insufficient to establish a root "
        "cause, explicitly classify the item as MANUAL_REVIEW.\n"

        "11. Do not state that a group contains a specific number "
        "of items unless that number is explicitly present in the "
        "authoritative backend data.\n"

        "12. If an ID range is displayed, treat it only as a list "
        "of identifiers. Never use the range to derive a count.\n"

        "13. Use INR (₹) for all monetary amounts. Never use $, "
        "USD, or other currency symbols.\n\n"
        "14. Preserve every deterministic exception_type exactly "
        "as provided by the backend. Never rename, normalize, "
        "reinterpret, or replace exception types.\n"

        "15. The authoritative exception types are "
        "MISSING_SETTLEMENT, MISSING_PAYMENT, UNKNOWN, "
        "STATUS_MISMATCH, and DUPLICATE. Use these exact names "
        "when referring to exception types.\n"

        "16. Do not introduce alternative classification labels "
        "such as MISSING_RECORD, STATUS_ISSUE, "
        "AMOUNT_DISCREPANCY, or similar labels unless they "
        "already exist in the authoritative backend data.\n"
    )
    # --------------------------------------------------------
    # MODEL EXECUTION
    # --------------------------------------------------------

    tool_trace = []

    tool_call_count = 0

    model_call_count = 0

    max_model_calls = 1

    max_tool_calls = 0

    final_response = None

    llm_status = "NOT_STARTED"

    llm_error = None

    try:

        model_call_count += 1

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            ),
        )

        llm_status = "AVAILABLE"

        final_response = (
            response.text
            if response.text
            else "Controller completed."
        )

    except Exception as error:

        llm_status = "UNAVAILABLE"

        llm_error = str(error)

        final_response = (
            "Gemini reasoning was unavailable. "
            "Deterministic reconciliation results remain "
            "the source of financial truth. "
            "Unresolved exceptions require manual review."
        )

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    if final_response is None:

        final_response = (
            "Finance Controller Agent completed with "
            "deterministic reconciliation results. "
            "Manual review is required for unresolved "
            "exceptions."
        )

    # --------------------------------------------------------
    # BUILD FINAL CONTROLLER REPORT
    #
    # Financial truth comes from the deterministic backend.
    # --------------------------------------------------------

    report = build_controller_report(
        batch_id,
        analyses,
    )

    # --------------------------------------------------------
    # ADD AGENT METADATA
    # --------------------------------------------------------

    report["agent_summary"] = (
        final_response
    )

    report["agent_version"] = "v2"

    report["model"] = MODEL_NAME

    report["llm_status"] = llm_status

    if llm_error is not None:

        report["llm_error"] = llm_error

    report["tool_calls"] = (
        tool_call_count
    )

    report["model_calls"] = (
        model_call_count
    )

    report["tool_trace"] = (
        tool_trace
    )

    report["agent_mode"] = (
        "BATCH_REASONING_CONTROLLER"
    )
    # --------------------------------------------------------
    # DETERMINISTIC RISK SUMMARY
    # --------------------------------------------------------

    report["risk_summary"] = {
        "high_risk_count": len(
            high_risk_exceptions
        ),
        "medium_risk_count": len(
            medium_risk_exceptions
        ),
        "high_risk_reconciliation_ids": [
            analysis["reconciliation_id"]
            for analysis in high_risk_exceptions
        ],
        "medium_risk_reconciliation_ids": [
            analysis["reconciliation_id"]
            for analysis in medium_risk_exceptions
        ],
    }
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
            "agent_version": "v2",
            "model": MODEL_NAME,
            "model_calls": model_call_count,
            "tool_calls": tool_call_count,
            "exceptions": len(
                exceptions
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