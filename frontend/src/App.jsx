import { useState } from "react";
import "./App.css";
import "./styles/financial.css";
import "./styles/exceptions.css";
import "./styles/investigation.css";
import "./styles/benchmark.css";
import "./styles/audit.css";
import "./styles/controller.css";
import FinancialOverview from "./components/FinancialOverview";
import ExceptionDistribution from "./components/ExceptionDistribution";
import InvestigationCoverage from "./components/InvestigationCoverage";
import PerformanceBenchmark from "./components/PerformanceBenchmark";
import ExceptionInvestigation from "./components/ExceptionInvestigation";
import ControllerReview from "./components/ControllerReview";
import AuditTrail from "./components/AuditTrail";
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
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");
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
      setAuditLogs([]);
      setAuditError("");

      const [
        metricsResponse,
        exceptionsResponse,
        auditResponse,
      ] = await Promise.all([
        fetch(`${API}/batches/${batchId}/metrics/`),
        fetch(`${API}/batches/${batchId}/exceptions/`),
        fetch(`${API}/batches/${batchId}/audit-logs/`),
      ]);

      if (
        !metricsResponse.ok ||
        !exceptionsResponse.ok ||
        !auditResponse.ok
      ) {
        throw new Error(
          "Failed to load batch details"
        );
      }

      const metricsData =
        await metricsResponse.json();

      const exceptionsData =
        await exceptionsResponse.json();

      const auditData =
        await auditResponse.json();

      setSelectedBatch(batchId);
      setMetrics(metricsData);
      setExceptions(exceptionsData);
      setAuditLogs(
        Array.isArray(auditData)
          ? auditData
          : []
      );
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

  const resolveException = async (
    reconciliationId,
    resolutionStatus
  ) => {
    try {
      setAiError("");

      const response = await fetch(
        `${API}/reconciliations/${reconciliationId}/resolve/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            resolution_status: resolutionStatus,
            resolved_by: "finance_controller",
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.details ||
            data.error ||
            "Unable to record resolution."
        );
      }

      setSelectedException(data);

      setAiAnalysis(
        data.ai_analysis || null
      );

      setMessage(
        `Exception ${resolutionStatus.toLowerCase()} successfully.`
      );

      await loadBatchDetails(
        selectedBatch.id
      );

    } catch (error) {
      console.error(error);

      setAiError(
        error.message ||
          "Unable to record resolution."
      );
    }
  };
  const exportControllerReport = () => {
    if (!controllerReport) {
      return;
    }

    const report = {
      exported_at: new Date().toISOString(),
      batch_id: selectedBatch,
      batch_metrics: metrics,
      controller_report: controllerReport,
    };

    const blob = new Blob(
      [JSON.stringify(report, null, 2)],
      {
        type: "application/json",
      }
    );

    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;
    link.download =
      `finance-controller-report-batch-${selectedBatch}.json`;

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
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
  const benchmarkBatches =
    batches
      .filter(
        (batch) =>
          batch.status === "COMPLETED" &&
          batch.total_records > 0 &&
          batch.processing_time_ms > 0
      )
      .slice(0, 10)
      .map((batch) => ({
        ...batch,
        throughput: Number(
          (
            batch.total_records /
            (batch.processing_time_ms / 1000)
          ).toFixed(2)
        ),
      }));
  const exceptionCounts =
    exceptions.reduce((acc, item) => {
      const type =
        item.exception_type || "UNKNOWN";

      acc[type] =
        (acc[type] || 0) + 1;

      return acc;
    }, {});
  const exceptionVisualization = Object.entries(
    exceptionCounts
  ).map(([type, count]) => ({
    type,
    count,
    percentage:
      exceptions.length > 0
        ? Number(
            ((count / exceptions.length) * 100).toFixed(1)
          )
        : 0,
  }));

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
            <FinancialOverview
              selectedBatch={selectedBatch}
              totalRecords={totalRecords}
              matchedRecords={matchedRecords}
              exceptionRecords={exceptionRecords}
              matchRate={matchRate}
              exceptionRate={exceptionRate}
              metrics={metrics}
            />
            <ExceptionDistribution
              exceptionRecords={exceptionRecords}
              exceptionVisualization={exceptionVisualization}
            />
            <InvestigationCoverage
              controllerReport={controllerReport}
              exceptionRecords={exceptionRecords}
            />

            <PerformanceBenchmark
              metrics={metrics}
              benchmarkBatches={benchmarkBatches}
            />

            <ControllerReview
              selectedBatch={selectedBatch}
              controllerReport={controllerReport}
              controllerLoading={controllerLoading}
              controllerError={controllerError}
              controllerHighRiskCount={controllerHighRiskCount}
              controllerMediumRiskCount={controllerMediumRiskCount}
              runController={runController}
              exportControllerReport={exportControllerReport}
              renderControllerSummary={renderControllerSummary}
            />

            <AuditTrail
              auditLogs={auditLogs}
              auditLoading={auditLoading}
              auditError={auditError}
            />

            <ExceptionInvestigation
              exceptions={exceptions}
              exceptionCounts={exceptionCounts}
              selectedException={selectedException}
              setSelectedException={setSelectedException}
              setAiAnalysis={setAiAnalysis}
              setAiError={setAiError}
              aiLoading={aiLoading}
              analyzeException={analyzeException}
              aiError={aiError}
              aiAnalysis={aiAnalysis}
              resolveException={resolveException}
            />

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