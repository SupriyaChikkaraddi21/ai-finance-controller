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

    The agent uses Gemini for planning/reasoning,
    while all financial evidence comes from deterministic
    backend tools.
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
            "agent_version": AGENT_VERSION,
            "model": MODEL_NAME,
        },
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # Get deterministic data first.
    # --------------------------------------------------------

    summary = get_batch_summary(
        batch_id
    )

    exceptions = get_batch_exceptions(
        batch_id
    )

    # --------------------------------------------------------
    # Existing AI analyses are reused.
    # This prevents unnecessary Gemini API usage.
    # --------------------------------------------------------

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
                    "classification": None,
                    "confidence": None,
                    "resolution": (
                        "MANUAL_REVIEW"
                    ),
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

    # --------------------------------------------------------
    # Gemini gets the verified controller state.
    #
    # It is used for reasoning/report generation,
    # NOT for financial truth.
    # --------------------------------------------------------

    client = get_client()

    controller_state = {
        "batch": summary,
        "exceptions": exceptions,
        "verified_analyses": analyses,
    }

    prompt = (
        CONTROLLER_SYSTEM_PROMPT
        + "\n\n"
        + CONTROLLER_TASK_PROMPT.format(
            batch_id=batch_id
        )
        + "\n\nCURRENT VERIFIED STATE:\n"
        + json.dumps(
            controller_state,
            indent=2,
        )
    )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
        ),
    )

    agent_summary = (
        response.text
        if response.text
        else "Controller completed."
    )

    report = build_controller_report(
        batch_id,
        analyses,
    )

    report["agent_summary"] = (
        agent_summary
    )

    report["agent_version"] = (
        AGENT_VERSION
    )

    report["model"] = MODEL_NAME

    AuditLog.objects.create(
        batch=batch,
        action="MANUAL_REVIEW",
        message=(
            "Finance Controller Agent completed."
        ),
        metadata={
            "agent_version": AGENT_VERSION,
            "model": MODEL_NAME,
            "exceptions_analyzed": (
                len(analyses)
            ),
            "manual_review_required": sum(
                1
                for item in analyses
                if item["resolution"]
                == "MANUAL_REVIEW"
            ),
        },
    )

    return report
