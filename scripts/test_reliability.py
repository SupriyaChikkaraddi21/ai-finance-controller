import csv
import os
import shutil
import subprocess
import sys


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)

TRANSACTIONS_FILE = os.path.join(
    DATA_DIR,
    "transactions.csv"
)

BACKUP_FILE = os.path.join(
    DATA_DIR,
    "transactions_backup.csv"
)


# ============================================================
# RECONCILIATION ENGINE
# ============================================================

def run_reconciliation():
    """
    Run the deterministic reconciliation engine
    and return the process result.
    """

    return subprocess.run(
        [
            sys.executable,
            os.path.join(
                BASE_DIR,
                "scripts",
                "reconcile.py"
            )
        ],
        capture_output=True,
        text=True,
    )


# ============================================================
# DATASET BACKUP / RESTORE
# ============================================================

def restore_dataset():
    """
    Restore the original valid dataset.
    """

    if os.path.exists(BACKUP_FILE):

        shutil.copy2(
            BACKUP_FILE,
            TRANSACTIONS_FILE
        )

        os.remove(BACKUP_FILE)


def backup_dataset():
    """
    Backup the current valid dataset.
    """

    shutil.copy2(
        TRANSACTIONS_FILE,
        BACKUP_FILE
    )


# ============================================================
# TEST 1 — MISSING REQUIRED COLUMN
# ============================================================

def test_missing_column():
    """
    Test CSV with a required column removed.
    """

    print()
    print("TEST 1 — MISSING REQUIRED COLUMN")
    print("----------------------------------------")

    backup_dataset()

    try:

        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            rows = list(reader)
            fields = reader.fieldnames

        fields.remove("payment_amount")

        with open(
            TRANSACTIONS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            for row in rows:

                row.pop(
                    "payment_amount",
                    None
                )

                writer.writerow(row)

        result = run_reconciliation()

        if result.returncode != 0:

            print("PASS")

            print(
                "System rejected the malformed CSV."
            )

            print(
                result.stderr.strip()
                or result.stdout.strip()
            )

        else:

            print("FAIL")

            print(
                "Reconciliation accepted a CSV "
                "with a missing required column."
            )

    finally:

        restore_dataset()


# ============================================================
# TEST 2 — EMPTY PAYMENT
# ============================================================

def test_empty_payment():
    """
    Test a valid CSV structure containing
    an empty financial value.
    """

    print()
    print("TEST 2 — EMPTY PAYMENT VALUE")
    print("----------------------------------------")

    backup_dataset()

    try:

        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        rows[0]["payment_amount"] = ""

        fields = list(
            rows[0].keys()
        )

        with open(
            TRANSACTIONS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(rows)

        result = run_reconciliation()

        if result.returncode == 0:

            print("PASS")

            print(
                "System handled the empty payment "
                "value without crashing."
            )

        else:

            print("FAIL")

            print(
                result.stderr.strip()
            )

    finally:

        restore_dataset()


# ============================================================
# TEST 3 — INVALID NUMERIC VALUE
# ============================================================

def test_invalid_numeric_value():
    """
    Test a non-numeric financial value.
    """

    print()
    print("TEST 3 — INVALID NUMERIC VALUE")
    print("----------------------------------------")

    backup_dataset()

    try:

        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        rows[0]["payment_amount"] = "INVALID"

        fields = list(
            rows[0].keys()
        )

        with open(
            TRANSACTIONS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(rows)

        result = run_reconciliation()

        if result.returncode != 0:

            print("PASS")

            print(
                "System rejected the invalid "
                "numeric value."
            )

            error_lines = [
                line.strip()
                for line in result.stderr.splitlines()
                if line.strip()
            ]

            if error_lines:

                print(
                    f"Controlled error: "
                    f"{error_lines[-1]}"
                )

        else:

            print("FAIL")

            print(
                "System accepted an invalid "
                "financial value."
            )

    finally:

        restore_dataset()


# ============================================================
# TEST 4 — DUPLICATE RECORD
# ============================================================

def test_duplicate_records():
    """
    Test that duplicate order records are detected
    without crashing the reconciliation engine.
    """

    print()
    print("TEST 4 — DUPLICATE RECORD")
    print("----------------------------------------")

    backup_dataset()

    try:

        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        duplicate = rows[0].copy()

        duplicate["transaction_id"] = (
            "TEST_DUPLICATE"
        )

        duplicate["order_id"] = (
            rows[0]["order_id"]
        )

        rows.append(duplicate)

        fields = list(
            rows[0].keys()
        )

        with open(
            TRANSACTIONS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(rows)

        result = run_reconciliation()

        if result.returncode != 0:

            print("FAIL")

            print(
                "Reconciliation crashed while "
                "processing a duplicate record."
            )

            error_lines = [
                line.strip()
                for line in result.stderr.splitlines()
                if line.strip()
            ]

            if error_lines:

                print(
                    f"Error: {error_lines[-1]}"
                )

            return

        results_file = os.path.join(
            DATA_DIR,
            "reconciliation_results.csv"
        )

        with open(
            results_file,
            "r",
            encoding="utf-8"
        ) as file:

            results = list(
                csv.DictReader(file)
            )

        duplicate_results = [
            row
            for row in results
            if row["transaction_id"]
            == "TEST_DUPLICATE"
        ]

        if (
            duplicate_results
            and duplicate_results[0]["result"]
            == "EXCEPTION"
            and duplicate_results[0]["exception_type"]
            == "DUPLICATE"
        ):

            print("PASS")

            print(
                "System detected the duplicate "
                "record correctly."
            )

        else:

            print("FAIL")

            print(
                "System did not classify the "
                "duplicate record correctly."
            )

    finally:

        restore_dataset()


# ============================================================
# TEST 5 — HUGE AMOUNT DISCREPANCY
# ============================================================

def test_huge_discrepancy():
    """
    Test that a very large settlement discrepancy
    is detected as an exception.
    """

    print()
    print("TEST 5 — HUGE AMOUNT DISCREPANCY")
    print("----------------------------------------")

    backup_dataset()

    try:

        with open(
            TRANSACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            rows = list(
                csv.DictReader(file)
            )

        row = rows[0]

        expected = float(
            row["expected_settlement"]
        )

        row["actual_settlement"] = str(
            round(
                expected - 10000,
                2
            )
        )

        fields = list(
            rows[0].keys()
        )

        with open(
            TRANSACTIONS_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )

            writer.writeheader()

            writer.writerows(rows)

        result = run_reconciliation()

        if result.returncode != 0:

            print("FAIL")

            print(
                "Reconciliation crashed while "
                "processing a huge discrepancy."
            )

            return

        results_file = os.path.join(
            DATA_DIR,
            "reconciliation_results.csv"
        )

        with open(
            results_file,
            "r",
            encoding="utf-8"
        ) as file:

            results = list(
                csv.DictReader(file)
            )

        tested_result = next(
            (
                result
                for result in results
                if result["transaction_id"]
                == row["transaction_id"]
            ),
            None
        )

        if (
            tested_result
            and tested_result["result"]
            == "EXCEPTION"
            and tested_result["exception_type"]
            == "AMOUNT_MISMATCH"
        ):

            print("PASS")

            print(
                "System detected the huge "
                "settlement discrepancy."
            )

        else:

            print("FAIL")

            print(
                "System did not correctly "
                "classify the huge discrepancy."
            )

    finally:

        restore_dataset()


# ============================================================
# TEST 6 — AI API FAILURE
# ============================================================

def test_ai_api_failure():
    """
    Simulate a Gemini/API failure and verify that
    the backend returns a controlled MANUAL_REVIEW
    fallback without affecting deterministic results.
    """

    print()
    print("TEST 6 — AI API FAILURE")
    print("----------------------------------------")

    backend_dir = os.path.join(
        BASE_DIR,
        "backend"
    )

    if backend_dir not in sys.path:

        sys.path.insert(
            0,
            backend_dir
        )

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings"
    )

    import django

    django.setup()

    # --------------------------------------------------------
    # Allow Django's test client to use "testserver".
    # This is only for this reliability test.
    # --------------------------------------------------------

    from django.conf import settings

    if "testserver" not in settings.ALLOWED_HOSTS:

        settings.ALLOWED_HOSTS.append(
            "testserver"
        )

    # --------------------------------------------------------
    # Imports after Django setup
    # --------------------------------------------------------

    from unittest.mock import patch

    from django.test import Client

    from core.models import (
          Batch,
        ReconciliationResult,
    )

    # --------------------------------------------------------
    # Find a known exception
    # --------------------------------------------------------
    batch = (
        Batch.objects
        .filter(
            status="COMPLETED"
        )
        .order_by("-id")
        .first()
    )

    reconciliation = (
        ReconciliationResult.objects
        .filter(
            transaction__batch=batch,
            result="EXCEPTION"
        )
        .first()
        if batch
        else None
    )

    if reconciliation is None:

        print("FAIL")

        print(
            "No exception record is available "
            "for the AI failure test."
        )

        return

    # --------------------------------------------------------
    # Simulate Gemini failure
    # --------------------------------------------------------

    def simulated_ai_failure(
        *args,
        **kwargs
    ):

        raise RuntimeError(
            "Simulated Gemini API failure"
        )

    try:

        with patch(
            "core.views.analyze_exception",
            side_effect=simulated_ai_failure
        ):

            client = Client()

            response = client.post(
                f"/api/reconciliations/"
                f"{reconciliation.id}/ai-analysis/"
            )

        # ----------------------------------------------------
        # Make sure response is JSON before calling json()
        # ----------------------------------------------------

        if response.status_code != 503:

            print("FAIL")

            print(
                "Unexpected HTTP status."
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            print(
                f"Response: "
                f"{response.content.decode()}"
            )

            return

        try:

            data = response.json()

        except ValueError:

            print("FAIL")

            print(
                "AI failure endpoint returned "
                "a non-JSON response."
            )

            print(
                response.content.decode()
            )

            return

        # ----------------------------------------------------
        # Validate controlled fallback
        # ----------------------------------------------------

        if (
            data.get("fallback")
            == "MANUAL_REVIEW"
            and data.get("deterministic_result")
            == "EXCEPTION"
            and data.get("deterministic_exception")
            == (
                reconciliation.exception_type
            )
        ):

            print("PASS")

            print(
                "AI failure was handled safely."
            )

            print(
                "Fallback: MANUAL_REVIEW"
            )

            print(
                "Deterministic reconciliation "
                "remained unchanged."
            )

        else:

            print("FAIL")

            print(
                "AI failure did not produce "
                "the expected controlled fallback."
            )

            print(
                f"HTTP status: "
                f"{response.status_code}"
            )

            print(
                f"Response: {data}"
            )

    except Exception as error:

        print("FAIL")

        print(
            f"AI failure test crashed: "
            f"{error}"
        )


# ============================================================
# TEST 7 — MALFORMED AI RESPONSE
# ============================================================

def test_malformed_ai_response():
    """
    Simulate Gemini returning malformed JSON and verify
    that the API safely falls back to MANUAL_REVIEW.
    """

    print()
    print("TEST 7 — MALFORMED AI RESPONSE")
    print("----------------------------------------")

    backend_dir = os.path.join(
        BASE_DIR,
        "backend"
    )

    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        "config.settings"
    )

    import django
    django.setup()

    from django.conf import settings

    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")

    from unittest.mock import patch
    from django.test import Client
    from core.models import Batch, ReconciliationResult

    batch = (
        Batch.objects
        .filter(status="COMPLETED")
        .order_by("-id")
        .first()
    )

    reconciliation = (
        ReconciliationResult.objects
        .filter(
            transaction__batch=batch,
            result="EXCEPTION"
        )
        .first()
        if batch
        else None
    )

    if reconciliation is None:
        print("FAIL")
        print(
            "No exception record is available "
            "for the malformed AI response test."
        )
        return

    def simulated_malformed_response(*args, **kwargs):
        raise ValueError(
            "Malformed AI response: invalid JSON"
        )

    try:
        with patch(
            "core.views.analyze_exception",
            side_effect=simulated_malformed_response
        ):
            client = Client()

            response = client.post(
                f"/api/reconciliations/"
                f"{reconciliation.id}/ai-analysis/"
            )

        if response.status_code != 503:
            print("FAIL")
            print(
                f"Expected HTTP 503, got "
                f"{response.status_code}"
            )
            print(response.content.decode())
            return

        data = response.json()

        if (
            data.get("fallback") == "MANUAL_REVIEW"
            and data.get("deterministic_result") == "EXCEPTION"
            and data.get("deterministic_exception")
            == reconciliation.exception_type
        ):
            print("PASS")
            print(
                "Malformed AI response was handled safely."
            )
            print("Fallback: MANUAL_REVIEW")
            print(
                "Deterministic reconciliation "
                "remained unchanged."
            )
        else:
            print("FAIL")
            print(
                "Malformed AI response did not produce "
                "the expected controlled fallback."
            )
            print(f"Response: {data}")

    except Exception as error:
        print("FAIL")
        print(
            f"Malformed AI response test crashed: "
            f"{error}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("========================================")
    print("PHASE 10 — RELIABILITY TESTS")
    print("========================================")

    if not os.path.exists(
        TRANSACTIONS_FILE
    ):

        print(
            "ERROR: transactions.csv not found."
        )

        return

    # Run tests in numerical order.
    test_missing_column()
    test_empty_payment()
    test_invalid_numeric_value()
    test_duplicate_records()
    test_huge_discrepancy()
    test_ai_api_failure()
    test_malformed_ai_response()

    print()
    print("========================================")
    print("RELIABILITY TESTS COMPLETE")
    print("========================================")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()