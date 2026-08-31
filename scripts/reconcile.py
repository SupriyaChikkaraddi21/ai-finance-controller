import csv
import os
import sys
import time
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)
            )
        ),
        "backend",
    ),
)

from core.reconciliation_rules import (
    reconcile_transaction as apply_reconciliation_rules,
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

INPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "transactions.csv"
)

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "reconciliation_results.csv"
)


# ============================================================
# REQUIRED CSV COLUMNS
# ============================================================

REQUIRED_COLUMNS = {
    "transaction_id",
    "order_id",
    "payment_amount",
    "fee",
    "refund",
    "adjustment",
    "expected_settlement",
    "actual_settlement",
    "payment_status",
    "settlement_status",
}


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_columns(fieldnames):
    """
    Validate that the input CSV contains
    all required financial columns.
    """

    if fieldnames is None:

        raise ValueError(
            "CSV file is missing a header row."
        )

    missing_columns = (
        REQUIRED_COLUMNS
        - set(fieldnames)
    )

    if missing_columns:

        missing = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"Missing required CSV column(s): {missing}"
        )


# ============================================================
# MONEY CONVERSION
# ============================================================

def to_float(value):
    """
    Convert CSV value to float.

    Empty values become None.
    Invalid numeric values raise a clear
    validation error.
    """

    if value is None or value == "":
        return None

    try:

        return round(
            float(value),
            2
        )

    except (TypeError, ValueError):

        raise ValueError(
            f"Invalid numeric value: '{value}'"
        )
# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "Starting reconciliation..."
    )

    print()

    # ========================================================
    # LOAD + VALIDATE DATASET
    # ========================================================

    try:

        with open(
            INPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(
                file
            )

            validate_columns(
                reader.fieldnames
            )

            transactions = list(
                reader
            )

    except (
        OSError,
        csv.Error,
        ValueError
    ) as error:

        print(
            f"INPUT VALIDATION ERROR: {error}"
        )

        return 1

    print(
        f"Loaded transactions: "
        f"{len(transactions)}"
    )

    # ========================================================
    # START PERFORMANCE TIMER
    # ========================================================

    start_time = time.perf_counter()

    # ========================================================
    # RECONCILE TRANSACTIONS
    # ========================================================

    results = []

    seen_orders = set()

    duplicate_count = 0

    for transaction in transactions:

        order_id = transaction[
            "order_id"
        ]

        is_duplicate = (
            order_id in seen_orders
        )

        if not is_duplicate:

            seen_orders.add(
                order_id
            )

        result = apply_reconciliation_rules(
            transaction
        )

        result["transaction_id"] = transaction[
            "transaction_id"
        ]

        result["order_id"] = transaction[
            "order_id"
        ]

        result["payment_amount"] = to_float(
            transaction["payment_amount"]
        )

        result["fee"] = to_float(
            transaction["fee"]
        )

        result["refund"] = to_float(
            transaction["refund"]
        )

        result["adjustment"] = to_float(
            transaction["adjustment"]
        )

        result["expected_settlement"] = to_float(
            transaction["expected_settlement"]
        )

        result["actual_settlement"] = to_float(
            transaction["actual_settlement"]
        )

        result["payment_status"] = transaction[
            "payment_status"
        ]

        result["settlement_status"] = transaction[
            "settlement_status"
        ]

        # ----------------------------------------------------
        # Duplicate detection
        # ----------------------------------------------------

        if is_duplicate:

            result["result"] = (
                "EXCEPTION"
            )

            result[
                "exception_type"
            ] = "DUPLICATE"

            result[
                "requires_manual_review"
            ] = True

            duplicate_count += 1

        results.append(
            result
        )

    print(
        f"Duplicate orders detected: "
        f"{duplicate_count}"
    )

    print()

    # ========================================================
    # METRICS
    # ========================================================

    total = len(
        results
    )

    matched = sum(
        1
        for result in results
        if result["result"]
        == "MATCHED"
    )

    exceptions = (
        total - matched
    )

    match_rate = (

        round(
            (
                matched
                / total
            ) * 100,
            2
        )

        if total

        else 0
    )

    exception_rate = (

        round(
            (
                exceptions
                / total
            ) * 100,
            2
        )

        if total

        else 0
    )

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    fields = [

        "transaction_id",

        "order_id",

        "result",

        "exception_type",

        "requires_manual_review",

        "payment_amount",

        "fee",

        "refund",

        "adjustment",

        "expected_settlement",

        "actual_settlement",

        "difference",

        "payment_status",

        "settlement_status",
    ]

    try:

        with open(
            OUTPUT_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(
                results
            )

    except OSError as error:

        print(
            f"OUTPUT ERROR: {error}"
        )

        return 1

    # ========================================================
    # PERFORMANCE METRICS
    # ========================================================

    elapsed_seconds = (
        time.perf_counter()
        - start_time
    )

    processing_time_ms = round(
        elapsed_seconds * 1000,
        2
    )

    throughput = (

        total
        / elapsed_seconds

        if elapsed_seconds > 0

        else 0
    )

    throughput = round(
        throughput,
        2
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    print(
        "========================================"
    )

    print(
        "RECONCILIATION COMPLETE"
    )

    print(
        "========================================"
    )

    print(
        f"Total transactions : "
        f"{total}"
    )

    print(
        f"Matched            : "
        f"{matched}"
    )

    print(
        f"Exceptions         : "
        f"{exceptions}"
    )

    print(
        f"Match rate         : "
        f"{match_rate}%"
    )

    print(
        f"Exception rate     : "
        f"{exception_rate}%"
    )

    print(
        f"Processing time    : "
        f"{processing_time_ms} ms"
    )

    print(
        f"Throughput         : "
        f"{throughput} records/sec"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Results saved to:"
    )

    print(
        OUTPUT_FILE
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )