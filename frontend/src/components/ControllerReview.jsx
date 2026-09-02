function ControllerReview({
  selectedBatch,
  controllerReport,
  controllerLoading,
  controllerError,
  controllerHighRiskCount,
  controllerMediumRiskCount,
  runController,
  exportControllerReport,
  renderControllerSummary,
}) {
  return (
<section className="section">
  <div className="section-header">

    <div>
      <span className="eyebrow">
        FINANCE CONTROLLER
      </span>

      <h3>
        Controller Review
      </h3>
    </div>

    <div className="controller-actions">

      <button
        className="controller-button"
        onClick={runController}
        disabled={
          controllerLoading ||
          !selectedBatch
        }
      >
        {controllerLoading
          ? "Running Controller..."
          : "Run Finance Controller"}
      </button>

      {controllerReport && (
        <button
          className="controller-button secondary"
          onClick={exportControllerReport}
        >
          Export Controller Report
        </button>
      )}

    </div>

  </div>

  {controllerError && (
    <div className="controller-error">
      <strong>
        Controller Failed
      </strong>

      <p>
        {controllerError}
      </p>
    </div>
  )}

  {controllerReport && (
    <div className="controller-card">
      <div className="controller-safety-banner">
  <strong>CONTROL SAFETY</strong>
  <span>
    Deterministic reconciliation remains the source of truth.
    AI classifies and explains exceptions but cannot modify
    financial results.
  </span>
</div>

      <div className="controller-header">

        <div>
          <span className="eyebrow">
            AGENT REPORT
          </span>

          <h3>
            Finance Controller Result
          </h3>
        </div>

        <span
          className={`controller-status ${
            controllerReport.llm_status ===
            "AVAILABLE"
              ? "available"
              : "unavailable"
          }`}
        >
          LLM{" "}
          {controllerReport.llm_status}
        </span>

      </div>

      <div className="controller-grid">

        <div className="controller-field">
          <span>
            MATCH RATE
          </span>

          <strong>
            {controllerReport.match_rate}%
          </strong>
        </div>

        <div className="controller-field">
          <span>
            TOTAL EXCEPTIONS
          </span>

          <strong>
            {
              controllerReport.investigation
                ?.exceptions_available ?? 0
            }
          </strong>
        </div>

        <div className="controller-field">
          <span>
            CONFIRMED
          </span>

          <strong>
            {
              controllerReport.agent
                ?.confirmed_exceptions ?? 0
            }
          </strong>
        </div>

        <div className="controller-field">
          <span>
            MANUAL REVIEW
          </span>

          <strong>
            {
              controllerReport.agent
                ?.manual_review_required ?? 0
            }
          </strong>
        </div>
        <div className="controller-field">
          <span>
            HIGH RISK
          </span>

          <strong>
            {controllerHighRiskCount}
          </strong>
        </div>
      </div>
      {controllerReport.tool_trace?.length > 0 && (
        <div className="risk-overview">

          <div className="risk-overview-header">
            <div>
              <span className="controller-label">
                RISK OVERVIEW
              </span>

              <h4>
                Investigation Priority
              </h4>
            </div>

            <span className="risk-total">
              {controllerHighRiskCount +
                controllerMediumRiskCount}{" "}
              EXCEPTIONS
            </span>
          </div>

          <div className="risk-grid">

            <div className="risk-card high-risk">
              <span>
                HIGH RISK
              </span>

              <strong>
                {controllerHighRiskCount}
              </strong>

              <p>
                Immediate investigation
              </p>
            </div>

            <div className="risk-card medium-risk">
              <span>
                MEDIUM RISK
              </span>

              <strong>
                {controllerMediumRiskCount}
              </strong>

              <p>
                Additional evidence required
              </p>
            </div>

          </div>

        </div>
      )}
      <div className="controller-details">

        <div>
          <span className="controller-label">
            AGENT MODE
          </span>

          <p>
            {controllerReport.agent_mode ||
              "TOOL_USING_CONTROLLER"}
          </p>
        </div>

        <div>
          <span className="controller-label">
            MODEL
          </span>

          <p>
            {controllerReport.model}
          </p>
        </div>
<div className="controller-summary">
  <span className="controller-label">
    AGENT SUMMARY
  </span>

  <div className="controller-summary-content">
    {renderControllerSummary(
      controllerReport.agent_summary
    )}
  </div>
</div>

      </div>
      {controllerReport.decision_audit && (
        <div className="controller-decision">

          <span className="controller-label">
            CONTROL DECISION
          </span>

          <div className="controller-decision-grid">

            <div>
              <span>INVESTIGATION</span>

              <strong>
                {controllerReport.decision_audit
                  .investigation_status}
              </strong>
            </div>

            <div>
              <span>COVERAGE</span>

              <strong>
                {controllerReport.decision_audit
                  .coverage_percent}%
              </strong>
            </div>

            <div>
              <span>EXCEPTIONS INSPECTED</span>

              <strong>
                {controllerReport.decision_audit
                  .exceptions_inspected}
                {" / "}
                {controllerReport.decision_audit
                  .exceptions_available}
              </strong>
            </div>

            <div>
              <span>UNINSPECTED</span>

              <strong>
                {controllerReport.decision_audit
                  .uninspected_exceptions}
              </strong>
            </div>

            <div>
              <span>FINALIZATION</span>

              <strong>
                {controllerReport.decision_audit
                  .finalization_decision ||
                  "NOT_FINALIZED"}
              </strong>
            </div>

            <div>
              <span>MANUAL REVIEW</span>

              <strong>
                {controllerReport.decision_audit
                  .manual_review_required
                  ? "REQUIRED"
                  : "NOT REQUIRED"}
              </strong>
            </div>

          </div>

          <p className="controller-truth-source">
            Financial truth:
            {" "}
            {controllerReport.decision_audit
              .deterministic_truth_source}
          </p>

        </div>
      )}
      {controllerReport.tool_trace?.length > 0 && (
        <div className="controller-tools">

          <span className="controller-label">
            TOOL TRACE
          </span>

          <ul>
            {controllerReport.tool_trace.map(
              (trace, index) => {

                const type =
                  trace.type || "UNKNOWN";

                return (
                  <li key={index}>
                    {trace.step > 0 && (
                      <>
                        <strong>
                          STEP {trace.step}
                        </strong>

                        {" "}

                        {type === "MODEL_CALL_BUDGET_REACHED" && (
                          <strong>
                            CONTROLLER STOPPED — MODEL CALL BUDGET REACHED
                          </strong>
                        )}
                      </>
                    )}
                    {type === "TOOL_CALL" && (
                      <>
                        <strong>
                          TOOL
                        </strong>

                        {" — "}

                        <strong>
                          {trace.tool}
                        </strong>

                        {" — "}

                        <span>
                          {trace.status}
                        </span>

                        {trace.arguments &&
                          Object.keys(
                            trace.arguments
                          ).length > 0 && (
                            <>
                              {" — "}

                              <span>
                                {JSON.stringify(
                                  trace.arguments
                                )}
                              </span>
                            </>
                          )}
                      </>
                    )}

                    {type === "FINALIZE" && (
                      <>
                        <strong>
                          FINALIZE
                        </strong>

                        {" — "}

                        <span>
                          {trace.decision ||
                            "FINALIZED"}
                        </span>

                        {" — "}

                        <span>
                          {trace.status}
                        </span>

                        {trace.coverage !==
                          undefined && (
                          <>
                            {" — Coverage: "}
                            {trace.coverage}%
                          </>
                        )}
                      </>
                    )}
                    {type === "EXISTING_ANALYSIS_REUSED" && (
                      <>
                        <strong>
                          EXISTING ANALYSIS REUSED
                        </strong>

                        {" — "}

                        <span>
                          RECONCILIATION #
                          {trace.reconciliation_id}
                        </span>

                        {" — "}

                        <span>
                          {trace.analysis?.classification ||
                            "UNKNOWN"}
                        </span>

                        {" — "}

                        <span>
                          {trace.verification?.resolution ||
                            "UNVERIFIED"}
                        </span>

                        {" — "}

                        <span>
                          {trace.risk?.risk_level ||
                            "UNKNOWN"}{" "}
                          RISK
                        </span>

                        {" — "}

                        <span>
                          {trace.status || "UNKNOWN"}
                        </span>
                      </>
                    )}
                    {type === "SAFETY_STOP" && (
                      <>
                        <strong>
                          SAFETY STOP
                        </strong>

                        {" — "}

                        <span>
                          {trace.status}
                        </span>

                        {" — "}

                        <span>
                          {trace.reason}
                        </span>
                      </>
                    )}

                    {type === "MODEL_ERROR" && (
                      <>
                        <strong>
                          MODEL ERROR
                        </strong>

                        {" — "}

                        <span>
                          {trace.error}
                        </span>
                      </>
                    )}

                  </li>
                );
              }
            )}
          </ul>

        </div>
      )}

    </div>
  )}

</section>
  );
}

export default ControllerReview;
