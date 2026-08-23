import json
import os
import sys
from collections import Counter

import django


# ============================================================
# DJANGO SETUP
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

BACKEND_DIR = os.path.join(
    BASE_DIR,
    "backend",
)

sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings",
)
from django.conf import settings

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")
django.setup()


# ============================================================
# IMPORT AFTER DJANGO SETUP
# ============================================================

from core.models import (
    Batch,
    ReconciliationResult,
    AIAnalysis,
)


# ============================================================
# CONFIGURATION
# ============================================================

BATCH_ID = int(
    sys.argv[1]
) if len(sys.argv) > 1 else 2

OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "data",
    "ai_evaluation_results.json",
)


# ============================================================
# EXPECTED AI CLASSIFICATION
# ============================================================

EXPECTED_AI_CLASSIFICATION = {
    "DUPLICATE": "DUPLICATE",
    "MISSING_PAYMENT": "MISSING_RECORD",
    "MISSING_SETTLEMENT": "MISSING_RECORD",
    "STATUS_MISMATCH": "STATUS_ISSUE",
    "AMOUNT_MISMATCH": "AMOUNT_DISCREPANCY",
    "UNKNOWN": "UNKNOWN",
}


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("========================================")
    print("AI EXCEPTION EVALUATION")
    print("========================================")

    # --------------------------------------------------------
    # Validate batch
    # --------------------------------------------------------

    try:

        batch = Batch.objects.get(
            id=BATCH_ID
        )

    except Batch.DoesNotExist:

        print(
            f"ERROR: Batch {BATCH_ID} does not exist."
        )

        return

    print(
        f"Batch ID      : {batch.id}"
    )

    print(
        f"Batch name    : {batch.name}"
    )

    # --------------------------------------------------------
    # Load deterministic exceptions
    # --------------------------------------------------------

    exceptions = list(
        ReconciliationResult.objects
        .filter(
            transaction__batch_id=BATCH_ID,
            result="EXCEPTION",
        )
        .select_related("transaction")
        .order_by(
            "transaction__transaction_id"
        )
    )

    total_exceptions = len(
        exceptions
    )

    print(
        f"Exceptions    : {total_exceptions}"
    )

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    evaluated = 0
    unevaluated = 0

    valid_responses = 0
    invalid_responses = 0

    correct_classifications = 0
    incorrect_classifications = 0

    unknown_count = 0

    confidence_values = []

    classification_distribution = Counter()
    ai_y_true = []
    ai_y_pred = []

    failures = []
    records = []

    # ========================================================
    # EVALUATE PERSISTED AI ANALYSES
    # ========================================================

    for index, reconciliation in enumerate(
        exceptions,
        start=1,
    ):

        transaction_id = (
            reconciliation.transaction.transaction_id
        )

        deterministic_exception = (
            reconciliation.exception_type
        )

        expected_ai_classification = (
            EXPECTED_AI_CLASSIFICATION.get(
                deterministic_exception
            )
        )

        print()
        print(
            f"[{index}/{total_exceptions}] "
            f"{transaction_id}"
        )

        print(
            f"Deterministic exception: "
            f"{deterministic_exception}"
        )

        print(
            f"Expected AI class: "
            f"{expected_ai_classification}"
        )

        # ----------------------------------------------------
        # Find existing AI analysis
        # ----------------------------------------------------

        try:

            analysis = AIAnalysis.objects.get(
                reconciliation_id=reconciliation.id
            )

        except AIAnalysis.DoesNotExist:

            unevaluated += 1

            print(
                "AI analysis: NOT AVAILABLE"
            )

            records.append(
                {
                    "reconciliation_id": (
                        reconciliation.id
                    ),
                    "transaction_id": (
                        transaction_id
                    ),
                    "deterministic_exception": (
                        deterministic_exception
                    ),
                    "expected_ai_classification": (
                        expected_ai_classification
                    ),
                    "actual_ai_classification": None,
                    "classification_status": (
                        "NOT_EVALUATED"
                    ),
                    "confidence": None,
                    "model_name": None,
                    "prompt_version": None,
                }
            )

            continue

        # ----------------------------------------------------
        # Validate persisted response
        # ----------------------------------------------------

        actual_classification = (
            analysis.classification
        )

        confidence = (
            float(analysis.confidence)
            if analysis.confidence is not None
            else None
        )

        valid_classification = (
            actual_classification
            in {
                "PROCESSING_FEE",
                "REFUND",
                "DUPLICATE",
                "STATUS_ISSUE",
                "MISSING_RECORD",
                "AMOUNT_DISCREPANCY",
                "UNKNOWN",
            }
        )

        valid_confidence = (
            confidence is not None
            and 0 <= confidence <= 1
        )

        if not valid_classification:
            valid_responses += 0
            invalid_responses += 1

            classification_status = (
                "INVALID_RESPONSE"
            )

            failures.append(
                {
                    "reconciliation_id": (
                        reconciliation.id
                    ),
                    "transaction_id": (
                        transaction_id
                    ),
                    "error": (
                        "Invalid AI classification."
                    ),
                }
            )

        elif not valid_confidence:
            valid_responses += 0
            invalid_responses += 1

            classification_status = (
                "INVALID_RESPONSE"
            )

            failures.append(
                {
                    "reconciliation_id": (
                        reconciliation.id
                    ),
                    "transaction_id": (
                        transaction_id
                    ),
                    "error": (
                        "Invalid AI confidence."
                    ),
                }
            )

        else:

            valid_responses += 1
            evaluated += 1

            classification_distribution[
                actual_classification
            ] += 1
            ai_y_true.append(
                expected_ai_classification
                )

            ai_y_pred.append(
                actual_classification
                )

            confidence_values.append(
                confidence
            )

            if (
                actual_classification
                == expected_ai_classification
            ):

                correct_classifications += 1

                classification_status = (
                    "CORRECT"
                )

            else:

                incorrect_classifications += 1

                classification_status = (
                    "WRONG"
                )

            if actual_classification == "UNKNOWN":
                unknown_count += 1

        print(
            f"Actual AI class: "
            f"{actual_classification}"
        )

        print(
            f"Confidence: "
            f"{confidence}"
        )

        print(
            f"Evaluation: "
            f"{classification_status}"
        )

        records.append(
            {
                "reconciliation_id": (
                    reconciliation.id
                ),
                "transaction_id": (
                    transaction_id
                ),
                "deterministic_exception": (
                    deterministic_exception
                ),
                "expected_ai_classification": (
                    expected_ai_classification
                ),
                "actual_ai_classification": (
                    actual_classification
                ),
                "classification_status": (
                    classification_status
                ),
                "confidence": confidence,
                "model_name": (
                    analysis.model_name
                ),
                "prompt_version": (
                    analysis.prompt_version
                ),
            }
        )

    # ========================================================
    # METRICS
    # ========================================================

    classification_accuracy = (
        (
            correct_classifications
            / evaluated
        ) * 100
        if evaluated
        else 0
    )

    average_confidence = (
        sum(confidence_values)
        / len(confidence_values)
        if confidence_values
        else 0
    )

    evaluation_coverage = (
        (
            evaluated
            / total_exceptions
        ) * 100
        if total_exceptions
        else 0
    )
    # ========================================================
    # AI CONFUSION MATRIX + PER-CLASS METRICS
    # ========================================================

    ai_labels = sorted(
        set(ai_y_true) | set(ai_y_pred)
    )

    ai_confusion = {
        true_label: {
            pred_label: 0
            for pred_label in ai_labels
        }
        for true_label in ai_labels
    }

    for true_label, pred_label in zip(
        ai_y_true,
        ai_y_pred,
    ):
        ai_confusion[
            true_label
        ][pred_label] += 1

    ai_metrics = {}

    for label in ai_labels:

        tp = sum(
            1
            for true_label, pred_label
            in zip(ai_y_true, ai_y_pred)
            if true_label == label
            and pred_label == label
        )

        fp = sum(
            1
            for true_label, pred_label
            in zip(ai_y_true, ai_y_pred)
            if true_label != label
            and pred_label == label
        )

        fn = sum(
            1
            for true_label, pred_label
            in zip(ai_y_true, ai_y_pred)
            if true_label == label
            and pred_label != label
        )

        support = sum(
            1
            for true_label in ai_y_true
            if true_label == label
        )

        precision = (
            tp / (tp + fp)
            if tp + fp
            else 0
        )

        recall = (
            tp / (tp + fn)
            if tp + fn
            else 0
        )

        f1 = (
            2 * precision * recall
            / (precision + recall)
            if precision + recall
            else 0
        )

        ai_metrics[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": support,
        }
    # ========================================================
    # PRINT SUMMARY
    # ========================================================
    print()
    print("AI CONFUSION MATRIX")
    print("----------------------------------------")

    header = "Actual \\ Predicted".ljust(25)

    for label in ai_labels:
        header += label.ljust(22)

    print(header)

    for true_label in ai_labels:

        row = true_label.ljust(25)

        for pred_label in ai_labels:
            row += str(
                ai_confusion[
                    true_label
                ][pred_label]
            ).ljust(22)

        print(row)

    print()
    print("AI PER-CLASS METRICS")
    print("----------------------------------------")

    print(
        f"{'Class':25}"
        f"{'Precision':12}"
        f"{'Recall':12}"
        f"{'F1':12}"
        f"{'Support':10}"
    )

    for label, values in ai_metrics.items():

        print(
            f"{label:25}"
            f"{values['precision'] * 100:10.2f}% "
            f"{values['recall'] * 100:10.2f}% "
            f"{values['f1'] * 100:10.2f}% "
            f"{values['support']:8}"
        )
    print()
    print("========================================")
    print("AI EVALUATION SUMMARY")
    print("========================================")

    print(
        f"Total exceptions       : "
        f"{total_exceptions}"
    )

    print(
        f"Evaluated analyses     : "
        f"{evaluated}"
    )

    print(
        f"Unevaluated exceptions : "
        f"{unevaluated}"
    )

    print(
        f"Evaluation coverage    : "
        f"{evaluation_coverage:.2f}%"
    )

    print(
        f"Valid responses        : "
        f"{valid_responses}"
    )

    print(
        f"Invalid responses      : "
        f"{invalid_responses}"
    )

    print(
        f"Correct classifications: "
        f"{correct_classifications}"
    )

    print(
        f"Wrong classifications  : "
        f"{incorrect_classifications}"
    )

    print(
        f"Classification accuracy: "
        f"{classification_accuracy:.2f}%"
    )

    print(
        f"UNKNOWN classifications: "
        f"{unknown_count}"
    )

    print(
        f"Average confidence     : "
        f"{average_confidence:.2f}"
    )

    print()
    print("CLASSIFICATION DISTRIBUTION")
    print("----------------------------------------")

    for classification, count in sorted(
        classification_distribution.items()
    ):

        print(
            f"{classification:25}"
            f"{count:5}"
        )

    # ========================================================
    # SAVE REPORT
    # ========================================================

    report = {

        "evaluation_type": (
            "Evaluation of persisted AI exception "
            "analysis outputs against predefined "
            "classification mapping"
        ),

        "evaluation_method": (
            "Persisted AIAnalysis records were evaluated. "
            "Gemini was NOT called during evaluation."
        ),

        "batch": {
            "id": batch.id,
            "name": batch.name,
        },

        "dataset": {
            "total_exceptions": total_exceptions,
            "evaluated_exceptions": evaluated,
            "unevaluated_exceptions": unevaluated,
            "evaluation_coverage": round(
                evaluation_coverage,
                2,
            ),
        },

        "overall": {
            "valid_responses": valid_responses,
            "invalid_responses": invalid_responses,
            "correct_classifications": (
                correct_classifications
            ),
            "wrong_classifications": (
                incorrect_classifications
            ),
            "classification_accuracy": round(
                classification_accuracy,
                2,
            ),
            "unknown_count": unknown_count,
            "average_confidence": round(
                average_confidence,
                4,
            ),
            "per_class_metrics":ai_metrics,

            "confusion_matrix":ai_confusion,

        },

        "expected_classification_mapping": (
            EXPECTED_AI_CLASSIFICATION
        ),

        "classification_distribution": dict(
            classification_distribution
        ),

        "records": records,

        "failures": failures,
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
        )

    print()
    print(
        "AI evaluation report saved to:"
    )

    print(
        OUTPUT_FILE
    )

    print()
    print("========================================")
    print("AI EVALUATION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()