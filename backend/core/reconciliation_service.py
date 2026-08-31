import csv
import os
import time
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from .models import (
    Batch,
    Transaction,
    ReconciliationResult,
    AuditLog,
)

from .reconciliation_rules import (
    reconcile_transaction,
    to_decimal,
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
# DETERMINISTIC RECONCILIATION
# ============================================================



# ============================================================
# BATCH RECONCILIATION
# ============================================================
@transaction.atomic
def reconcile_batch(batch_id):
    """
    Reconcile the complete CSV dataset and persist
    transactions + reconciliation results into PostgreSQL.
    """

    start_time = time.perf_counter()
    batch = Batch.objects.get(
        id=batch_id
    )
    if batch.status == "COMPLETED":
        raise ValueError(
            "This batch has already been reconciled."
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
    throughput_records_per_sec = (
    round(
        total / (processing_time_ms / 1000),
        2,
    )
    if processing_time_ms > 0
    else 0
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
