import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .models import (
    AIAnalysis,
    ReconciliationResult,
)

load_dotenv()


MODEL_NAME = "gemini-3.6-flash"
PROMPT_VERSION = "v2"


def get_gemini_client():
    """
    Create Gemini client using the API key
    stored in the environment.
    """

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(
        api_key=api_key
    )


def build_exception_evidence(
    reconciliation,
):
    """
    Build a controlled evidence object.

    IMPORTANT:
    Gemini receives only financial evidence
    already produced by our system.
    """

    transaction = (
        reconciliation.transaction
    )

    return {
        "transaction_id": (
            transaction.transaction_id
        ),

        "order_id": (
            transaction.order_id
        ),

        "payment_amount": (
            str(transaction.payment_amount)
            if transaction.payment_amount is not None
            else None
        ),

        "fee": str(transaction.fee),

        "refund": str(transaction.refund),

        "adjustment": str(
            transaction.adjustment
        ),

        "expected_settlement": (
            str(
                transaction.expected_settlement
            )
            if transaction.expected_settlement
            is not None
            else None
        ),

        "actual_settlement": (
            str(
                transaction.actual_settlement
            )
            if transaction.actual_settlement
            is not None
            else None
        ),

        "payment_status": (
            transaction.payment_status
        ),

        "settlement_status": (
            transaction.settlement_status
        ),

        "deterministic_result": (
            reconciliation.result
        ),

        "deterministic_exception": (
            reconciliation.exception_type
        ),

        "difference": (
            str(reconciliation.difference)
            if reconciliation.difference is not None
            else None
        ),

        "requires_manual_review": (
            reconciliation.requires_manual_review
        ),

        "rule_version": (
            reconciliation.rule_version
        ),
    }

def build_prompt(evidence):
    """
    Strict prompt for finance exception analysis.
    """

    evidence_json = json.dumps(
        evidence,
        indent=2,
    )

    return f"""
You are an AI assistant for a financial
reconciliation control system.

Your job is ONLY to analyze an exception that
has already been detected by a deterministic
reconciliation engine.

The deterministic reconciliation result and
financial amounts are the source of truth.

You are an explanation and classification layer.
You are NOT the reconciliation engine.

You MUST NOT:
- change the deterministic result
- invent transactions
- invent missing records
- change financial amounts
- recalculate or override the deterministic result
- claim that an exception is resolved
- invent a fee, refund, adjustment, tax, processor charge,
  or other cause that is not present in the evidence
- infer a specific root cause merely because a numerical
  difference exists

IMPORTANT UNKNOWN RULE:

A numerical difference by itself does NOT prove
the cause of an exception.

If the evidence shows that actual settlement differs
from expected settlement, but the evidence does NOT
identify a specific reason for that difference,
you MUST classify the exception as:

"UNKNOWN"

Do NOT classify such a case as
"AMOUNT_DISCREPANCY" merely because a difference exists.

Use "AMOUNT_DISCREPANCY" only when the evidence
supports a genuine identifiable amount-related
discrepancy.

Examples:

Example 1:
Expected settlement = 1000
Actual settlement = 980
No refund
No adjustment
No additional fee
No other evidence explaining the 20 difference

Classification:
"UNKNOWN"

Reason:
The system knows that 20 is missing, but the evidence
does not establish WHY it is missing.

Example 2:
Expected settlement = 1000
Actual settlement = 980
Evidence explicitly states an additional settlement
fee of 20

Classification:
"PROCESSING_FEE"

Reason:
The evidence identifies the cause.

Example 3:
Payment = 1000
Refund = 200
Expected settlement = 780
Actual settlement = 780

Classification:
"REFUND"

Reason:
The refund is explicitly present in the evidence.

Example 4:
Payment status = SUCCESS
Settlement status = FAILED

Classification:
"STATUS_ISSUE"

Reason:
The evidence explicitly shows the status conflict.

Example 5:
Payment amount is missing and payment status is MISSING

Classification:
"MISSING_RECORD"

Reason:
The evidence explicitly indicates missing payment evidence.

Example 6:
The order ID is identified as a duplicate by the
deterministic reconciliation system.

Classification:
"DUPLICATE"

Reason:
The deterministic evidence explicitly identifies duplication.

CONFIDENCE RULES:

- Confidence must be between 0 and 1.
- Use high confidence only when the evidence clearly
  supports the classification.
- Use low confidence when the root cause is uncertain.
- UNKNOWN cases should generally have low confidence.
- Never increase confidence merely because a numerical
  difference is large.
- Do not pretend an UNKNOWN discrepancy has a known cause.

CLASSIFICATION OPTIONS:

"PROCESSING_FEE"
"REFUND"
"DUPLICATE"
"STATUS_ISSUE"
"MISSING_RECORD"
"AMOUNT_DISCREPANCY"
"UNKNOWN"

Return ONLY valid JSON with exactly these fields:

{{
  "classification": "PROCESSING_FEE | REFUND | DUPLICATE | STATUS_ISSUE | MISSING_RECORD | AMOUNT_DISCREPANCY | UNKNOWN",
  "explanation": "Clear explanation based only on the evidence.",
  "confidence": 0.0,
  "recommended_action": "Specific manual investigation action.",
  "evidence_summary": {{
    "key_facts": [],
    "financial_difference": "",
    "known_cause": false
  }}
}}

The deterministic system is the source of truth.

Use ONLY the evidence provided below.

Evidence:

{evidence_json}
"""

def parse_ai_response(response_text):
    """
    Parse and validate Gemini's JSON response.
    """

    cleaned = response_text.strip()

    # Handle accidental markdown fences.
    if cleaned.startswith("```"):
        cleaned = cleaned.replace(
            "```json",
            "",
            1,
        )

        cleaned = cleaned.replace(
            "```",
            "",
        ).strip()

    data = json.loads(cleaned)

    required_fields = {
        "classification",
        "explanation",
        "confidence",
        "recommended_action",
        "evidence_summary",
    }

    missing = (
        required_fields
        - set(data.keys())
    )

    if missing:
        raise ValueError(
            f"AI response missing fields: {missing}"
        )

    valid_classifications = {
        "PROCESSING_FEE",
        "REFUND",
        "DUPLICATE",
        "STATUS_ISSUE",
        "MISSING_RECORD",
        "AMOUNT_DISCREPANCY",
        "UNKNOWN",
    }

    if (
        data["classification"]
        not in valid_classifications
    ):
        raise ValueError(
            "Invalid AI classification."
        )

    confidence = float(
        data["confidence"]
    )

    if not 0 <= confidence <= 1:
        raise ValueError(
            "AI confidence must be between 0 and 1."
        )

    if not isinstance(
        data["evidence_summary"],
        dict,
    ):
        raise ValueError(
            "evidence_summary must be an object."
        )

    return data


def analyze_exception(
    reconciliation_id,
):
    """
    Analyze ONE reconciliation exception
    using Gemini.

    Returns the persisted AIAnalysis object.
    """

    reconciliation = (
        ReconciliationResult.objects
        .select_related("transaction")
        .get(
            id=reconciliation_id
        )
    )

    if reconciliation.result != "EXCEPTION":
        raise ValueError(
            "AI analysis is only allowed for exceptions."
        )

    evidence = build_exception_evidence(
        reconciliation
    )

    prompt = build_prompt(
        evidence
    )

    client = get_gemini_client()

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )

    if not response.text:
        raise ValueError(
            "Gemini returned an empty response."
        )

    analysis_data = parse_ai_response(
        response.text
    )

    ai_analysis, created = (
        AIAnalysis.objects.update_or_create(

            reconciliation=reconciliation,

            defaults={
                "classification": (
                    analysis_data[
                        "classification"
                    ]
                ),

                "explanation": (
                    analysis_data[
                        "explanation"
                    ]
                ),

                "confidence": (
                    analysis_data[
                        "confidence"
                    ]
                ),

                "recommended_action": (
                    analysis_data[
                        "recommended_action"
                    ]
                ),

                "evidence_summary": (
                    analysis_data[
                        "evidence_summary"
                    ]
                ),

                "model_name": MODEL_NAME,

                "prompt_version": (
                    PROMPT_VERSION
                ),
            },
        )
    )

    return ai_analysis