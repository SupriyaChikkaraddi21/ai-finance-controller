from .tools import (
    get_batch_exceptions,
    get_ai_analysis,
    verify_ai_analysis,
    build_controller_report,
    assess_exception_risk,
)


def build_authoritative_controller_report(
    batch_id,
    inspected_reconciliation_ids,
    investigation,
    final_response,
    tool_trace,
    tool_call_count,
    model_call_count,
    llm_status,
    llm_error,
):
    exceptions = get_batch_exceptions(
        batch_id
    )

    analyses = []
    risk_cache = {}

    for exception in exceptions:
        reconciliation_id = (
            exception[
                "reconciliation_id"
            ]
        )

        risk = assess_exception_risk(
            reconciliation_id
        )

        risk_cache[reconciliation_id] = risk

        if (
            reconciliation_id
            not in inspected_reconciliation_ids
        ):
            continue

        ai_analysis = get_ai_analysis(
            reconciliation_id
        )

        if not ai_analysis["available"]:
            analyses.append(
                {
                    "reconciliation_id": (
                        reconciliation_id
                    ),
                    "transaction_id": (
                        exception[
                            "transaction_id"
                        ]
                    ),
                    "deterministic_exception": (
                        exception[
                            "exception_type"
                        ]
                    ),
                    "classification": None,
                    "confidence": None,
                    "resolution": "MANUAL_REVIEW",
                    "verified": False,
                    "reason": (
                        "AI analysis unavailable. "
                        "Manual review required."
                    ),
                    "risk_level": (
                        risk[
                            "risk_level"
                        ]
                    ),
                    "risk_reasons": (
                        risk[
                            "reasons"
                        ]
                    ),
                }
            )

            continue

        verification = verify_ai_analysis(
            reconciliation_id
        )

        analyses.append(
            {
                "reconciliation_id": (
                    reconciliation_id
                ),
                "transaction_id": (
                    exception[
                        "transaction_id"
                    ]
                ),
                "deterministic_exception": (
                    exception[
                        "exception_type"
                    ]
                ),
                "classification": (
                    ai_analysis[
                        "classification"
                    ]
                ),
                "confidence": (
                    ai_analysis[
                        "confidence"
                    ]
                ),
                "resolution": (
                    verification[
                        "resolution"
                    ]
                ),
                "verified": (
                    verification[
                        "verified"
                    ]
                ),
                "reason": (
                    verification[
                        "reason"
                    ]
                ),
                "risk_level": (
                    risk[
                        "risk_level"
                    ]
                ),
                "risk_reasons": (
                    risk[
                        "reasons"
                    ]
                ),
            }
        )
    exceptions_available = investigation.get(
        "exceptions_available",
        0,
    )

    exceptions_inspected = investigation.get(
        "exceptions_inspected",
        0,
    )

    investigation_coverage = investigation.get(
        "investigation_coverage",
        0,
    )

    uninspected_exceptions = investigation.get(
        "uninspected_exceptions",
        0,
    )

    report = build_controller_report(
        batch_id,
        analyses,
    )

    report["agent"]["exceptions_investigated"] = (
        exceptions_inspected
    )

    report["agent"]["exceptions_analyzed"] = (
        len(analyses)
    )

    confirmed_exceptions = sum(
        1
        for analysis in analyses
        if analysis.get("resolution") == "CONFIRMED"
    )

    investigated_manual_review = sum(
        1
        for analysis in analyses
        if analysis.get("resolution") == "MANUAL_REVIEW"
    )

    manual_review_count = (
        investigated_manual_review
        + uninspected_exceptions
    )

    report["agent"]["confirmed_exceptions"] = (
        confirmed_exceptions
    )

    report["agent"]["manual_review_required"] = (
        manual_review_count
    )

    if uninspected_exceptions > 0:
        report["agent_summary"] = (
            "Investigation was partial. "
            f"{exceptions_inspected} of "
            f"{exceptions_available} exceptions were inspected "
            f"({investigation_coverage}% coverage). "
            f"{uninspected_exceptions} exceptions remain "
            "uninspected. "
            "Manual review is required for the uninspected cases. "
            "Financial truth remains authoritative from the "
            "deterministic reconciliation engine."
        )
    else:
        report["agent_summary"] = (
            "Investigation completed. "
            f"All {exceptions_available} exceptions were inspected "
            f"({investigation_coverage}% coverage). "
            "Final controller decisions are based on the verified "
            "investigation state. "
            "Financial truth remains authoritative from the "
            "deterministic reconciliation engine."
        )

    report["agent_reasoning"] = final_response
    report["final_response"] = final_response
    report["agent_version"] = "v2"
    report["model"] = "gemini-3.5-flash-lite"
    report["llm_status"] = llm_status

    if llm_error is not None:
        report["llm_error"] = llm_error

    report["tool_calls"] = tool_call_count
    report["model_calls"] = model_call_count
    report["tool_trace"] = tool_trace
    report["agent_mode"] = "BATCH_REASONING_CONTROLLER"

    report["investigation"] = investigation

    coverage = investigation.get(
        "investigation_coverage",
        0,
    )

    finalization_decision = investigation.get(
        "finalization_decision"
    )

    if (
        exceptions_available > 0
        and uninspected_exceptions > 0
    ):
        investigation_status = "PARTIAL"
    elif (
        finalization_decision
        == "INVESTIGATION_COMPLETE"
    ):
        investigation_status = "COMPLETE"
    elif (
        finalization_decision
        == "PARTIAL_INVESTIGATION"
    ):
        investigation_status = "PARTIAL"
    else:
        investigation_status = "UNKNOWN"

    report["decision_audit"] = {
        "investigation_status": investigation_status,
        "coverage_percent": coverage,
        "exceptions_available": exceptions_available,
        "exceptions_inspected": exceptions_inspected,
        "uninspected_exceptions": uninspected_exceptions,
        "finalization_decision": finalization_decision,
        "manual_review_required": report[
            "agent"
        ][
            "manual_review_required"
        ],
        "deterministic_truth_source": (
            "reconciliation_engine"
        ),
    }

    population_high_risk = []
    population_medium_risk = []

    for exception in exceptions:
        risk = risk_cache[
            exception["reconciliation_id"]
        ]

        if risk["risk_level"] == "HIGH":
            population_high_risk.append(
                exception["reconciliation_id"]
            )
        elif risk["risk_level"] == "MEDIUM":
            population_medium_risk.append(
                exception["reconciliation_id"]
            )

    report["risk_summary"] = {
        "high_risk_count": len(
            population_high_risk
        ),
        "medium_risk_count": len(
            population_medium_risk
        ),
        "high_risk_reconciliation_ids": (
            population_high_risk
        ),
        "medium_risk_reconciliation_ids": (
            population_medium_risk
        ),
        "source": (
            "deterministic_reconciliation_engine"
        ),
    }

    return report
