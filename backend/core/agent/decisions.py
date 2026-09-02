from .tools import inspect_investigation_scope as get_investigation_scope


def get_required_investigation_ids(
    batch_id
):
    scope = get_investigation_scope(
        batch_id
    )

    # The controller has a bounded step budget.
    # Require investigation of only the highest-priority
    # unresolved deterministic exceptions.

    candidates = list(
        scope.get(
            "exceptions",
            []
        )
    )

    candidates.sort(
        key=lambda item: (
            -item.get(
                "priority_score",
                0,
            ),
            item["reconciliation_id"],
        )
    )

    # Require investigation of the bounded deterministic
    # exception population selected for this controller run.
    # The full population remains available for deterministic
    # risk reporting; this set controls the investigation gate.
    MAX_REQUIRED_INVESTIGATIONS = 25

    return {
        item["reconciliation_id"]
        for item in candidates[
            :MAX_REQUIRED_INVESTIGATIONS
        ]
    }
