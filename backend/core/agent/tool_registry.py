from google.genai import types

from .tools import (
    get_batch_summary,
    get_batch_exceptions,
    get_transaction_evidence,
    get_ai_analysis,
    verify_ai_analysis,
    assess_exception_risk,
    inspect_investigation_scope as get_investigation_scope,
)
from .tools import analyze_exception_for_controller

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
        return get_batch_summary(
            arguments["batch_id"]
        )

    if name == "inspect_exceptions":
        return get_batch_exceptions(
            arguments["batch_id"]
        )

    if name == "inspect_investigation_scope":
        return get_investigation_scope(
            arguments["batch_id"]
        )

    if name == "inspect_evidence":
        return get_transaction_evidence(
            arguments["reconciliation_id"]
        )

    if name == "inspect_ai_analysis":
        return get_ai_analysis(
            arguments["reconciliation_id"]
        )

    if name == "analyze_exception":
        return analyze_exception_for_controller(
            arguments["reconciliation_id"]
        )

    if name == "verify_analysis":
        return verify_ai_analysis(
            arguments["reconciliation_id"]
        )

    if name == "assess_risk":
        return assess_exception_risk(
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
