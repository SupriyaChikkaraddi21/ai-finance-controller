import csv
import os
import random

random.seed(42)

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(BASE_DIR, "data")

TRANSACTIONS_FILE = os.path.join(
    DATA_DIR,
    "transactions.csv"
)

GROUND_TRUTH_FILE = os.path.join(
    DATA_DIR,
    "ground_truth.csv"
)


def money(value):
    if value is None:
        return None

    return round(float(value), 2)


def create_transaction(transaction_id, case_type):
    payment_amount = random.choice(
        [
            499,
            799,
            999,
            1299,
            1499,
            1999,
            2499,
            2999,
            3999,
            4999,
        ]
    )

    fee = money(payment_amount * 0.02)
    refund = 0.0
    adjustment = 0.0

    expected_settlement = money(
        payment_amount
        - fee
        - refund
        + adjustment
    )

    actual_settlement = expected_settlement

    payment_status = "SUCCESS"
    settlement_status = "SETTLED"

    # ==================================================
    # VALID RECONCILED TRANSACTION
    # ==================================================

    if case_type == "MATCHED":
        pass

    # ==================================================
    # VALID REFUND
    # ==================================================

    elif case_type == "REFUND":

        refund = money(
            payment_amount * 0.25
        )

        expected_settlement = money(
            payment_amount
            - fee
            - refund
            + adjustment
        )

        actual_settlement = expected_settlement
    # ==================================================
    # CALCULATION MISMATCH
    # ==================================================

    elif case_type == "CALCULATION_MISMATCH":

        expected_settlement = money(
            expected_settlement - 50
        )

        actual_settlement = expected_settlement

    # ==================================================
    # MISSING SETTLEMENT
    # ==================================================

    elif case_type == "MISSING_SETTLEMENT":

        actual_settlement = None
        settlement_status = "MISSING"

    # ==================================================
    # MISSING PAYMENT
    # ==================================================

    elif case_type == "MISSING_PAYMENT":

        payment_amount = None
        expected_settlement = None
        actual_settlement = None
        payment_status = "MISSING"

    # ==================================================
    # UNEXPLAINED AMOUNT DIFFERENCE
    # ==================================================

    elif case_type == "AMOUNT_MISMATCH":

        actual_settlement = money(
            expected_settlement + 100
        )

    # ==================================================
    # STATUS MISMATCH
    # ==================================================

    elif case_type == "STATUS_MISMATCH":

        settlement_status = "FAILED"

    return {
        "transaction_id": transaction_id,
        "order_id": f"ORD{transaction_id[3:]}",
        "payment_amount": payment_amount,
        "fee": fee,
        "refund": refund,
        "adjustment": adjustment,
        "expected_settlement": expected_settlement,
        "actual_settlement": actual_settlement,
        "payment_status": payment_status,
        "settlement_status": settlement_status,
    }


def expected_ground_truth(case_type):
    """
    Ground truth describes the correct reconciliation
    outcome based on the financial evidence.
    """

    if case_type in {
        "MATCHED",
        "REFUND",
    }:
        return {
            "expected_result": "MATCHED",
            "exception_type": "",
        }

    return {
        "expected_result": "EXCEPTION",
        "exception_type": case_type,
    }


def main():

    transactions = []
    ground_truth = []
    cases = [
        ("MATCHED", 70),
        ("REFUND", 5),
        ("MISSING_SETTLEMENT", 4),
        ("MISSING_PAYMENT", 3),
        ("CALCULATION_MISMATCH", 12),
        ("STATUS_MISMATCH", 3),
        ("DUPLICATE", 3),
    ]
    transaction_number = 1

    # ==================================================
    # CREATE NORMAL RECORDS
    # ==================================================

    for case_type, count in cases:

        # Duplicate records are handled separately.
        if case_type == "DUPLICATE":
            continue

        for _ in range(count):

            transaction_id = (
                f"TXN{transaction_number:04d}"
            )

            transaction = create_transaction(
                transaction_id,
                case_type
            )

            transactions.append(transaction)

            truth = expected_ground_truth(
                case_type
            )

            ground_truth.append(
                {
                    "transaction_id": transaction_id,
                    "expected_result": truth[
                        "expected_result"
                    ],
                    "exception_type": truth[
                        "exception_type"
                    ],
                }
            )

            transaction_number += 1

    # ==================================================
    # CREATE 3 DUPLICATE ORDER RECORDS
    # ==================================================

    duplicate_sources = [
        transactions[0],
        transactions[1],
        transactions[2],
    ]

    for index, source in enumerate(
        duplicate_sources,
        start=1
    ):

        duplicate = source.copy()

        duplicate["transaction_id"] = (
            f"TXN{transaction_number:04d}"
        )

        # IMPORTANT:
        # Same order_id means this is a duplicate
        # of an existing order.

        duplicate["order_id"] = source["order_id"]

        transactions.append(duplicate)

        ground_truth.append(
            {
                "transaction_id": duplicate[
                    "transaction_id"
                ],
                "expected_result": "EXCEPTION",
                "exception_type": "DUPLICATE",
            }
        )

        transaction_number += 1

    # ==================================================
    # WRITE transactions.csv
    # ==================================================

    transaction_fields = [
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
    ]

    with open(
        TRANSACTIONS_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=transaction_fields
        )

        writer.writeheader()
        writer.writerows(transactions)

    # ==================================================
    # WRITE ground_truth.csv
    # ==================================================

    ground_truth_fields = [
        "transaction_id",
        "expected_result",
        "exception_type",
    ]

    with open(
        GROUND_TRUTH_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=ground_truth_fields
        )

        writer.writeheader()
        writer.writerows(ground_truth)

    print("Dataset generated successfully!")
    print(
        f"Transactions: {len(transactions)}"
    )
    print(
        f"Ground truth: {len(ground_truth)}"
    )
    print()
    print(
        f"Created: {TRANSACTIONS_FILE}"
    )
    print(
        f"Created: {GROUND_TRUTH_FILE}"
    )


if __name__ == "__main__":
    main()