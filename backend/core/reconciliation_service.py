import csv
import os
import time
from decimal import Decimal

from django.utils import timezone

from .models import (
    Batch,
    Transaction,
    ReconciliationResult,
    AuditLog,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

TRANSACTIONS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "transactions.csv",
)


# ============================================================
# HELPERS
# ============================================================

def to_decimal(value):
    """
    Convert a CSV value into Decimal with 2 decimal places.

    Empty values become None.
    """

    if value is None or value == "":
        return None

    return Decimal(str(value)).quantize(
        Decimal("0.01")
    )


# ============================================================
# DETERMINISTIC RECONCILIATION
# ============================================================

def reconcile_transaction(transaction):
    """
    Reconcile ONE transaction using deterministic
    financial rules.

    No AI is used here.
    """

    payment = to_decimal(
        transaction["payment_amount"]
    )

    fee = (
        to_decimal(transaction["fee"])
        or Decimal("0.00")
    )

    refund = (
        to_decimal(transaction["refund"])
        or Decimal("0.00")
    )

    adjustment = (
        to_decimal(transaction["adjustment"])
        or Decimal("0.00")
    )

    expected = to_decimal(
        transaction["expected_settlement"]
    )

    actual = to_decimal(
        transaction["actual_settlement"]
    )

    payment_status = transaction[
        "payment_status"
    ]

    settlement_status = transaction[
        "settlement_status"
    ]

    exceptions = []

    # ========================================================
    # RULE 1 — MISSING PAYMENT
    # ========================================================

    if (
        payment_status == "MISSING"
        or payment is None
    ):
        exceptions.append(
            "MISSING_PAYMENT"
        )

    # ========================================================
    # RULE 2 — MISSING SETTLEMENT
    # ========================================================

    if (
        settlement_status == "MISSING"
        or actual is None
    ):
        exceptions.append(
            "MISSING_SETTLEMENT"
        )

    # ========================================================
    # RULE 3 — EXPECTED SETTLEMENT CALCULATION
    #
    # Expected settlement =
    # payment - fee - refund + adjustment
    # ========================================================

    if payment is not None:

        calculated_expected = (
            payment
            - fee
            - refund
            + adjustment
        )

        calculated_expected = (
            calculated_expected.quantize(
                Decimal("0.01")
            )
        )

        if expected is not None:

            if (
                abs(
                    calculated_expected
                    - expected
                )
                > Decimal("0.01")
            ):
                exceptions.append(
                    "CALCULATION_MISMATCH"
                )

    # ========================================================
    # RULE 4 — ACTUAL VS EXPECTED SETTLEMENT
    # ========================================================

    difference = None

    if (
        actual is not None
        and expected is not None
    ):

        difference = (
            actual - expected
        ).quantize(
            Decimal("0.01")
        )

        if abs(difference) > Decimal("0.01"):

            exceptions.append(
                "AMOUNT_MISMATCH"
            )

    # ========================================================
    # RULE 5 — STATUS VALIDATION
    # ========================================================

    if (
        payment_status == "SUCCESS"
        and settlement_status == "FAILED"
    ):
        exceptions.append(
            "STATUS_MISMATCH"
        )

    # ========================================================
    # REMOVE DUPLICATE EXCEPTION LABELS
    # ========================================================

    exceptions = list(
        dict.fromkeys(exceptions)
    )

    # ========================================================
    # FINAL CLASSIFICATION
    # ========================================================

    if not exceptions:

        result = "MATCHED"

        exception_type = ""

        requires_review = False

    else:

        result = "EXCEPTION"

        requires_review = True

        # ----------------------------------------------------
        # Known exception priority
        # ----------------------------------------------------

        if "MISSING_PAYMENT" in exceptions:

            exception_type = (
                "MISSING_PAYMENT"
            )

        elif "MISSING_SETTLEMENT" in exceptions:

            exception_type = (
                "MISSING_SETTLEMENT"
            )

        elif "CALCULATION_MISMATCH" in exceptions:

            exception_type = (
                "CALCULATION_MISMATCH"
            )

        elif "STATUS_MISMATCH" in exceptions:

            exception_type = (
                "STATUS_MISMATCH"
            )

        elif "AMOUNT_MISMATCH" in exceptions:

            # The deterministic engine knows
            # that the amount differs, but if no
            # known rule explains the difference,
            # it becomes UNKNOWN.
            exception_type = "UNKNOWN"

        else:

            exception_type = exceptions[0]

    return {
        "result": result,
        "exception_type": exception_type,
        "requires_manual_review": requires_review,
        "difference": difference,
    }


# ============================================================
# BATCH RECONCILIATION
# ============================================================

def reconcile_batch(batch_id):
    """
    Reconcile the complete CSV dataset and persist
    transactions + reconciliation results into PostgreSQL.
    """

    start_time = time.perf_counter()

    batch = Batch.objects.get(
        id=batch_id
    )

    # ========================================================
    # MARK BATCH AS PROCESSING
    # ========================================================

    batch.status = "PROCESSING"

    batch.save(
        update_fields=["status"]
    )

    AuditLog.objects.create(
        batch=batch,
        action="RECONCILIATION_STARTED",
        message=(
            "Deterministic reconciliation started."
        ),
    )

    # ========================================================
    # LOAD DATASET
    # ========================================================

    with open(
        TRANSACTIONS_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        transactions = list(
            csv.DictReader(file)
        )

    # ========================================================
    # PROCESS TRANSACTIONS
    #
    # IMPORTANT:
    #
    # The FIRST occurrence of an order is valid.
    # Only subsequent occurrences are duplicates.
    #
    # Example:
    #
    # ORD0001 → MATCHED
    # ORD0001 → DUPLICATE
    #
    # This matches our standalone reconciliation engine.
    # ========================================================

    seen_orders = set()

    results = []

    for row in transactions:

        order_id = row["order_id"]

        is_duplicate = (
            order_id in seen_orders
        )

        if not is_duplicate:

            seen_orders.add(order_id)

        # ====================================================
        # CREATE TRANSACTION IN DATABASE
        # ====================================================

        transaction = Transaction.objects.create(

            transaction_id=row[
                "transaction_id"
            ],

            order_id=row[
                "order_id"
            ],

            payment_amount=to_decimal(
                row["payment_amount"]
            ),

            fee=(
                to_decimal(row["fee"])
                or Decimal("0.00")
            ),

            refund=(
                to_decimal(row["refund"])
                or Decimal("0.00")
            ),

            adjustment=(
                to_decimal(row["adjustment"])
                or Decimal("0.00")
            ),

            expected_settlement=to_decimal(
                row["expected_settlement"]
            ),

            actual_settlement=to_decimal(
                row["actual_settlement"]
            ),

            payment_status=row[
                "payment_status"
            ],

            settlement_status=row[
                "settlement_status"
            ],

            batch=batch,
        )

        # ====================================================
        # RUN DETERMINISTIC ENGINE
        # ====================================================

        reconciliation = (
            reconcile_transaction(row)
        )

        # ====================================================
        # OVERRIDE ONLY THE SECOND DUPLICATE
        # ====================================================

        if is_duplicate:

            reconciliation[
                "result"
            ] = "EXCEPTION"

            reconciliation[
                "exception_type"
            ] = "DUPLICATE"

            reconciliation[
                "requires_manual_review"
            ] = True

        # ====================================================
        # STORE RECONCILIATION RESULT
        # ====================================================

        result = (
            ReconciliationResult.objects.create(

                transaction=transaction,

                result=reconciliation[
                    "result"
                ],

                exception_type=reconciliation[
                    "exception_type"
                ],

                difference=reconciliation[
                    "difference"
                ],

                requires_manual_review=(
                    reconciliation[
                        "requires_manual_review"
                    ]
                ),

                rule_version="v1",
            )
        )

        results.append(result)

    # ========================================================
    # CALCULATE BATCH METRICS
    # ========================================================

    total = len(results)

    matched = sum(
        1
        for result in results
        if result.result == "MATCHED"
    )

    exceptions = total - matched

    match_rate = (
        (matched / total) * 100
        if total
        else 0
    )

    processing_time_ms = int(
        (
            time.perf_counter()
            - start_time
        )
        * 1000
    )

    # ========================================================
    # UPDATE BATCH
    # ========================================================

    batch.total_records = total

    batch.matched_records = matched

    batch.exception_records = exceptions

    batch.match_rate = round(
        match_rate,
        2,
    )

    batch.processing_time_ms = (
        processing_time_ms
    )

    batch.status = "COMPLETED"

    batch.completed_at = (
        timezone.now()
    )

    batch.save()

    # ========================================================
    # AUDIT LOG
    # ========================================================

    AuditLog.objects.create(
        batch=batch,

        action=(
            "RECONCILIATION_COMPLETED"
        ),

        message=(
            f"Reconciliation completed. "
            f"{matched} matched, "
            f"{exceptions} exceptions."
        ),

        metadata={
            "total_records": total,

            "matched_records": matched,

            "exception_records": exceptions,

            "match_rate": round(
                match_rate,
                2,
            ),

            "processing_time_ms": (
                processing_time_ms
            ),
        },
    )

    return batch