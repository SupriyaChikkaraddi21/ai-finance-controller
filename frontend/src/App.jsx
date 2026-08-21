import { useEffect, useState } from "react";
import "./App.css";

const API = "/api";

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

      setMessage(
        "Batch created. Running reconciliation..."
      );

      const reconcileResponse =
        await fetch(
          `${API}/batches/${batch.id}/reconcile/`,
          {
            method: "POST",
          }
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

  useEffect(() => {
    loadBatches();
  }, []);

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

              </div>

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

                          <tr key={item.id}>

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

                              <button
                                className="ai-button"
                                onClick={() =>
                                  analyzeException(
                                    item.id
                                  )
                                }
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

                  <div className="ai-analysis-header">

                    <div>
                      <span className="eyebrow">
                        GEMINI AI
                      </span>

                      <h3>
                        Exception Analysis
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
                        RECOMMENDED ACTION
                      </span>

                      <p>
                        {
                          aiAnalysis.recommended_action
                        }
                      </p>

                    </div>

                    <div>

                      <span className="ai-label">
                        EVIDENCE
                      </span>

                      <ul>

                        {(
                          aiAnalysis
                            .evidence_summary
                            ?.key_facts ||
                          []
                        ).map(
                          (fact, index) => (
                            <li key={index}>
                              {fact}
                            </li>
                          )
                        )}

                      </ul>

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