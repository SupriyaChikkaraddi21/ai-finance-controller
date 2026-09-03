from dataclasses import dataclass, field


@dataclass
class InvestigationState:
    """
    Mutable state for one controller investigation run.

    This state tracks investigation coverage and operational
    progress. It is not a source of financial truth.
    """

    exceptions_available: int = 0

    exceptions_inspected: set = field(
        default_factory=set
    )

    evidence_inspected: set = field(
        default_factory=set
    )

    analyses_inspected: set = field(
        default_factory=set
    )

    analyses_verified: set = field(
        default_factory=set
    )

    risks_assessed: set = field(
        default_factory=set
    )

    # Tracks completed tool actions separately from
    # investigation coverage. This prevents the agent from
    # repeating the exact same investigation action while
    # still allowing different tools on the same exception.
    evidence_calls: set = field(
        default_factory=set
    )
    evidence_complete: set = field(
        default_factory=set
    )

    analysis_calls: set = field(
        default_factory=set
    )

    risk_calls: set = field(
        default_factory=set
    )

    risk_cache: dict = field(
        default_factory=dict
    )
    investigated_exception_types: dict = field(
        default_factory=dict
    )
    def investigation_coverage(self):
        if not self.exceptions_available:
            return 0

        return round(
            len(self.exceptions_inspected)
            / self.exceptions_available
            * 100,
            2,
        )

    def uninspected_exceptions(self):
        return (
            self.exceptions_available
            - len(self.exceptions_inspected)
        )