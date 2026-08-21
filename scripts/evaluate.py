import csv
import json
import os
from collections import Counter, defaultdict


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

GROUND_TRUTH_FILE = os.path.join(
    BASE_DIR,
    "data",
    "ground_truth.csv",
)

RESULTS_FILE = os.path.join(
    BASE_DIR,
    "data",
    "reconciliation_results.csv",
)

EVALUATION_FILE = os.path.join(
    BASE_DIR,
    "data",
    "evaluation_results.json",
)


def load_csv(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def calculate_metrics(y_true, y_pred):
    labels = sorted(
        set(y_true) | set(y_pred)
    )

    metrics = {}

    for label in labels:

        tp = sum(
            1
            for true, pred in zip(y_true, y_pred)
            if true == label and pred == label
        )

        fp = sum(
            1
            for true, pred in zip(y_true, y_pred)
            if true != label and pred == label
        )

        fn = sum(
            1
            for true, pred in zip(y_true, y_pred)
            if true == label and pred != label
        )

        support = sum(
            1
            for true in y_true
            if true == label
        )

        precision = (
            tp / (tp + fp)
            if (tp + fp)
            else 0
        )

        recall = (
            tp / (tp + fn)
            if (tp + fn)
            else 0
        )

        f1 = (
            2 * precision * recall
            / (precision + recall)
            if (precision + recall)
            else 0
        )

        metrics[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": support,
        }

    return metrics


def main():

    print()
    print("========================================")
    print("RECONCILIATION EVALUATION")
    print("========================================")

    ground_truth = load_csv(
        GROUND_TRUTH_FILE
    )

    results = load_csv(
        RESULTS_FILE
    )

    truth_by_id = {
        row["transaction_id"]: row
        for row in ground_truth
    }

    results_by_id = {
        row["transaction_id"]: row
        for row in results
    }

    y_true = []
    y_pred = []

    missing_results = []

    for transaction_id, truth in truth_by_id.items():

        result = results_by_id.get(
            transaction_id
        )

        if result is None:
            missing_results.append(
                transaction_id
            )
            continue

        expected_result = truth[
            "expected_result"
        ]

        actual_result = result[
            "result"
        ]

        expected_exception = truth[
            "exception_type"
        ]

        actual_exception = result[
            "exception_type"
        ]

        if expected_result == "MATCHED":
            true_label = "MATCHED"
        else:
            true_label = (
                expected_exception
                or "EXCEPTION"
            )

        if actual_result == "MATCHED":
            predicted_label = "MATCHED"
        else:
            predicted_label = (
                actual_exception
                or "EXCEPTION"
            )

        y_true.append(true_label)
        y_pred.append(predicted_label)

    total = len(y_true)

    correct = sum(
        true == pred
        for true, pred in zip(
            y_true,
            y_pred,
        )
    )

    wrong = total - correct

    accuracy = (
        correct / total * 100
        if total
        else 0
    )

    # --------------------------------------------------
    # Confusion matrix
    # --------------------------------------------------

    labels = sorted(
        set(y_true) | set(y_pred)
    )

    confusion = defaultdict(
        lambda: Counter()
    )

    for true, pred in zip(
        y_true,
        y_pred,
    ):
        confusion[true][pred] += 1

    confusion_matrix = {}

    for true_label in labels:

        confusion_matrix[true_label] = {}

        for pred_label in labels:

            confusion_matrix[true_label][
                pred_label
            ] = confusion[true_label][
                pred_label
            ]

    # --------------------------------------------------
    # Per-class metrics
    # --------------------------------------------------

    metrics = calculate_metrics(
        y_true,
        y_pred,
    )

    # --------------------------------------------------
    # Exception distribution
    # --------------------------------------------------

    exception_counts = Counter(
        label
        for label in y_true
        if label != "MATCHED"
    )

    exception_distribution = {}

    for label, count in sorted(
        exception_counts.items()
    ):

        percentage = (
            count / total * 100
            if total
            else 0
        )

        exception_distribution[label] = {
            "count": count,
            "percentage": round(
                percentage,
                2,
            ),
        }

    # --------------------------------------------------
    # Batch metrics
    # --------------------------------------------------

    matched = sum(
        1
        for label in y_true
        if label == "MATCHED"
    )

    exceptions = total - matched

    match_rate = (
        matched / total * 100
        if total
        else 0
    )

    exception_rate = (
        exceptions / total * 100
        if total
        else 0
    )

    # --------------------------------------------------
    # Evaluation report
    # --------------------------------------------------

    evaluation = {
        "evaluation_type": (
            "Deterministic reconciliation "
            "against synthetic ground truth"
        ),
        "dataset": {
            "total_records": total,
            "ground_truth_records": len(
                ground_truth
            ),
            "result_records": len(
                results
            ),
        },
        "overall": {
            "correct": correct,
            "wrong": wrong,
            "accuracy": round(
                accuracy,
                2,
            ),
        },
        "batch_metrics": {
            "total_records": total,
            "matched_records": matched,
            "exception_records": exceptions,
            "match_rate": round(
                match_rate,
                2,
            ),
            "exception_rate": round(
                exception_rate,
                2,
            ),
        },
        "per_class_metrics": metrics,
        "confusion_matrix": confusion_matrix,
        "exception_distribution": (
            exception_distribution
        ),
        "missing_results": missing_results,
    }

    # --------------------------------------------------
    # Save JSON
    # --------------------------------------------------

    with open(
        EVALUATION_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            evaluation,
            file,
            indent=4,
        )

    # --------------------------------------------------
    # Console output
    # --------------------------------------------------

    print()
    print("OVERALL")
    print("----------------------------------------")
    print(f"Total records : {total}")
    print(f"Correct       : {correct}")
    print(f"Wrong         : {wrong}")
    print(f"Accuracy      : {accuracy:.2f}%")

    if missing_results:
        print()
        print(
            "Missing results:",
            len(missing_results),
        )

    print()
    print("CONFUSION MATRIX")
    print("----------------------------------------")

    header = "Actual \\ Predicted".ljust(25)

    for label in labels:
        header += label.ljust(22)

    print(header)

    for true_label in labels:

        row = true_label.ljust(25)

        for pred_label in labels:

            row += str(
                confusion_matrix[
                    true_label
                ][pred_label]
            ).ljust(22)

        print(row)

    print()
    print("PER-CLASS METRICS")
    print("----------------------------------------")

    print(
        f"{'Class':25}"
        f"{'Precision':12}"
        f"{'Recall':12}"
        f"{'F1':12}"
        f"{'Support':10}"
    )

    for label, values in metrics.items():

        print(
            f"{label:25}"
            f"{values['precision'] * 100:10.2f}% "
            f"{values['recall'] * 100:10.2f}% "
            f"{values['f1'] * 100:10.2f}% "
            f"{values['support']:8}"
        )

    print()
    print("GROUND-TRUTH EXCEPTION DISTRIBUTION")
    print("----------------------------------------")

    for label, values in (
        exception_distribution.items()
    ):

        print(
            f"{label:25}"
            f"{values['count']:3} "
            f"({values['percentage']:.2f}%)"
        )

    print()
    print("BATCH METRICS")
    print("----------------------------------------")
    print(f"Total records   : {total}")
    print(f"Matched         : {matched}")
    print(f"Exceptions      : {exceptions}")
    print(f"Match rate      : {match_rate:.2f}%")
    print(
        f"Exception rate  : {exception_rate:.2f}%"
    )

    print()
    print("Evaluation report saved to:")
    print(EVALUATION_FILE)

    print()
    print("========================================")
    print("EVALUATION COMPLETE")
    print("========================================")


if __name__ == "__main__":
    main()