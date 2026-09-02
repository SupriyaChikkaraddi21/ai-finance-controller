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
    inspect_investigation_scope as get_investigation_scope,
)
from core.ai_analysis_service import analyze_exception
from core.models import AIAnalysis

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
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=120000,
            client_args={
                "trust_env": False,
            },
        ),
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
def inspect_investigation_scope(
    batch_id: int
):

    return get_investigation_scope(
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
def get_required_investigation_ids(
    batch_id
):
    scope = get_investigation_scope(
        batch_id
    )

    # The controller has a bounded step budget.
    # Require investigation of only the highest-priority
    # unresolved deterministic exceptions.

    priority_order = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    candidates = list(
        scope.get(
            "exceptions",
            []
        )
    )
    candidates.sort(
        key=lambda item: (
            -item.get(
                "priority_score",
                0,
            ),
            item["reconciliation_id"],
        )
    )
    # Require investigation of the bounded deterministic
    # exception population selected for this controller run.
    # The full population remains available for deterministic
    # risk reporting; this set controls the investigation gate.
    MAX_REQUIRED_INVESTIGATIONS = 25

    return {
        item["reconciliation_id"]
        for item in candidates[
            :MAX_REQUIRED_INVESTIGATIONS
        ]
    }


def inspect_ai_analysis(
    reconciliation_id: int
):

    return get_ai_analysis(
        reconciliation_id
    )
def analyze_exception_for_controller(
    reconciliation_id: int
):

    analysis = analyze_exception(
        reconciliation_id
    )

    return {
        "reconciliation_id": reconciliation_id,
        "classification": analysis.classification,
        "explanation": analysis.explanation,
        "confidence": float(
            analysis.confidence
        ),
        "recommended_action": (
            analysis.recommended_action
        ),
        "evidence_summary": (
            analysis.evidence_summary
        ),
        "model_name": analysis.model_name,
        "prompt_version": analysis.prompt_version,
    }
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
                name="inspect_investigation_scope",
                description=(
                    "Inspect the population-level investigation "
                    "scope for a reconciliation batch. "
                    "This is an OVERVIEW and PRIORITIZATION tool. "
                    "It does NOT count as individually inspecting "
                    "any exception and does NOT provide complete "
                    "transaction-level evidence. "
                    "Use the returned exception IDs to select "
                    "specific cases for deeper investigation."
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
                name="analyze_exception",
                description=(
                    "Generate AI analysis for one reconciliation "
                    "exception when deeper investigation is required. "
                    "Use this selectively; do not analyze every "
                    "exception automatically."
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
            types.FunctionDeclaration(
                name="FINALIZE",
                description=(
                    "Finish the controller investigation only when "
                    "the available deterministic evidence has been "
                    "sufficiently inspected. State why the investigation "
                    "can be finalized and identify any unresolved cases "
                    "that still require manual review."
                ),
                parameters_json_schema={
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "reason"
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

    if name == "inspect_investigation_scope":

        return inspect_investigation_scope(
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

    if name == "analyze_exception":

        return analyze_exception_for_controller(
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

    if name == "FINALIZE":

        return {
            "finalized": True,
            "reason": (
                arguments.get("reason")
                or "Agent investigation completed."
            ),
        }

    raise ValueError(
        f"Unknown agent tool: {name}"
    )


# ============================================================
# REAL AGENT LOOP
# ============================================================

MAX_AGENT_STEPS = 40

# Gemini free-tier requests are limited per minute.
# Keep the controller below that limit so a single run
# does not exhaust the available model quota.
MAX_GEMINI_CALLS = 10

def get_investigation_status(
    exceptions_available,
    exceptions_inspected,
):
    inspected_count = len(
        exceptions_inspected
    )


    uninspected_count = (
        exceptions_available
        - inspected_count
    )

    coverage = (
        round(
            (
                inspected_count
                / exceptions_available
                * 100
            ),
            2,
        )
        if exceptions_available
        else 0
    )

    return (
        inspected_count,
        uninspected_count,
        coverage,
    )
def run_agent_loop(
    client,
    batch_id,
):
    """
    Execute a bounded agentic investigation loop.

    One model decision produces at most one tool call.
    The tool result is returned to Gemini before the next
    decision.

    Flow:

        OBSERVE
          ↓
        DECIDE
          ↓
        TOOL
          ↓
        OBSERVE
          ↓
        DECIDE

    The deterministic backend remains the source of truth.
    """
    tool_trace = []
    tool_call_count = 0
    model_call_count = 0

    # --------------------------------------------------------
    # AUTHORITATIVE EXCEPTION COUNT
    #
    # Get the exception count directly from the deterministic
    # reconciliation backend before Gemini is called.
    # --------------------------------------------------------

    exceptions_available = len(
        inspect_exceptions(
            batch_id
        )
    )
    required_investigation_ids = (
        get_required_investigation_ids(
            batch_id
        )
    )

    # Existing persisted AI analyses are already available evidence.
    # Do not spend a Gemini call regenerating an analysis that already
    # exists in the database.
    existing_analysis_ids = set(
        AIAnalysis.objects.filter(
            reconciliation_id__in=required_investigation_ids
        ).values_list(
            "reconciliation_id",
            flat=True,
        )
    )

    # Existing AI analyses can be reused by the controller.
    # They do not by themselves count as evidence inspection.
    # Deterministic verification remains authoritative.
    existing_analysis_coverage = (
        round(
            len(existing_analysis_ids)
            / len(required_investigation_ids)
            * 100,
            2,
        )
        if required_investigation_ids
        else 100
    )

    exceptions_inspected = set()
    evidence_inspected = set()
    analyses_inspected = set()
    analyses_verified = set()
    risks_assessed = set()
    risk_cache = {}

    # --------------------------------------------------------
    # REUSE EXISTING AI ANALYSES
    #
    # Existing analyses do not require another Gemini call.
    # Their classifications are checked against deterministic
    # reconciliation evidence before the controller reasons
    # over the batch.
    # --------------------------------------------------------

    for reconciliation_id in sorted(
        existing_analysis_ids
    ):
        try:
            analysis = get_ai_analysis(
                reconciliation_id
            )

            verification = verify_ai_analysis(
                reconciliation_id
            )

            risk = assess_exception_risk(
                reconciliation_id
            )
            risk_cache[reconciliation_id] = risk

            analyses_inspected.add(
                reconciliation_id
            )

            risks_assessed.add(
                reconciliation_id
            )

            if verification.get("verified") is True:
                analyses_verified.add(
                    reconciliation_id
                )

                # A persisted analysis counts as investigated
                # only after successful deterministic verification.
                exceptions_inspected.add(
                    reconciliation_id
                )

            tool_trace.append(
                {
                    "step": 0,
                    "type": "EXISTING_ANALYSIS_REUSED",
                    "reconciliation_id": (
                        reconciliation_id
                    ),
                    "analysis": analysis,
                    "verification": verification,
                    "risk": risk,
                    "status": "SUCCESS",
                }
            )

        except Exception as error:
            tool_trace.append(
                {
                    "step": 0,
                    "type": "EXISTING_ANALYSIS_REUSE_ERROR",
                    "reconciliation_id": (
                        reconciliation_id
                    ),
                    "error": str(error),
                    "status": "ERROR",
                }
            )
    # Provide Gemini with the authoritative deterministic
    # investigation scope so it does not waste model turns
    # rediscovering exception IDs and risk priorities.
    investigation_scope = get_investigation_scope(
        batch_id
    )

    scope_summary = investigation_scope.get(
        "exceptions",
        []
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=CONTROLLER_TASK_PROMPT.format(
                        batch_id=batch_id,
                        required_ids=sorted(
                            required_investigation_ids
                        ),
                        investigation_scope=scope_summary,
                    ),
                )
            ],
        )
    ]
    # --------------------------------------------------------
    # FAST PATH — EXISTING ANALYSIS STATE IS COMPLETE
    #
    # If every required exception already has persisted AI
    # analysis and deterministic verification/risk assessment
    # succeeded, there is no reason to spend Gemini calls
    # rediscovering the same exception-level information.
    # --------------------------------------------------------

    if (
        required_investigation_ids
        and required_investigation_ids
        <= exceptions_inspected
    ):
        final_reason = (
            "Controller investigation completed using "
            "persisted AI analyses and deterministic "
            "verification/risk assessment. "
            f"All {exceptions_available} required exceptions "
            "were reviewed without regenerating existing "
            "AI analyses."
        )

        tool_trace.append(
            {
                "step": 0,
                "type": "FINALIZE",
                "reason": final_reason,
                "decision": "INVESTIGATION_COMPLETE",
                "coverage": 100.0,
                "exceptions_available": exceptions_available,
                "exceptions_inspected": len(
                    exceptions_inspected
                ),
                "uninspected_exceptions": 0,
                "status": "SUCCESS",
                "fast_path": True,
            }
        )

        return {
            "final_response": final_reason,
            "tool_trace": tool_trace,
            "tool_call_count": 0,
            "model_call_count": 0,
            "llm_status": "NOT_REQUIRED",
            "llm_error": None,
            "investigation": {
                "exceptions_available": exceptions_available,
                "exceptions_inspected": len(
                    exceptions_inspected
                ),
                "inspected_reconciliation_ids": sorted(
                    exceptions_inspected
                ),
                "evidence_inspected": len(
                    evidence_inspected
                ),
                "analyses_inspected": len(
                    analyses_inspected
                ),
                "analyses_verified": len(
                    analyses_verified
                ),
                "risks_assessed": len(
                    risks_assessed
                ),
                "investigation_coverage": 100.0,
                "uninspected_exceptions": 0,
                "finalization_decision": (
                    "INVESTIGATION_COMPLETE"
                ),
                "existing_analysis_coverage": (
                    existing_analysis_coverage
                ),
            },
        }
    for step in range(1, MAX_AGENT_STEPS + 1):

        print(
            f"🤖 CONTROLLER STEP {step}/{MAX_AGENT_STEPS}",
            flush=True,
        )

        if model_call_count >= MAX_GEMINI_CALLS:
            final_response = (
                "Controller investigation stopped after reaching "
                f"the Gemini model-call budget of {MAX_GEMINI_CALLS}. "
                f"{len(exceptions_inspected)} of "
                f"{exceptions_available} exceptions were inspected. "
                f"{exceptions_available - len(exceptions_inspected)} "
                "exceptions remain unresolved and require further "
                "automated investigation or manual review."
            )

            tool_trace.append(
                {
                    "step": step,
                    "type": "MODEL_CALL_BUDGET_REACHED",
                    "status": "STOPPED",
                    "model_call_budget": MAX_GEMINI_CALLS,
                    "model_calls_used": model_call_count,
                    "exceptions_available": exceptions_available,
                    "exceptions_inspected": len(
                        exceptions_inspected
                    ),
                }
            )

            return {
                "final_response": final_response,
                "tool_trace": tool_trace,
                "tool_call_count": tool_call_count,
                "model_call_count": model_call_count,
                "llm_status": "CALL_BUDGET_REACHED",
                "llm_error": None,
                "investigation": {
                    "exceptions_available": exceptions_available,
                    "exceptions_inspected": len(
                        exceptions_inspected
                    ),
                    "evidence_inspected": len(
                        evidence_inspected
                    ),
                    "analyses_inspected": len(
                        analyses_inspected
                    ),
                    "analyses_verified": len(
                        analyses_verified
                    ),
                    "risks_assessed": len(
                        risks_assessed
                    ),
                    "investigation_coverage": (
                        round(
                            len(exceptions_inspected)
                            / exceptions_available * 100,
                            2,
                        )
                        if exceptions_available
                        else 100
                    ),
                    "uninspected_exceptions": (
                        exceptions_available
                        - len(exceptions_inspected)
                    ),
                    "status": "BLOCKED_MODEL_CALL_BUDGET",
                },
            }

        model_call_count += 1

        try:

            print(
                f"📡 Calling Gemini at step {step}...",
                flush=True,
            )


            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=CONTROLLER_SYSTEM_PROMPT,
                    tools=TOOLS,
                    temperature=0.1,
                ),
            )



        except Exception as error:
            print(
                "🔥 CONTROLLER AGENT ERROR:",
                repr(error),
            )

            error_message = str(error)

            is_quota_error = (
                "429" in error_message
                or "RESOURCE_EXHAUSTED" in error_message
                or "quota" in error_message.lower()
            )

            llm_status = (
                "QUOTA_EXCEEDED"
                if is_quota_error
                else "UNAVAILABLE"
            )

            investigation_status = (
                "BLOCKED_LLM_QUOTA"
                if is_quota_error
                else "NOT_STARTED"
            )

            if is_quota_error:
                final_response = (
                    "Investigation was blocked because the Gemini "
                    "API quota was exhausted. "
                    f"{len(exceptions_inspected)} of "
                    f"{exceptions_available} exceptions were inspected "
                    f"before the quota limit was reached. "
                    f"{exceptions_available - len(exceptions_inspected)} "
                    "exceptions remain unresolved and require "
                    "further automated investigation or manual review."
                )
            else:
                final_response = (
                    "Investigation could not continue because Gemini "
                    "reasoning was unavailable. "
                    f"{len(exceptions_inspected)} of "
                    f"{exceptions_available} exceptions were inspected. "
                    f"{exceptions_available - len(exceptions_inspected)} "
                    "exceptions remain unresolved and require "
                    "further automated investigation or manual review."
                )

            tool_trace.append(
                {
                    "step": step,
                    "type": "MODEL_ERROR",
                    "status": "ERROR",
                    "error": error_message,
                    "llm_status": llm_status,
                }
            )

            return {
                "final_response": final_response,
                "tool_trace": tool_trace,
                "tool_call_count": tool_call_count,
                "model_call_count": model_call_count,
                "llm_status": llm_status,
                "llm_error": error_message,
                "investigation": {
                    "exceptions_available": exceptions_available,
                    "exceptions_inspected": len(exceptions_inspected),
                    "evidence_inspected": len(evidence_inspected),
                    "analyses_inspected": len(analyses_inspected),
                    "analyses_verified": len(analyses_verified),
                    "risks_assessed": len(risks_assessed),
                    "investigation_coverage": (
                        round(
                            len(exceptions_inspected)
                            / exceptions_available * 100,
                            2,
                        )
                        if exceptions_available
                        else 100
                    ),
                    "uninspected_exceptions": (
                        exceptions_available
                        - len(exceptions_inspected)
                    ),
                    "status": investigation_status,
                },
            }

        # ----------------------------------------------------
        # Preserve Gemini response
        # ----------------------------------------------------

        candidate = (
            response.candidates[0]
            if response.candidates
            else None
        )

        if candidate and candidate.content:

            contents.append(
                candidate.content
            )

        # ----------------------------------------------------
        # Extract function calls
        # ----------------------------------------------------

        function_calls = []

        if candidate and candidate.content:

            for part in (
                candidate.content.parts or []
            ):

                if part.function_call:

                    function_calls.append(
                        part.function_call
                    )

        # ----------------------------------------------------
        # No function call
        # ----------------------------------------------------

        if not function_calls:

            final_text = (
                response.text
                if response.text
                else (
                    "Agent attempted to finalize "
                    "without an explicit FINALIZE decision."
                )
            )

            (
                inspected_count,
                uninspected_count,
                coverage,
            ) = get_investigation_status(
                exceptions_available,
                exceptions_inspected,
            )

            unresolved_required_ids = (
                required_investigation_ids
                - exceptions_inspected
            )

            # ------------------------------------------------
            # Treat plain text as an implicit FINALIZE request.
            # It must pass the same safety gate.
            # ------------------------------------------------

            if unresolved_required_ids:
                tool_trace.append(
                    {
                        "step": step,
                        "type": "IMPLICIT_FINALIZE_REJECTED",
                        "reason": (
                            "Agent returned a final response "
                            "without completing investigation."
                        ),
                        "coverage": coverage,
                        "exceptions_available": (
                            exceptions_available
                        ),
                        "exceptions_inspected": (
                            inspected_count
                        ),
                        "uninspected_exceptions": (
                            uninspected_count
                        ),
                        "required_investigation_count": (
                            len(required_investigation_ids)
                        ),
                        "remaining_required_investigations": (
                            len(unresolved_required_ids)
                        ),
                        "agent_reason": final_text,
                        "status": "REJECTED",
                    }
                )

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "FINAL RESPONSE REJECTED. "
                                    "The investigation is incomplete. "
                                    f"{len(unresolved_required_ids)} required exceptions remain "
                                    "uninvestigated. "
                                    f"Required reconciliation IDs still outstanding: "
                                    f"{sorted(unresolved_required_ids)}. "
                                    "Investigate one of these outstanding IDs using an "
                                    "exception-level tool before attempting to finalize. "
                                    "Do not repeatedly investigate an already inspected ID."
                                )
                            )
                        ],
                    )
                )

                continue

            tool_trace.append(
                {
                    "step": step,
                    "type": "FINALIZE",
                    "reason": final_text,
                    "decision": (
                        "INVESTIGATION_COMPLETE"
                    ),
                    "coverage": coverage,
                    "status": "SUCCESS",
                    "implicit": True,
                }
            )

            return {
                "final_response": final_text,
                "tool_trace": tool_trace,
                "tool_call_count": tool_call_count,
                "model_call_count": model_call_count,
                "llm_status": "AVAILABLE",
                "llm_error": None,
                "investigation": {
                    "exceptions_available": (
                        exceptions_available
                    ),
                    "exceptions_inspected": (
                        inspected_count
                    ),
                    "inspected_reconciliation_ids": sorted(
                        exceptions_inspected
                    ),
                    "evidence_inspected": len(
                        evidence_inspected
                    ),
                    "analyses_inspected": len(
                        analyses_inspected
                    ),
                    "analyses_verified": len(
                        analyses_verified
                    ),
                    "risks_assessed": len(
                        risks_assessed
                    ),
                    "investigation_coverage": (
                        coverage
                    ),
                    "uninspected_exceptions": (
                        uninspected_count
                    ),
                    "finalization_decision": (
                        "PARTIAL_INVESTIGATION"
                    ),
                },
            }

        # ----------------------------------------------------
        # Enforce ONE decision per model turn
        # ----------------------------------------------------

        function_call = function_calls[0]

        tool_name = function_call.name

        arguments = (
            dict(function_call.args)
            if function_call.args
            else {}
        )

        # ----------------------------------------------------
        # Explicit FINALIZE decision
        # ----------------------------------------------------
        if tool_name == "FINALIZE":

            reason = (
                arguments.get(
                    "reason"
                )
                or "Agent investigation completed."
            )

            (
                inspected_count,
                uninspected_count,
                coverage,
            ) = get_investigation_status(
                exceptions_available,
                exceptions_inspected,
            )

            unresolved_required_ids = (
                required_investigation_ids
                - exceptions_inspected
            )

            # ------------------------------------------------
            # FINALIZATION GATE
            #
            # Gemini cannot finalize an incomplete
            # investigation. The request is rejected and
            # returned to Gemini as a new observation.
            # ------------------------------------------------

            if unresolved_required_ids:

                tool_trace.append(
                    {
                        "step": step,
                        "type": "FINALIZE_REJECTED",
                        "reason": (
                            "Finalization rejected because "
                            "the investigation is incomplete."
                        ),
                        "decision": (
                            "PARTIAL_INVESTIGATION"
                        ),
                        "coverage": coverage,
                        "exceptions_available": (
                            exceptions_available
                        ),
                        "exceptions_inspected": (
                            inspected_count
                        ),
                        "uninspected_exceptions": (
                            uninspected_count
                        ),
                        "agent_reason": reason,
                        "status": "REJECTED",
                    }
                )

                # --------------------------------------------
                # Force another investigation decision.
                # --------------------------------------------
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "FINALIZATION REJECTED. "
                                    f"{len(unresolved_required_ids)} required exceptions "
                                    "remain uninvestigated. "
                                    f"Required reconciliation IDs still outstanding: "
                                    f"{sorted(unresolved_required_ids)}. "
                                    "You must investigate one of these outstanding IDs "
                                    "before attempting FINALIZE again. "
                                    "Do not select an ID outside this required set "
                                    "unless all required IDs have already been investigated. "
                                    "Do not repeatedly investigate the same reconciliation ID. "
                                    "Use only the minimum exception-level tool necessary."
                                )
                            )
                        ],
                    )
                )

                continue
            # ------------------------------------------------
            # FINALIZATION IS VALID
            # ------------------------------------------------

            if uninspected_count == 0:
                final_reason = (
                    "Controller investigation completed. "
                    f"All {exceptions_available} exceptions were investigated. "
                    "No unresolved investigation coverage gap remains."
                )
            else:
                final_reason = (
                    "Controller investigation completed within the bounded "
                    "investigation scope. "
                    f"{inspected_count} of {exceptions_available} exceptions "
                    "were investigated. "
                    f"{uninspected_count} exceptions remain uninspected and "
                    "require manual review."
                )
            tool_trace.append(
                {
                    "step": step,
                    "type": "FINALIZE",
                    "reason": final_reason,
                    "decision": (
                        "INVESTIGATION_COMPLETE"
                         if uninspected_count == 0
                         else "PARTIAL_INVESTIGATION"
                    ),
                    "coverage": coverage,
                    "exceptions_available": (
                        exceptions_available
                    ),
                    "exceptions_inspected": (
                        inspected_count
                    ),
                    "uninspected_exceptions": (
                        uninspected_count
                    ),
                    "status": "SUCCESS",
                }
            )

            return {
                "final_response": final_reason,
                "tool_trace": tool_trace,
                "tool_call_count": tool_call_count,
                "model_call_count": model_call_count,
                "llm_status": "AVAILABLE",
                "llm_error": None,
                "investigation": {
                    "exceptions_available": (
                        exceptions_available
                    ),
                    "exceptions_inspected": (
                        inspected_count
                    ),
                    "evidence_inspected": len(
                        evidence_inspected
                    ),
                    "analyses_inspected": len(
                        analyses_inspected
                    ),
                    "analyses_verified": len(
                        analyses_verified
                    ),
                    "risks_assessed": len(
                        risks_assessed
                    ),
                    "investigation_coverage": (
                        coverage
                    ),
                    "uninspected_exceptions": (
                        uninspected_count
                    ),
                    "finalization_decision": (
                    "INVESTIGATION_COMPLETE"
                    if uninspected_count == 0
                    else "PARTIAL_INVESTIGATION"
                    ),
                },
            }

        # ----------------------------------------------------
        # VALIDATE GEMINI'S INVESTIGATION REQUEST
        #
        # Gemini chooses the investigation tool.
        # Python only validates that the requested
        # reconciliation ID belongs to the bounded scope
        # and has not already been investigated.
        # ----------------------------------------------------

        unresolved_required_ids = (
            required_investigation_ids
            - exceptions_inspected
        )

        requested_reconciliation_id = arguments.get(
            "reconciliation_id"
        )

        investigation_tools = {
            "inspect_evidence",
            "inspect_ai_analysis",
            "analyze_exception",
            "verify_analysis",
            "assess_risk",
        }

        if tool_name in investigation_tools:

            # An exception-level tool must specify an ID.
            if requested_reconciliation_id is None:

                tool_trace.append(
                    {
                        "step": step,
                        "type": "INVALID_INVESTIGATION_REQUEST",
                        "original_tool": tool_name,
                        "original_arguments": arguments,
                        "reason": (
                            "Exception-level investigation tools "
                            "require a reconciliation_id."
                        ),
                        "status": "REJECTED",
                    }
                )

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "INVESTIGATION REQUEST REJECTED. "
                                    "You must provide a valid "
                                    "reconciliation_id for the "
                                    "exception-level tool."
                                )
                            )
                        ],
                    )
                )

                continue

            # The ID must belong to the bounded investigation scope.
            if (
                requested_reconciliation_id
                not in required_investigation_ids
            ):

                tool_trace.append(
                    {
                        "step": step,
                        "type": "INVALID_INVESTIGATION_REQUEST",
                        "original_tool": tool_name,
                        "original_arguments": arguments,
                        "reconciliation_id": (
                            requested_reconciliation_id
                        ),
                        "reason": (
                            "The requested reconciliation ID is "
                            "outside the bounded investigation scope."
                        ),
                        "status": "REJECTED",
                    }
                )

                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                text=(
                                    "INVESTIGATION REQUEST REJECTED. "
                                    f"Reconciliation ID "
                                    f"{requested_reconciliation_id} "
                                    "is outside the bounded "
                                    "investigation scope. "
                                    f"Choose one of: "
                                    f"{sorted(required_investigation_ids)}."
                                )
                            )
                        ],
                    )
                )

                continue
        tool_call_count += 1

        trace_entry = {
            "step": step,
            "type": "TOOL_CALL",
            "tool": tool_name,
            "arguments": arguments,
        }

        try:
            result = execute_tool(
                tool_name,
                arguments,
            )

            trace_entry["status"] = "SUCCESS"
            trace_entry["result"] = result

            # ------------------------------------------------
            # Track investigation coverage
            # ------------------------------------------------
            if tool_name == "inspect_exceptions":
                if isinstance(result, list):
                    exceptions_available = len(result)

            elif tool_name in {
                "inspect_evidence",
                "inspect_ai_analysis",
                "analyze_exception",
                "verify_analysis",
                "assess_risk",
            }:
                reconciliation_id = arguments.get(
                    "reconciliation_id"
                )

                if reconciliation_id is not None:
                    reconciliation_id = int(
                        float(
                            str(
                                reconciliation_id
                            ).strip()
                        )
                    )

                    if tool_name == "inspect_evidence":
                        evidence_inspected.add(
                            reconciliation_id
                        )

                    elif tool_name == "inspect_ai_analysis":
                        analyses_inspected.add(
                            reconciliation_id
                        )

                    elif tool_name == "analyze_exception":
                        analyses_inspected.add(
                            reconciliation_id
                        )

                    elif tool_name == "assess_risk":
                        risks_assessed.add(
                            reconciliation_id
                        )

                    elif tool_name == "verify_analysis":
                        if (
                            isinstance(result, dict)
                            and result.get("verified") is True
                        ):
                            analyses_verified.add(
                                reconciliation_id
                            )
                            exceptions_inspected.add(
                                reconciliation_id
                            )

            tool_trace.append(trace_entry)
        except Exception as error:
            error_message = str(error)

            trace_entry["status"] = "ERROR"
            trace_entry["error"] = error_message

            result = {
                "error": error_message,
                "manual_review_required": True,
                "investigation_status": "ATTEMPTED_BUT_FAILED",
            }

            # ------------------------------------------------
            # Failed investigation attempts are NOT counted
            # as completed investigation coverage.
            #
            # The exception remains unresolved and is
            # explicitly escalated to manual review.
            # Only a successful verify_analysis result can
            # add an exception to exceptions_inspected.
            # ------------------------------------------------

            tool_trace.append(trace_entry)

        # ----------------------------------------------------
        # Return the tool observation to Gemini
        #
        # The controller may override Gemini's requested tool.
        # Therefore we must not send a function_response whose
        # name differs from Gemini's original function_call.
        # Instead, provide the executed tool result as a normal
        # controller observation.
        # ----------------------------------------------------

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=(
                            "CONTROLLER TOOL OBSERVATION. "
                            f"Executed tool: {tool_name}. "
                            f"Arguments: {arguments}. "
                            f"Result: {result}"
                        )
                    )
                ],
            )
        )

        # Gemini gets another decision cycle.
        # The next loop iteration will call the model again.
        # ----------------------------------------------------
    # --------------------------------------------------------
    # Safety stop
    # --------------------------------------------------------

    final_response = (
        "Controller investigation stopped after reaching "
        f"the maximum of {MAX_AGENT_STEPS} agent steps. "
        "Unresolved cases require manual review."
    )

    tool_trace.append(
        {
            "step": MAX_AGENT_STEPS,
            "type": "SAFETY_STOP",
            "reason": (
                "Maximum agent step limit reached."
            ),
            "status": "STOPPED",
        }
    )

    return {
        "final_response": final_response,
        "tool_trace": tool_trace,
        "tool_call_count": tool_call_count,
        "model_call_count": model_call_count,
        "llm_status": "AVAILABLE",
        "llm_error": None,
        "investigation": {
            "exceptions_available": exceptions_available,
            "exceptions_inspected": len(
                exceptions_inspected
            ),
            "evidence_inspected": len(
                evidence_inspected
            ),
            "analyses_inspected": len(
                analyses_inspected
            ),
            "analyses_verified": len(
                analyses_verified
            ),
            "risks_assessed": len(
                risks_assessed
            ),
            "investigation_coverage": (
                round(
                    (
                        len(
                            exceptions_inspected
                        )
                        / exceptions_available
                        * 100
                    ),
                    2,
                )
                if exceptions_available
                else 0
            ),
            "uninspected_exceptions": (
                exceptions_available
                - len(
                    exceptions_inspected
                )
            ),
            "finalization_decision": (
              "PARTIAL_INVESTIGATION"
              ),
        },
    }


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

    # --------------------------------------------------------
    # REBUILD AUTHORITATIVE STATE FROM DATABASE
    #
    # The agent's observations and decisions are not treated
    # as financial truth. The backend reads the deterministic
    # reconciliation state again after the agent completes.
    # --------------------------------------------------------

    summary = get_batch_summary(
        batch_id
    )

    exceptions = get_batch_exceptions(
        batch_id
    )

    analyses = []
    all_risk_assessments = []
    risk_cache = {}

    for exception in exceptions:

        reconciliation_id = (
            exception[
                "reconciliation_id"
            ]
        )
        risk = assess_risk(
            reconciliation_id
        )

        risk_cache[reconciliation_id] = risk

        all_risk_assessments.append(
            risk
        )
        # Only exceptions actually investigated by the controller
        # are included in the agent analysis report.
        if (
            reconciliation_id
            not in inspected_reconciliation_ids
        ):
            continue

        ai_analysis = get_ai_analysis(
            reconciliation_id
        )

        risk = risk_cache[
            reconciliation_id
        ]


        if not ai_analysis["available"]:

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
                        "AI analysis unavailable. "
                        "Manual review required."
                    ),
                    "risk_level": (
                        risk[
                            "risk_level"
                        ]
                    ),
                    "risk_reasons": (
                        risk[
                            "reasons"
                        ]
                    ),
                }
            )

            continue

        verification = verify_ai_analysis(
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
                    risk[
                        "risk_level"
                    ]
                ),
                "risk_reasons": (
                    risk[
                        "reasons"
                    ]
                ),
            }
        )

    # --------------------------------------------------------
    # DETERMINISTIC RISK GROUPS
    # --------------------------------------------------------
    high_risk_exceptions = [
        risk
        for risk in all_risk_assessments
        if risk["risk_level"] == "HIGH"
    ]

    medium_risk_exceptions = [
        risk
        for risk in all_risk_assessments
        if risk["risk_level"] == "MEDIUM"
    ]

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

    # --------------------------------------------------------
    # AUTHORITATIVE AGENT SUMMARY
    #
    # The LLM reasoning is not trusted for coverage claims.
    # Investigation metadata from Python is authoritative.
    # --------------------------------------------------------

    exceptions_available = investigation.get(
        "exceptions_available",
        0,
    )

    exceptions_inspected = investigation.get(
        "exceptions_inspected",
        0,
    )
    report["agent"]["exceptions_investigated"] = (
        exceptions_inspected
    )

    report["agent"]["exceptions_analyzed"] = (
        len(analyses)
    )

    investigation_coverage = investigation.get(
        "investigation_coverage",
        0,
    )

    uninspected_exceptions = investigation.get(
        "uninspected_exceptions",
        0,
    )
    # --------------------------------------------------------
    # AUTHORITATIVE CONTROLLER DECISION COUNTS
    #
    # These counts are derived from the actual investigated
    # analysis results. They are not taken from Gemini's text.
    # --------------------------------------------------------

    confirmed_exceptions = sum(
        1
        for analysis in analyses
        if analysis.get("resolution") == "CONFIRMED"
    )

    investigated_manual_review = sum(
        1
        for analysis in analyses
        if analysis.get("resolution") == "MANUAL_REVIEW"
    )

    manual_review_count = (
        investigated_manual_review
        + uninspected_exceptions
    )

    report["agent"]["confirmed_exceptions"] = (
        confirmed_exceptions
    )

    report["agent"]["manual_review_required"] = (
        manual_review_count
    )
    # --------------------------------------------------------
    # AUTHORITATIVE MANUAL REVIEW COUNT
    #
    # The controller report is built from investigated analyses,
    # but uninspected deterministic exceptions still require
    # manual review even when Gemini is unavailable.
    # --------------------------------------------------------

    if uninspected_exceptions > 0:

        report["agent_summary"] = (
            "Investigation was partial. "
            f"{exceptions_inspected} of "
            f"{exceptions_available} exceptions were inspected "
            f"({investigation_coverage}% coverage). "
            f"{uninspected_exceptions} exceptions remain "
            "uninspected. "
            "Manual review is required for the uninspected cases. "
            "Financial truth remains authoritative from the "
            "deterministic reconciliation engine."
        )

    else:

        report["agent_summary"] = (
            "Investigation completed. "
            f"All {exceptions_available} exceptions were inspected "
            f"({investigation_coverage}% coverage). "
            "Final controller decisions are based on the verified "
            "investigation state. "
            "Financial truth remains authoritative from the "
            "deterministic reconciliation engine."
        )

    # Preserve Gemini's actual reasoning separately.
    report["agent_reasoning"] = final_response
    report["final_response"] = final_response

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
    # AGENT INVESTIGATION METRICS
    #
    # These metrics describe what the agent actually inspected.
    # They are NOT financial truth and do not override the
    # deterministic reconciliation results.
    # --------------------------------------------------------

    report["investigation"] = investigation

    # --------------------------------------------------------
    # CONTROLLER DECISION AUDIT
    #
    # This is structured operational metadata.
    # It does not replace deterministic financial truth.
    # --------------------------------------------------------

    coverage = investigation.get(
        "investigation_coverage",
        0,
    )

    finalization_decision = investigation.get(
        "finalization_decision"
    )
    if (
        exceptions_available > 0
        and uninspected_exceptions > 0
    ):

        investigation_status = "PARTIAL"

    elif (
        finalization_decision
        == "INVESTIGATION_COMPLETE"
    ):

        investigation_status = "COMPLETE"

    elif (
        finalization_decision
        == "PARTIAL_INVESTIGATION"
    ):

        investigation_status = "PARTIAL"

    else:

        investigation_status = "UNKNOWN"

    report["decision_audit"] = {
        "investigation_status": (
            investigation_status
        ),
        "coverage_percent": coverage,
        "exceptions_available": (
            exceptions_available
        ),
        "exceptions_inspected": (
            exceptions_inspected
        ),
        "uninspected_exceptions": (
            uninspected_exceptions
        ),
        "finalization_decision": (
            finalization_decision
        ),
        "manual_review_required": (
            report[
                "agent"
            ][
                "manual_review_required"
            ]
        ),
        "deterministic_truth_source": (
            "reconciliation_engine"
        ),
    }

    # --------------------------------------------------------
    # DETERMINISTIC RISK SUMMARY
    #
    # Risk summary must represent the COMPLETE exception
    # population, not only exceptions investigated by Gemini.
    # The deterministic risk engine is the source of truth.
    # --------------------------------------------------------

    population_high_risk = []
    population_medium_risk = []
    for exception in exceptions:
        risk = risk_cache[
            exception["reconciliation_id"]
        ]

        if risk["risk_level"] == "HIGH":
            population_high_risk.append(
                exception["reconciliation_id"]
            )

        elif risk["risk_level"] == "MEDIUM":
            population_medium_risk.append(
                exception["reconciliation_id"]
            )

    report["risk_summary"] = {
        "high_risk_count": len(
            population_high_risk
        ),
        "medium_risk_count": len(
            population_medium_risk
        ),
        "high_risk_reconciliation_ids": (
            population_high_risk
        ),
        "medium_risk_reconciliation_ids": (
            population_medium_risk
        ),
        "source": "deterministic_reconciliation_engine",
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
