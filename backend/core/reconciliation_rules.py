from decimal import Decimal


MONEY_QUANTUM = Decimal("0.01")
MISMATCH_TOLERANCE = Decimal("0.01")


def to_decimal(value):
    """
    Convert a financial value into Decimal with 2 decimal places.

    Empty values become None.
    """

    if value is None or value == "":
        return None

    return Decimal(str(value)).quantize(
        MONEY_QUANTUM
    )


def reconcile_transaction(transaction):
    """
    Apply the deterministic financial reconciliation rules
    to a single transaction.

    This function contains ONLY financial decision logic.
    It does not access the database, files, Django models,
    or AI services.
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

    # RULE 1 — Missing Payment
    if (
        payment_status == "MISSING"
        or payment is None
    ):
        exceptions.append(
            "MISSING_PAYMENT"
        )

    # RULE 2 — Missing Settlement
    if (
        settlement_status == "MISSING"
        or actual is None
    ):
        exceptions.append(
            "MISSING_SETTLEMENT"
        )

    # RULE 3 — Settlement Calculation
    if payment is not None:

        calculated_expected = (
            payment
            - fee
            - refund
            + adjustment
        ).quantize(
            MONEY_QUANTUM
        )

        if expected is not None:

            if (
                abs(
                    calculated_expected
                    - expected
                )
                > MISMATCH_TOLERANCE
            ):
                exceptions.append(
                    "CALCULATION_MISMATCH"
                )

    # RULE 4 — Actual vs Expected Settlement
    difference = None

    if (
        actual is not None
        and expected is not None
    ):

        difference = (
            actual - expected
        ).quantize(
            MONEY_QUANTUM
        )

        if (
            abs(difference)
            > MISMATCH_TOLERANCE
        ):
            exceptions.append(
                "AMOUNT_MISMATCH"
            )

    # RULE 5 — Status Validation
    if (
        payment_status == "SUCCESS"
        and settlement_status == "FAILED"
    ):
        exceptions.append(
            "STATUS_MISMATCH"
        )

    # Remove duplicate exception labels
    exceptions = list(
        dict.fromkeys(exceptions)
    )

    # Final classification
    if not exceptions:

        result = "MATCHED"
        exception_type = ""
        requires_review = False

    else:

        result = "EXCEPTION"
        requires_review = True

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

            exception_type = (
                "AMOUNT_MISMATCH"
            )

        else:

            exception_type = exceptions[0]

    return {
        "result": result,
        "exception_type": exception_type,
        "requires_manual_review": requires_review,
        "difference": difference,
    }
