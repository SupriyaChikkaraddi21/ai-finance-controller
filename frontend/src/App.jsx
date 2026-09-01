import { useState } from "react";
import "./App.css";

const API = "/api";
function renderControllerSummary(text) {
  if (!text) return null;

  return text.split("\n").map((line, index) => {
    let clean = line.trim();

    // Remove markdown heading markers
    clean = clean.replace(/^#+\s*/, "");

    // Remove bold / italic markdown
    clean = clean.replace(/\*\*/g, "");
    clean = clean.replace(/\*/g, "");

    // Remove backticks
    clean = clean.replace(/`/g, "");

    // Remove bullet markers
    clean = clean.replace(/^[-•]\s*/, "");

    // Remove numbered-list formatting
    const numberedMatch = clean.match(/^(\d+)\.\s*(.*)$/);

    if (numberedMatch) {
      clean = numberedMatch[2];
    }

    clean = clean.trim();

    // Ignore empty separator lines
    if (!clean || clean === "--") {
      return null;
    }

    // Detect section headings
    const headingWords = [
      "FINANCE CONTROLLER REPORT",
      "Batch Execution Summary",
      "Exception Breakdown & Verification Status",
      "Verification of Existing AI Analyses",
      "Human Finance Controller Investigation Priorities (Risk-Prioritized)",
    ];

    const isHeading = headingWords.some(
      (heading) =>
        clean.toLowerCase() === heading.toLowerCase()
    );

    if (isHeading) {
      return (
        <h4
          key={index}
          className="controller-summary-heading"
        >
          {clean}
        </h4>
      );
    }

    // Numbered priority items
    if (/^\d+\./.test(line.trim())) {
      return (
        <div
          key={index}
          className="controller-summary-bullet"
        >
          <span>•</span>
          <span>{clean}</span>
        </div>
      );
    }

    // Normal bullet / report line
    if (
      line.trim().startsWith("*") ||
      line.trim().startsWith("-") ||
      line.trim().startsWith("•")
    ) {
      return (
        <div
          key={index}
          className="controller-summary-bullet"
        >
          <span>•</span>
          <span>{clean}</span>
        </div>
      );
    }

    return (
      <p
        key={index}
        className="controller-summary-text"
      >
        {clean}
      </p>
    );
  });
}
function App() {
  const [batches, setBatches] = useState([]);
  const [selectedBatch, setSelectedBatch] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [exceptions, setExceptions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const [aiLoading, setAiLoading] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [aiError, setAiError] = useState("");
  const [selectedException, setSelectedException] = useState(null);
  const [controllerReport, setControllerReport] = useState(null);
  const [controllerLoading, setControllerLoading] = useState(false);
  const [controllerError, setControllerError] = useState("");

  const loadBatches = async () => {
    try {
      const response = await fetch(`${API}/batches/`);

      if (!response.ok) {
        throw new Error("Failed to load batches");
      }

      const data = await response.json();

      setBatches(
        Array.isArray(data)
          ? data
          : data.results || []
      );
    } catch (error) {
      console.error(error);
      setMessage("Unable to load batches.");
    }
  };

  const loadBatchDetails = async (batchId) => {
    try {
      setLoading(true);
      setAiAnalysis(null);
      setAiError("");
      setControllerReport(null);
      setControllerError("");

      const [
        metricsResponse,
        exceptionsResponse,
      ] = await Promise.all([
        fetch(`${API}/batches/${batchId}/metrics/`),
        fetch(`${API}/batches/${batchId}/exceptions/`),
      ]);

      if (
        !metricsResponse.ok ||
        !exceptionsResponse.ok
      ) {
        throw new Error(
          "Failed to load batch details"
        );
      }

      const metricsData =
        await metricsResponse.json();

      const exceptionsData =
        await exceptionsResponse.json();

      setSelectedBatch(batchId);
      setMetrics(metricsData);
      setExceptions(exceptionsData);
    } catch (error) {
      console.error(error);
      setMessage(
        "Unable to load batch details."
      );
    } finally {
      setLoading(false);
    }
  };

  const createAndReconcile = async () => {
    try {
      setLoading(true);
      setMessage(
        "Creating reconciliation batch..."
      );

      const createResponse = await fetch(
        `${API}/batches/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name: `Reconciliation Batch ${new Date().toLocaleString()}`,
          }),
        }
      );

      if (!createResponse.ok) {
        throw new Error(
          "Failed to create batch"
        );
      }

      const batch =
  await createResponse.json();

console.log("🔥 CREATED BATCH:", batch);

setMessage(
  "Batch created. Running reconciliation..."
);

console.log(
  "🔥 STARTING RECONCILIATION:",
  `${API}/batches/${batch.id}/reconcile/`
);

const reconcileResponse =
  await fetch(
    `${API}/batches/${batch.id}/reconcile/`,
    {
      method: "POST",
    }
  );

console.log(
  "🔥 RECONCILIATION RESPONSE:",
  reconcileResponse.status
);

      if (!reconcileResponse.ok) {
        throw new Error(
          "Reconciliation failed"
        );
      }

      const completedBatch =
        await reconcileResponse.json();

      setMessage(
        `Reconciliation completed successfully — ${completedBatch.total_records} records processed.`
      );

      await loadBatches();
      await loadBatchDetails(
        completedBatch.id
      );
    } catch (error) {
      console.error(error);
      setMessage(
        "Something went wrong during reconciliation."
      );
    } finally {
      setLoading(false);
    }
  };

  const analyzeException = async (
    reconciliationId
  ) => {
    try {
      setAiLoading(reconciliationId);
      setAiAnalysis(null);
      setAiError("");

      const response = await fetch(
        `${API}/reconciliations/${reconciliationId}/ai-analysis/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 503 && data.error === "AI analysis unavailable.") {
          throw new Error(
            "Gemini API quota has been exhausted. " +
            "Deterministic reconciliation remains authoritative. " +
            "Manual review is required."
          );
        }

        throw new Error(
          data.details ||
            data.error ||
            "AI analysis failed."
        );
      }

      setAiAnalysis(data);

    } catch (error) {
      console.error(error);

      setAiError(
        error.message ||
          "Unable to generate AI analysis."
      );
    } finally {
      setAiLoading(null);
    }
  };
const runController = async () => {
  if (!selectedBatch) {
    return;
  }

  try {
    setControllerLoading(true);
    setControllerError("");
    setControllerReport(null);

    const response = await fetch(
      `${API}/batches/${selectedBatch}/controller/`,
      {
        method: "POST",
      }
    );

    const data = await response.json();
    console.log(
      "CONTROLLER RESPONSE:",
      data
    );

    if (!response.ok) {
      throw new Error(
        data.detail ||
          data.error ||
          "Finance Controller failed."
      );
    }

    setControllerReport(data);

    // ------------------------------------------------
    // REFRESH BATCH DATA AFTER CONTROLLER COMPLETES
    //
    // The Controller may have generated and saved
    // new AIAnalysis records. Reload the exceptions
    // so the UI shows the latest AI state.
    // ------------------------------------------------

    const exceptionsResponse = await fetch(
      `${API}/batches/${selectedBatch}/exceptions/`
    );

    if (!exceptionsResponse.ok) {
      throw new Error(
        "Controller completed, but failed to refresh exceptions."
      );
    }

    const exceptionsData =
      await exceptionsResponse.json();

    setExceptions(exceptionsData);

  } catch (error) {
    console.error(error);

    setControllerError(
      error.message ||
        "Unable to run Finance Controller."
    );

  } finally {
    setControllerLoading(false);
  }
};

  const totalRecords =
    metrics?.total_records ?? 0;

  const matchedRecords =
    metrics?.matched_records ?? 0;

  const exceptionRecords =
    metrics?.exception_records ?? 0;

  const matchRate =
    metrics?.match_rate ?? 0;

  const exceptionRate =
    metrics?.exception_rate ?? 0;

  const controllerHighRiskCount =
    controllerReport?.risk_summary?.high_risk_count ?? 0;

  const controllerMediumRiskCount =
    controllerReport?.risk_summary?.medium_risk_count ?? 0;

  const exceptionCounts =
    exceptions.reduce((acc, item) => {
      const type =
        item.exception_type || "UNKNOWN";

      acc[type] =
        (acc[type] || 0) + 1;

      return acc;
    }, {});

  return (
    <div className="app">

      <header className="topbar">

        <div>
          <div className="brand">

            <span className="brand-icon">
              ₿
            </span>

            <div>
              <h1>
                AI Finance Controller
              </h1>

              <p>
                Automated Payment
                Reconciliation Platform
              </p>
            </div>

          </div>
        </div>

        <button
          className="primary-button"
          onClick={createAndReconcile}
          disabled={loading}
        >
          {loading
            ? "Processing..."
            : "Run Reconciliation"}
        </button>

      </header>

      <main className="container">

        {message && (
          <div className="message">
            {message}
          </div>
        )}

        <section className="hero">

          <div>

            <span className="eyebrow">
              FINANCE OPERATIONS
            </span>

            <h2>
              Reconciliation
              <br />
              Control Center
            </h2>

            <p>
              Detect settlement discrepancies,
              identify financial exceptions,
              and surface transactions
              requiring manual review.
            </p>

          </div>

          <div className="hero-status">

            <div className="status-dot"></div>

            <div>
              <strong>
                System Operational
              </strong>

              <span>
                Django API connected
              </span>
            </div>

          </div>

        </section>

        <section className="section">

          <div className="section-header">

            <div>

              <span className="eyebrow">
                BATCHES
              </span>

              <h3>
                Reconciliation Runs
              </h3>

            </div>

            <span className="batch-count">
              {batches.length} batch
              {batches.length !== 1
                ? "es"
                : ""}
            </span>

          </div>

          <div className="batch-grid">

            {batches.length === 0 ? (

              <div className="empty">

                <h4>
                  No reconciliation batches
                </h4>

                <p>
                  Click "Run Reconciliation"
                  to process the transaction
                  dataset.
                </p>

              </div>

            ) : (

              batches.map((batch) => (

                <button
                  key={batch.id}
                  className={`batch-card ${
                    selectedBatch === batch.id
                      ? "selected"
                      : ""
                  }`}
                  onClick={() =>
                    loadBatchDetails(
                      batch.id
                    )
                  }
                >

                  <div className="batch-card-top">

                    <span className="batch-id">
                      BATCH #{batch.id}
                    </span>

                    <span
                      className={`badge ${
                        batch.status ===
                        "COMPLETED"
                          ? "success"
                          : "processing"
                      }`}
                    >
                      {batch.status}
                    </span>

                  </div>

                  <h4>
                    {batch.name}
                  </h4>

                  <div className="batch-info">

                    <span>
                      <strong>
                        {batch.total_records}
                      </strong>
                      Records
                    </span>

                    <span>
                      <strong>
                        {batch.match_rate}%
                      </strong>
                      Match rate
                    </span>

                    <span>
                      <strong>
                        {batch.processing_time_ms}
                        ms
                      </strong>
                      Processing
                    </span>

                  </div>

                </button>

              ))
            )}

          </div>

        </section>

        {metrics && (
          <>

            <section className="section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    BATCH #{selectedBatch}
                  </span>

                  <h3>
                    Financial Overview
                  </h3>

                </div>

                <span className="completed">
                  ● COMPLETED
                </span>

              </div>

              <div className="metrics-grid">

                <div className="metric-card">

                  <span className="metric-label">
                    TOTAL TRANSACTIONS
                  </span>

                  <strong className="metric-value">
                    {totalRecords}
                  </strong>

                  <span className="metric-description">
                    Transactions processed
                  </span>

                </div>

                <div className="metric-card matched">

                  <span className="metric-label">
                    MATCHED
                  </span>

                  <strong className="metric-value">
                    {matchedRecords}
                  </strong>

                  <span className="metric-description">
                    {matchRate}%
                    successfully
                    reconciled
                  </span>

                </div>

                <div className="metric-card exception">

                  <span className="metric-label">
                    EXCEPTIONS
                  </span>

                  <strong className="metric-value">
                    {exceptionRecords}
                  </strong>

                  <span className="metric-description">
                    {exceptionRate}%
                    require investigation
                  </span>

                </div>

                <div className="metric-card">

                  <span className="metric-label">
                    PROCESSING TIME
                  </span>

                  <strong className="metric-value">
                    {metrics.processing_time_ms}
                    <small> ms</small>
                  </strong>

                  <span className="metric-description">
                    Deterministic
                    reconciliation engine
                  </span>

                </div>

                <div className="metric-card">

                  <span className="metric-label">
                    THROUGHPUT
                  </span>

                  <strong className="metric-value">
                    {metrics.throughput_records_per_sec}
                    <small> records/s</small>
                  </strong>

                  <span className="metric-description">
                    Deterministic
                    reconciliation throughput
                  </span>

                </div>

              </div>

            </section>

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

    {"  "}
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
            <section className="section">

              <div className="section-header">

                <div>

                  <span className="eyebrow">
                    EXCEPTION ANALYSIS
                  </span>

                  <h3>
                    Issues Requiring Attention
                  </h3>

                </div>

              </div>

              <div className="exception-layout">

                <div className="exception-summary">

                  {Object.entries(
                    exceptionCounts
                  ).map(
                    ([type, count]) => (

                      <div
                        className="exception-row"
                        key={type}
                      >

                        <div>

                          <span className="exception-marker"></span>

                          <span className="exception-name">
                            {type.replaceAll(
                              "_",
                              " "
                            )}
                          </span>

                        </div>

                        <strong>
                          {count}
                        </strong>

                      </div>

                    )
                  )}

                </div>

                <div className="exception-table-container">

                  <table>

                    <thead>

                      <tr>

                        <th>
                          TRANSACTION
                        </th>

                        <th>
                          ORDER
                        </th>

                        <th>
                          TYPE
                        </th>

                        <th>
                          DIFFERENCE
                        </th>

                        <th>
                          REVIEW
                        </th>

                        <th>
                          AI
                        </th>

                      </tr>

                    </thead>

                    <tbody>
                      {exceptions.map(
                        (item) => (

                          <tr
                            key={item.id}
                            className={
                              selectedException?.id === item.id
                                ? "exception-row-selected"
                                : ""
                            }
                            onClick={() => {
                              setSelectedException(item);
                              setAiAnalysis(
                                item.ai_analysis || null
                              );
                              setAiError("");
                            }}
                          >

                            <td className="transaction-id">
                              {item.transaction_id}
                            </td>

                            <td>
                              {item.order_id}
                            </td>

                            <td>

                              <span className="exception-badge">
                                {item.exception_type}
                              </span>

                            </td>

                            <td>

                              {item.difference
                                ? `₹${item.difference}`
                                : "—"}

                            </td>

                            <td>

                              {item.requires_manual_review ? (

                                <span className="review">
                                  REVIEW
                                </span>

                              ) : (
                                "—"
                              )}

                            </td>

                            <td>

  {item.ai_analysis ? (

  <button
    className="ai-analyzed-button"
    onClick={(event) => {
      event.stopPropagation();
      setAiAnalysis(item.ai_analysis);
    }}
  >
    ✓ AI ANALYZED
  </button>

) : (

    <button
      className="ai-button"
      onClick={(event) => {
        event.stopPropagation();
        analyzeException(item.id);
      }}
      disabled={
        aiLoading ===
        item.id
      }
    >

      {aiLoading ===
      item.id
        ? "Analyzing..."
        : "✨ Analyze"}

    </button>

  )}

</td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                  {exceptions.length ===
                    0 && (

                    <div className="empty-table">
                      No exceptions found.
                    </div>

                  )}

                </div>

              </div>

            </section>
            {selectedException && (
              <section className="section">

                <div className="investigation-card">

                  <div className="investigation-header">

                    <div>
                      <span className="eyebrow">
                        STEP 1 · DETERMINISTIC INVESTIGATION
                      </span>

                      <h3>
                        {selectedException.transaction_id}
                      </h3>

                      <p className="investigation-subtitle">
                        Financial exception identified by the reconciliation engine.
                      </p>

                      <p>
                        Order {selectedException.order_id}
                      </p>
                    </div>
                    <button
                      className="investigation-close"
                      onClick={() =>
                        setSelectedException(null)
                      }
                    >
                      Close
                    </button>

                  </div>

                  <div className="investigation-grid">

                    <div className="investigation-field">
                      <span>
                        EXCEPTION TYPE
                      </span>

                      <strong>
                        {selectedException.exception_type}
                      </strong>
                    </div>

                    <div className="investigation-field">
                      <span>
                        FINANCIAL DIFFERENCE
                      </span>

                      <strong>
                        {selectedException.difference
                          ? `₹${selectedException.difference}`
                          : "—"}
                      </strong>
                    </div>

                    <div className="investigation-field">
                      <span>
                        MANUAL REVIEW
                      </span>

                      <strong>
                        {selectedException.requires_manual_review
                          ? "REQUIRED"
                          : "NOT REQUIRED"}
                      </strong>
                    </div>

                    <div className="investigation-field">
                      <span>
                        RECONCILIATION ID
                      </span>

                      <strong>
                        {selectedException.id}
                      </strong>
                    </div>

                  </div>
                  <div className="investigation-evidence">

                    <div className="investigation-section-label">
                      DETERMINISTIC EVIDENCE
                    </div>

                    <div className="evidence-grid">

                      <div className="evidence-item">
                        <span>PAYMENT</span>
                        <strong>
                          ₹{selectedException.payment_amount ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>FEE</span>
                        <strong>
                          ₹{selectedException.fee ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>REFUND</span>
                        <strong>
                          ₹{selectedException.refund ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>ADJUSTMENT</span>
                        <strong>
                          ₹{selectedException.adjustment ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>EXPECTED SETTLEMENT</span>
                        <strong>
                          ₹{selectedException.expected_settlement ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>ACTUAL SETTLEMENT</span>
                        <strong>
                          ₹{selectedException.actual_settlement ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>PAYMENT STATUS</span>
                        <strong>
                          {selectedException.payment_status ?? "—"}
                        </strong>
                      </div>

                      <div className="evidence-item">
                        <span>SETTLEMENT STATUS</span>
                        <strong>
                          {selectedException.settlement_status ?? "—"}
                        </strong>
                      </div>

                    </div>

                  </div>
                  <div className="investigation-actions">

                    {selectedException.ai_analysis ? (

                      <button
                        className="ai-analyzed-button"
                        onClick={() =>
                          setAiAnalysis(
                            selectedException.ai_analysis
                          )
                        }
                      >
                        ✓ VIEW AI ANALYSIS
                      </button>

                    ) : (

                      <button
                        className="ai-button"
                        onClick={() =>
                          analyzeException(
                            selectedException.id
                          )
                        }
                        disabled={
                          aiLoading ===
                          selectedException.id
                        }
                      >
                        {aiLoading ===
                        selectedException.id
                          ? "Analyzing..."
                          : "✨ Analyze Exception"}
                      </button>

                    )}

                  </div>

                </div>

              </section>
            )}
            {aiError && (
              <section className="section">

                <div className="ai-error">
                  <strong>
                    AI Analysis Failed
                  </strong>

                  <p>
                    {aiError}
                  </p>

                </div>

              </section>
            )}

            {aiAnalysis && (
              <section className="section">

                <div className="ai-analysis-card">
                  <div className="ai-role-banner">
  <strong>AI EXCEPTION ANALYSIS</strong>

  <span>
    AI explains and classifies deterministic exceptions using
    evidence provided by the reconciliation system.
    It does not calculate or override financial results.
  </span>
</div>

                  <div className="ai-analysis-header">
                    <div>
                      <span className="eyebrow">
                        STEP 2 · AI INTERPRETATION
                      </span>

                      <h3>
                        Evidence-Based Exception Analysis
                      </h3>
                    </div>
                    <span className="ai-model">
                      {aiAnalysis.model_name}
                    </span>

                  </div>

                  <div className="ai-grid">

                    <div className="ai-field">

                      <span>
                        CLASSIFICATION
                      </span>

                      <strong>
                        {aiAnalysis.classification}
                      </strong>

                    </div>

                    <div className="ai-field">

                      <span>
                        CONFIDENCE
                      </span>

                      <strong>
                        {(
                          Number(
                            aiAnalysis.confidence
                          ) * 100
                        ).toFixed(0)}
                        %
                      </strong>

                    </div>

                    <div className="ai-field">

                      <span>
                        FINANCIAL DIFFERENCE
                      </span>

                      <strong>
                        ₹
                        {
                          aiAnalysis
                            .evidence_summary
                            ?.financial_difference ??
                          "—"
                        }
                      </strong>

                    </div>

                    <div className="ai-field">

                      <span>
                        KNOWN CAUSE
                      </span>

                      <strong>
                        {aiAnalysis
                          .evidence_summary
                          ?.known_cause
                          ? "YES"
                          : "NO"}
                      </strong>

                    </div>

                  </div>

                  <div className="ai-content">

                    <div>

                      <span className="ai-label">
                        EXPLANATION
                      </span>

                      <p>
                        {aiAnalysis.explanation}
                      </p>

                    </div>

                    <div>

                      <span className="ai-label">
                        STEP 3 · RECOMMENDED ACTION
                      </span>

                      <p>
                        {
                          aiAnalysis.recommended_action
                        }
                      </p>

                    </div>
                  </div>

                  <div className="ai-footer">
                    Prompt version:{" "}
                    {aiAnalysis.prompt_version}
                  </div>

                </div>

              </section>
            )}

          </>
        )}

        <footer>

          <span>
            AI Finance Controller
          </span>

          <span>
            Deterministic Reconciliation
            Engine • Rule Version v1
          </span>

        </footer>

      </main>

    </div>
  );
}


export default App;