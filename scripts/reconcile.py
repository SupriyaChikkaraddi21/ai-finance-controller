import csv
import os
import time


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
# RECONCILE ONE TRANSACTION
# ============================================================

def reconcile_transaction(transaction):
    """
    Apply deterministic reconciliation rules
    to a single transaction.
    """

    transaction_id = transaction[
        "transaction_id"
    ]

    payment = to_float(
        transaction["payment_amount"]
    )

    fee = to_float(
        transaction["fee"]
    )

    refund = to_float(
        transaction["refund"]
    )

    adjustment = to_float(
        transaction["adjustment"]
    )

    expected = to_float(
        transaction["expected_settlement"]
    )

    actual = to_float(
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
    # RULE 1 — Missing Payment
    # ========================================================

    if (
        payment_status == "MISSING"
        or payment is None
    ):

        exceptions.append(
            "MISSING_PAYMENT"
        )

    # ========================================================
    # RULE 2 — Missing Settlement
    # ========================================================

    if (
        settlement_status == "MISSING"
        or actual is None
    ):

        exceptions.append(
            "MISSING_SETTLEMENT"
        )

    # ========================================================
    # RULE 3 — Settlement Calculation
    # ========================================================

    if payment is not None:

        calculated_expected = round(
            payment
            - fee
            - refund
            + adjustment,
            2
        )

        if expected is not None:

            if (
                abs(
                    calculated_expected
                    - expected
                ) > 0.01
            ):

                exceptions.append(
                    "CALCULATION_MISMATCH"
                )

    # ========================================================
    # RULE 4 — Actual vs Expected Settlement
    # ========================================================

    difference = None

    if (
        actual is not None
        and expected is not None
    ):

        difference = round(
            actual - expected,
            2
        )

        if abs(difference) > 0.01:

            exceptions.append(
                "AMOUNT_MISMATCH"
            )

    # ========================================================
    # RULE 5 — Status Validation
    # ========================================================

    if (
        payment_status == "SUCCESS"
        and settlement_status == "FAILED"
    ):

        exceptions.append(
            "STATUS_MISMATCH"
        )

    # ========================================================
    # Remove duplicate exception labels
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
        # Determine primary exception
        # ----------------------------------------------------

        if (
            "MISSING_PAYMENT"
            in exceptions
        ):

            exception_type = (
                "MISSING_PAYMENT"
            )

        elif (
            "MISSING_SETTLEMENT"
            in exceptions
        ):

            exception_type = (
                "MISSING_SETTLEMENT"
            )

        elif (
            "CALCULATION_MISMATCH"
            in exceptions
        ):

            exception_type = (
                "CALCULATION_MISMATCH"
            )

        elif (
            "STATUS_MISMATCH"
            in exceptions
        ):

            exception_type = (
                "STATUS_MISMATCH"
            )

        elif (
            "AMOUNT_MISMATCH"
            in exceptions
        ):

            exception_type = (
                "AMOUNT_MISMATCH"
            )

        else:

            exception_type = (
                exceptions[0]
            )

    # ========================================================
    # RESULT
    # ========================================================

    return {

        "transaction_id": (
            transaction_id
        ),

        "order_id": (
            transaction["order_id"]
        ),

        "result": (
            result
        ),

        "exception_type": (
            exception_type
        ),

        "requires_manual_review": (
            requires_review
        ),

        "payment_amount": (
            payment
        ),

        "fee": (
            fee
        ),

        "refund": (
            refund
        ),

        "adjustment": (
            adjustment
        ),

        "expected_settlement": (
            expected
        ),

        "actual_settlement": (
            actual
        ),

        "difference": (
            difference
        ),

        "payment_status": (
            payment_status
        ),

        "settlement_status": (
            settlement_status
        ),
    }


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

        result = reconcile_transaction(
            transaction
        )

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