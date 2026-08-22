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

from .prompts import (
    CONTROLLER_SYSTEM_PROMPT,
    CONTROLLER_TASK_PROMPT,
)


load_dotenv()


MODEL_NAME = "gemini-3.6-flash"
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
def run_controller_agent(
    batch_id
):
    """
    Run the Finance Controller Agent.

    Gemini controls the investigation workflow through
    deterministic backend tools.

    The deterministic reconciliation engine remains the
    source of financial truth.
    """

    batch = Batch.objects.get(
        id=batch_id
    )

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

    client = get_client()

    # --------------------------------------------------------
    # INITIAL CONTEXT
    #
    # We give the agent only the batch identifier.
    # The agent must use tools to inspect the evidence.
    # --------------------------------------------------------

    initial_prompt = (
        CONTROLLER_SYSTEM_PROMPT
        + "\n\n"
        + CONTROLLER_TASK_PROMPT.format(
            batch_id=batch_id
        )
        + "\n\n"
        "You are operating as an autonomous Finance "
        "Controller Agent.\n\n"
        f"Batch ID: {batch_id}\n\n"
        "You must investigate this batch using the "
        "available tools.\n\n"
        "Required workflow:\n"
        "1. Inspect the batch.\n"
        "2. Inspect the deterministic exceptions.\n"
        "3. Assess risk for exceptions that require "
        "investigation.\n"
        "4. Inspect transaction evidence when needed.\n"
        "5. Inspect existing AI analysis when available.\n"
        "6. Verify AI analysis against deterministic evidence.\n"
        "7. Decide whether each investigated exception is "
        "CONFIRMED or requires MANUAL_REVIEW.\n"
        "8. Never change deterministic financial results.\n"
        "9. Produce a concise controller report.\n\n"
        "Use tools instead of assuming financial facts."
    )

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(
                    text=initial_prompt
                )
            ],
        )
    ]

    tool_trace = []
    tool_call_count = 0
    model_call_count = 0

    max_model_calls = 5
    max_tool_calls = 30

    final_response = None

    # --------------------------------------------------------
    # AGENT LOOP
    # --------------------------------------------------------

    while (
        model_call_count < max_model_calls
        and tool_call_count < max_tool_calls
    ):

        model_call_count += 1

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                temperature=0.1,
                tools=TOOLS,
            ),
        )

        if not response.candidates:
            break

        candidate = response.candidates[0]
        content = candidate.content

        if not content:
            break

        function_calls = []

        for part in content.parts:

            if getattr(
                part,
                "function_call",
                None
            ):
                function_calls.append(
                    part.function_call
                )

        # ----------------------------------------------------
        # NO TOOL CALL
        #
        # Agent has finished reasoning and produced
        # its controller report.
        # ----------------------------------------------------

        if not function_calls:

            final_response = (
                response.text
                if response.text
                else "Controller completed."
            )

            break

        # ----------------------------------------------------
        # PRESERVE MODEL TOOL-CALL MESSAGE
        # ----------------------------------------------------

        contents.append(
            content
        )

        # ----------------------------------------------------
        # EXECUTE TOOLS
        # ----------------------------------------------------

        for function_call in function_calls:

            if tool_call_count >= max_tool_calls:
                break

            tool_call_count += 1

            name = function_call.name

            arguments = (
                dict(
                    function_call.args
                )
                if function_call.args
                else {}
            )

            tool_trace.append(
                {
                    "tool": name,
                    "arguments": arguments,
                }
            )

            try:

                result = execute_tool(
                    name,
                    arguments,
                )

            except Exception as error:

                result = {
                    "error": str(error)
                }

            # ------------------------------------------------
            # Gemini expects function responses as USER
            # content with function_response parts.
            # ------------------------------------------------

            response_part = types.Part(
                function_response=(
                    types.FunctionResponse(
                        name=name,
                        response={
                            "result": result
                        },
                    )
                )
            )

            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        response_part
                    ],
                )
            )

    # --------------------------------------------------------
    # FALLBACK IF AGENT HIT LIMIT
    # --------------------------------------------------------

    if final_response is None:

        final_response = (
            "Finance Controller Agent stopped after "
            "reaching its investigation limit. "
            "Manual review is required for unresolved "
            "exceptions."
        )

    # --------------------------------------------------------
    # BUILD REPORT FROM DETERMINISTIC DATA
    #
    # This does NOT ask Gemini to invent financial truth.
    # The report is based on existing verified backend data.
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

        ai_analysis = get_ai_analysis(
            reconciliation_id
        )

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
                        "AI analysis is not available."
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
            }
        )

    report = build_controller_report(
        batch_id,
        analyses,
    )

    report["agent_summary"] = (
        final_response
    )

    report["agent_version"] = "v2"

    report["model"] = MODEL_NAME

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
        "TOOL_USING_CONTROLLER"
    )

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

    return report