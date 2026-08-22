from decimal import Decimal

from django.db.models import Count

from ..models import (
    Batch,
    Transaction,
    ReconciliationResult,
    AIAnalysis,
)


# ============================================================
# TOOL 1 — GET BATCH SUMMARY
# ============================================================

def get_batch_summary(batch_id):
    """
    Return the current deterministic reconciliation
    summary for a batch.
    """

    batch = Batch.objects.get(
        id=batch_id
    )

    return {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "status": batch.status,
        "total_records": batch.total_records,
        "matched_records": batch.matched_records,
        "exception_records": batch.exception_records,
        "match_rate": float(batch.match_rate),
        "exception_rate": (
            round(
                (
                    batch.exception_records
                    / batch.total_records
                ) * 100,
                2,
            )
            if batch.total_records
            else 0
        ),
        "processing_time_ms": (
            batch.processing_time_ms
        ),
    }


# ============================================================
# TOOL 2 — GET EXCEPTIONS
# ============================================================

def get_batch_exceptions(batch_id):
    """
    Return all deterministic exceptions for a batch.
    """

    results = (
        ReconciliationResult.objects
        .filter(
            transaction__batch_id=batch_id,
            result="EXCEPTION",
        )
        .select_related("transaction")
        .order_by(
            "transaction__transaction_id"
        )
    )

    return [
        {
            "reconciliation_id": result.id,
            "transaction_id": (
                result.transaction.transaction_id
            ),
            "order_id": (
                result.transaction.order_id
            ),
            "exception_type": (
                result.exception_type
            ),
            "difference": (
                str(result.difference)
                if result.difference is not None
                else None
            ),
            "requires_manual_review": (
                result.requires_manual_review
            ),
        }
        for result in results
    ]


# ============================================================
# TOOL 3 — GET TRANSACTION EVIDENCE
# ============================================================

def get_transaction_evidence(
    reconciliation_id
):
    """
    Return the complete financial evidence associated
    with one reconciliation result.
    """

    reconciliation = (
        ReconciliationResult.objects
        .select_related("transaction")
        .get(
            id=reconciliation_id
        )
    )

    transaction = reconciliation.transaction

    return {
        "reconciliation_id": (
            reconciliation.id
        ),
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
        "adjustment": str(transaction.adjustment),
        "expected_settlement": (
            str(transaction.expected_settlement)
            if transaction.expected_settlement is not None
            else None
        ),
        "actual_settlement": (
            str(transaction.actual_settlement)
            if transaction.actual_settlement is not None
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


# ============================================================
# TOOL 4 — GET EXISTING AI ANALYSIS
# ============================================================

def get_ai_analysis(
    reconciliation_id
):
    """
    Retrieve an existing AI analysis.

    This prevents unnecessary Gemini API calls when an
    exception has already been analyzed.
    """

    try:

        analysis = (
            AIAnalysis.objects
            .get(
                reconciliation_id=reconciliation_id
            )
        )

    except AIAnalysis.DoesNotExist:

        return {
            "available": False,
            "reconciliation_id": reconciliation_id,
        }

    return {
        "available": True,
        "analysis_id": analysis.id,
        "reconciliation_id": reconciliation_id,
        "classification": analysis.classification,
        "explanation": analysis.explanation,
        "confidence": (
            float(analysis.confidence)
            if analysis.confidence is not None
            else None
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


# ============================================================
# TOOL 5 — VERIFY AI ANALYSIS
# ============================================================

def verify_ai_analysis(
    reconciliation_id
):
    """
    Deterministic verification layer.

    The LLM cannot override financial truth.

    Returns whether the AI classification is sufficiently
    supported by deterministic evidence.
    """

    reconciliation = (
        ReconciliationResult.objects
        .select_related("transaction")
        .get(
            id=reconciliation_id
        )
    )

    try:

        analysis = (
            AIAnalysis.objects
            .get(
                reconciliation_id=reconciliation_id
            )
        )

    except AIAnalysis.DoesNotExist:

        return {
            "verified": False,
            "resolution": "MANUAL_REVIEW",
            "reason": "No AI analysis exists.",
        }

    classification = (
        analysis.classification
    )

    confidence = (
        float(analysis.confidence)
        if analysis.confidence is not None
        else 0
    )

    deterministic_exception = (
        reconciliation.exception_type
    )

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

    if classification == "UNKNOWN":

        return {
            "verified": True,
            "resolution": "MANUAL_REVIEW",
            "reason": (
                "Evidence does not establish a "
                "specific root cause."
            ),
            "classification": classification,
            "confidence": confidence,
        }

    # --------------------------------------------------------
    # MISSING RECORD
    # --------------------------------------------------------

    if (
        classification == "MISSING_RECORD"
        and deterministic_exception
        in {
            "MISSING_PAYMENT",
            "MISSING_SETTLEMENT",
        }
    ):

        return {
            "verified": True,
            "resolution": "CONFIRMED",
            "reason": (
                "Deterministic reconciliation confirms "
                "a missing financial record."
            ),
            "classification": classification,
            "confidence": confidence,
        }

    # --------------------------------------------------------
    # STATUS ISSUE
    # --------------------------------------------------------

    if (
        classification == "STATUS_ISSUE"
        and deterministic_exception
        == "STATUS_MISMATCH"
    ):

        return {
            "verified": True,
            "resolution": "CONFIRMED",
            "reason": (
                "Deterministic reconciliation confirms "
                "a payment/settlement status conflict."
            ),
            "classification": classification,
            "confidence": confidence,
        }

    # --------------------------------------------------------
    # DUPLICATE
    # --------------------------------------------------------

    if (
        classification == "DUPLICATE"
        and deterministic_exception
        == "DUPLICATE"
    ):

        return {
            "verified": True,
            "resolution": "CONFIRMED",
            "reason": (
                "Deterministic reconciliation confirms "
                "the duplicate transaction."
            ),
            "classification": classification,
            "confidence": confidence,
        }

    # --------------------------------------------------------
    # AMOUNT DISCREPANCY
    # --------------------------------------------------------

    if (
        classification
        == "AMOUNT_DISCREPANCY"
    ):

        if (
            reconciliation.difference
            is not None
        ):

            return {
                "verified": False,
                "resolution": "MANUAL_REVIEW",
                "reason": (
                    "A financial difference exists, "
                    "but the deterministic evidence "
                    "does not establish its root cause."
                ),
                "classification": classification,
                "confidence": confidence,
            }

    # --------------------------------------------------------
    # PROCESSING FEE / REFUND
    # --------------------------------------------------------

    transaction = (
        reconciliation.transaction
    )

    if (
        classification
        == "PROCESSING_FEE"
    ):

        if transaction.fee and transaction.fee > 0:

            return {
                "verified": True,
                "resolution": "CONFIRMED",
                "reason": (
                    "A processing fee is explicitly "
                    "present in the transaction evidence."
                ),
                "classification": classification,
                "confidence": confidence,
            }

    if classification == "REFUND":

        if (
            transaction.refund
            and transaction.refund > 0
        ):

            return {
                "verified": True,
                "resolution": "CONFIRMED",
                "reason": (
                    "A refund is explicitly present "
                    "in the transaction evidence."
                ),
                "classification": classification,
                "confidence": confidence,
            }

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return {
        "verified": False,
        "resolution": "MANUAL_REVIEW",
        "reason": (
            "AI classification could not be verified "
            "against deterministic evidence."
        ),
        "classification": classification,
        "confidence": confidence,
    }


# ============================================================
# TOOL 6 — BUILD CONTROLLER REPORT
# ============================================================

def build_controller_report(
    batch_id,
    analyses,
):
    """
    Build the final finance controller report.
    """

    batch = Batch.objects.get(
        id=batch_id
    )

    confirmed = [
        item
        for item in analyses
        if item["resolution"] == "CONFIRMED"
    ]

    manual_review = [
        item
        for item in analyses
        if item["resolution"] == "MANUAL_REVIEW"
    ]

    analyzed = len(analyses)

    return {
        "batch_id": batch.id,
        "batch_name": batch.name,
        "total_transactions": (
            batch.total_records
        ),
        "matched_transactions": (
            batch.matched_records
        ),
        "deterministic_exceptions": (
            batch.exception_records
        ),
        "match_rate": float(
            batch.match_rate
        ),
        "agent": {
            "exceptions_analyzed": analyzed,
            "confirmed_exceptions": len(
                confirmed
            ),
            "manual_review_required": len(
                manual_review
            ),
            "analysis_coverage": (
                round(
                    (
                        analyzed
                        / batch.exception_records
                    ) * 100,
                    2,
                )
                if batch.exception_records
                else 0
            ),
        },
        "unresolved_exceptions": manual_review,
        "resolved_exceptions": confirmed,
    }
# ============================================================
# TOOL — ASSESS EXCEPTION RISK
# ============================================================

def assess_exception_risk(reconciliation_id):
    """
    Assess the operational risk of a reconciliation exception.

    This tool does NOT change financial data.
    It only evaluates how urgently the exception
    should be investigated.
    """

    result = (
        ReconciliationResult.objects
        .select_related("transaction")
        .get(id=reconciliation_id)
    )

    transaction = result.transaction

    difference = (
        abs(result.difference)
        if result.difference is not None
        else Decimal("0")
    )

    risk = "LOW"
    reasons = []

    # --------------------------------------------------------
    # HIGH RISK CONDITIONS
    # --------------------------------------------------------

    if result.exception_type in {
        "MISSING_PAYMENT",
        "MISSING_SETTLEMENT",
        "DUPLICATE",
    }:
        risk = "HIGH"

        reasons.append(
            f"Exception type {result.exception_type} "
            "can directly affect financial completeness."
        )

    elif difference >= Decimal("100"):
        risk = "HIGH"

        reasons.append(
            f"Financial difference is {difference}, "
            "which is significant."
        )

    # --------------------------------------------------------
    # MEDIUM RISK CONDITIONS
    # --------------------------------------------------------

    elif result.exception_type in {
        "STATUS_MISMATCH",
        "AMOUNT_MISMATCH",
        "CALCULATION_MISMATCH",
    }:
        risk = "MEDIUM"

        reasons.append(
            "Exception requires additional financial evidence "
            "before resolution."
        )

    elif difference > Decimal("0"):
        risk = "MEDIUM"

        reasons.append(
            f"Unexplained financial difference of {difference}."
        )

    # --------------------------------------------------------
    # UNKNOWN / MANUAL REVIEW
    # --------------------------------------------------------

    elif result.exception_type == "UNKNOWN":
        risk = "MEDIUM"

        reasons.append(
            "Root cause is not established by deterministic "
            "reconciliation evidence."
        )

    return {
        "reconciliation_id": result.id,
        "transaction_id": transaction.transaction_id,
        "exception_type": result.exception_type,
        "difference": str(difference),
        "risk_level": risk,
        "reasons": reasons,
        "requires_manual_review": (
            risk == "HIGH"
            or result.exception_type == "UNKNOWN"
        ),
    }