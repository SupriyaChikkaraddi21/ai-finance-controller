import json

from google.genai import types

from core.models import AIAnalysis

from .loop_state import InvestigationState
from .prompts import (
    CONTROLLER_SYSTEM_PROMPT,
    CONTROLLER_TASK_PROMPT,
)
from .tools import (
    get_batch_exceptions,
    get_ai_analysis,
    verify_ai_analysis,
    assess_exception_risk,
    inspect_investigation_scope as get_investigation_scope,
)
from .decisions import get_required_investigation_ids
from .tool_registry import (
    TOOLS,
    execute_tool,
)

MODEL_NAME = "gemini-3.5-flash-lite"
MAX_AGENT_STEPS = 40
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
    batch_exceptions = get_batch_exceptions(
        batch_id
    )

    exceptions_available = len(
        batch_exceptions
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

    state = InvestigationState(
        exceptions_available=exceptions_available,
    )
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

            state.risk_cache[reconciliation_id] = risk

            state.analyses_inspected.add(
                reconciliation_id
            )

            state.risks_assessed.add(
                reconciliation_id
            )

            if verification.get("verified") is True:
                state.analyses_verified.add(
                    reconciliation_id
                )

                # A persisted analysis counts as investigated
                # only after successful deterministic verification.
                state.exceptions_inspected.add(
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
        <= state.exceptions_inspected
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
                    state.exceptions_inspected
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
                    state.exceptions_inspected
                ),
                "inspected_reconciliation_ids": sorted(
                    state.exceptions_inspected
                ),
                "evidence_inspected": len(
                    state.evidence_inspected
                ),
                "analyses_inspected": len(
                    state.analyses_inspected
                ),
                "analyses_verified": len(
                    state.analyses_verified
                ),
                "risks_assessed": len(
                    state.risks_assessed
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
                f"{len(state.exceptions_inspected)} of "
                f"{exceptions_available} exceptions were inspected. "
                f"{state.uninspected_exceptions()} "
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
                        state.exceptions_inspected
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
                        state.exceptions_inspected
                    ),
                    "evidence_inspected": len(
                        state.evidence_inspected
                    ),
                    "analyses_inspected": len(
                        state.analyses_inspected
                    ),
                    "analyses_verified": len(
                        state.analyses_verified
                    ),
                    "risks_assessed": len(
                        state.risks_assessed
                    ),
                    "investigation_coverage": (
                        state.investigation_coverage()
                    ),
                    "uninspected_exceptions": (
                        state.uninspected_exceptions()
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
                    f"{len(state.exceptions_inspected)} of "
                    f"{exceptions_available} exceptions were inspected "
                    f"before the quota limit was reached. "
                    f"{state.uninspected_exceptions()} "
                    "exceptions remain unresolved and require "
                    "further automated investigation or manual review."
                )
            else:
                final_response = (
                    "Investigation could not continue because Gemini "
                    "reasoning was unavailable. "
                    f"{len(state.exceptions_inspected)} of "
                    f"{exceptions_available} exceptions were inspected. "
                    f"{state.uninspected_exceptions()} "
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
                    "exceptions_inspected": len(
                        state.exceptions_inspected
                    ),
                    "evidence_inspected": len(
                        state.evidence_inspected
                    ),
                    "analyses_inspected": len(
                        state.analyses_inspected
                    ),
                    "analyses_verified": len(
                        state.analyses_verified
                    ),
                    "risks_assessed": len(
                        state.risks_assessed
                    ),
                    "investigation_coverage": (
                        state.investigation_coverage()
                    ),
                    "uninspected_exceptions": (
                        state.uninspected_exceptions()
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
                state.exceptions_inspected,
            )

            unresolved_required_ids = (
                required_investigation_ids
                - state.exceptions_inspected
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
                        state.exceptions_inspected
                    ),
                    "evidence_inspected": len(
                        state.evidence_inspected
                    ),
                    "analyses_inspected": len(
                        state.analyses_inspected
                    ),
                    "analyses_verified": len(
                        state.analyses_verified
                    ),
                    "risks_assessed": len(
                        state.risks_assessed
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
                state.exceptions_inspected,
            )

            unresolved_required_ids = (
                required_investigation_ids
                - state.exceptions_inspected
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
                        state.evidence_inspected
                    ),
                    "analyses_inspected": len(
                        state.analyses_inspected
                    ),
                    "analyses_verified": len(
                        state.analyses_verified
                    ),
                    "risks_assessed": len(
                        state.risks_assessed
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
            - state.exceptions_inspected
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
        # ----------------------------------------------------
        # ENFORCE COMPLETION OF EVIDENCE-COMPLETE CASES
        #
        # If deterministic evidence has already established
        # the exception type, require risk assessment before
        # moving on to another investigation case.
        #
        # This is a state-dependent controller gate, not a
        # fixed investigation sequence.
        # ----------------------------------------------------

        if (
            tool_name in investigation_tools
            and requested_reconciliation_id is not None
            and state.evidence_complete
        ):
            pending_risk_ids = (
                state.evidence_complete
                - state.risks_assessed
            )

            if (
                pending_risk_ids
                and requested_reconciliation_id
                not in pending_risk_ids
                and tool_name != "assess_risk"
            ):
                required_risk_id = sorted(
                    pending_risk_ids
                )[0]

                tool_trace.append(
                    {
                        "step": step,
                        "type": "ADAPTIVE_TOOL_REQUEST_REJECTED",
                        "original_tool": tool_name,
                        "original_arguments": arguments,
                        "reconciliation_id": (
                            requested_reconciliation_id
                        ),
                        "required_reconciliation_id": (
                            required_risk_id
                        ),
                        "reason": (
                            "A previously inspected exception "
                            "has deterministic evidence sufficient "
                            "to establish its exception type, but "
                            "its risk has not yet been assessed. "
                            "Complete the pending risk assessment "
                            "before moving to another exception."
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
                                    "ADAPTIVE INVESTIGATION REQUEST "
                                    "REJECTED. "
                                    f"Reconciliation ID "
                                    f"{required_risk_id} has "
                                    "deterministic evidence sufficient "
                                    "to establish its exception type, "
                                    "but risk has not been assessed. "
                                    "Call assess_risk for that "
                                    "reconciliation ID before "
                                    "investigating another exception."
                                )
                            )
                        ],
                    )
                )

                continue
        # ----------------------------------------------------
        # PREVENT REDUNDANT INVESTIGATION ACTIONS
        #
        # Different tools may be used for the same exception,
        # but the exact same successful investigation action
        # should not be repeated.
        # ----------------------------------------------------

        if tool_name in {
            "inspect_evidence",
            "inspect_ai_analysis",
            "analyze_exception",
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

                duplicate_action = (
                    (
                        tool_name == "inspect_evidence"
                        and reconciliation_id
                        in state.evidence_calls
                    )
                    or (
                        tool_name in {
                            "inspect_ai_analysis",
                            "analyze_exception",
                        }
                        and reconciliation_id
                        in state.analysis_calls
                    )
                    or (
                        tool_name == "assess_risk"
                        and reconciliation_id
                        in state.risk_calls
                    )
                )

                if duplicate_action:
                    tool_trace.append(
                        {
                            "step": step,
                            "type": "REDUNDANT_TOOL_CALL_REJECTED",
                            "tool": tool_name,
                            "reconciliation_id": (
                                reconciliation_id
                            ),
                            "reason": (
                                "The same investigation action "
                                "was already completed for this "
                                "reconciliation ID. Choose a "
                                "different useful investigation "
                                "action or move to another "
                                "uninspected exception."
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
                                        "REDUNDANT TOOL CALL REJECTED. "
                                        f"{tool_name} was already completed "
                                        f"for reconciliation ID "
                                        f"{reconciliation_id}. "
                                        "Do not repeat the same tool for "
                                        "the same exception. "
                                        "Choose another useful tool, or "
                                        "move to another previously "
                                        "uninspected exception."
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
                        state.evidence_inspected.add(
                            reconciliation_id
                        )
                        state.evidence_calls.add(
                            reconciliation_id
                        )

                        # Deterministic evidence can complete investigation
                        # for exception types whose nature is already established
                        # without requiring AI interpretation.
                        if isinstance(result, dict):
                            deterministic_exception = result.get(
                                "deterministic_exception"
                            )
                        if deterministic_exception:
                            state.investigated_exception_types[
                                reconciliation_id
                            ] = deterministic_exception

                            evidence_complete_types = {
                                "DUPLICATE",
                                "MISSING_PAYMENT",
                                "MISSING_SETTLEMENT",
                                "STATUS_MISMATCH",
                            }

                            if (
                                deterministic_exception
                                in evidence_complete_types
                            ):
                                state.evidence_complete.add(
                                    reconciliation_id
                                )
                                state.exceptions_inspected.add(
                                    reconciliation_id
                                )
                    elif tool_name == "inspect_ai_analysis":
                        state.analyses_inspected.add(
                            reconciliation_id
                        )
                        state.analysis_calls.add(
                            reconciliation_id
                        )
                    elif tool_name == "inspect_ai_analysis":
                        state.analyses_inspected.add(
                            reconciliation_id
                        )
                        state.analysis_calls.add(
                            reconciliation_id
                        )

                    elif tool_name == "analyze_exception":
                        state.analyses_inspected.add(
                            reconciliation_id
                        )
                        state.analysis_calls.add(
                            reconciliation_id
                        )

                    elif tool_name == "assess_risk":
                        state.risks_assessed.add(
                            reconciliation_id
                        )
                        state.risk_calls.add(
                            reconciliation_id
                        )

                    elif tool_name == "verify_analysis":
                        if (
                            isinstance(result, dict)
                            and result.get("verified") is True
                        ):
                            state.analyses_verified.add(
                                reconciliation_id
                            )
                            state.exceptions_inspected.add(
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
        # ----------------------------------------------------
        # Build adaptive controller observation
        # ----------------------------------------------------
        observation_text = (
            "CONTROLLER TOOL OBSERVATION. "
            f"Executed tool: {tool_name}. "
            f"Arguments: {arguments}. "
            f"Result: {result}"
        )

        if (
            tool_name == "inspect_evidence"
            and isinstance(result, dict)
            and reconciliation_id is not None
        ):
            deterministic_exception = result.get(
                "deterministic_exception"
            )

            evidence_complete_types = {
                "DUPLICATE",
                "MISSING_PAYMENT",
                "MISSING_SETTLEMENT",
                "STATUS_MISMATCH",
            }

            if deterministic_exception in evidence_complete_types:
                observation_text += (
                    " CASE INVESTIGATION STATUS: "
                    "DETERMINISTIC EVIDENCE IS SUFFICIENT "
                    "TO ESTABLISH THE EXCEPTION TYPE. "
                    "Do not repeat inspect_evidence for this "
                    "reconciliation ID. "
                    "Assess risk if useful, then move to the "
                    "next unresolved exception."
                )
            else:
                observation_text += (
                    " CASE INVESTIGATION STATUS: "
                    "DETERMINISTIC EVIDENCE DOES NOT BY ITSELF "
                    "ESTABLISH THE ROOT CAUSE. "
                    "If interpretation is needed, use "
                    "analyze_exception and verify the AI result "
                    "before treating the case as confirmed."
                )

        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=observation_text
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
                state.exceptions_inspected
            ),
            "evidence_inspected": len(
                state.evidence_inspected
            ),
            "analyses_inspected": len(
                state.analyses_inspected
            ),
            "analyses_verified": len(
                state.analyses_verified
            ),
            "risks_assessed": len(
                state.risks_assessed
            ),
            "investigation_coverage": (
                round(
                    (
                        len(
                            state.exceptions_inspected
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
                    state.exceptions_inspected
                )
            ),
            "finalization_decision": (
              "PARTIAL_INVESTIGATION"
              ),
        },
    }


# ============================================================
