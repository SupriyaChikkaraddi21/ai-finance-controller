import React from "react";

function ExceptionInvestigation({
  exceptions,
  exceptionCounts,
  selectedException,
  setSelectedException,
  setAiAnalysis,
  setAiError,
  aiLoading,
  analyzeException,
  aiError,
  aiAnalysis,
  resolveException,
}) {
  return (
    <>
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
                  <th>TRANSACTION</th>
                  <th>ORDER</th>
                  <th>TYPE</th>
                  <th>DIFFERENCE</th>
                  <th>REVIEW</th>
                  <th>AI</th>
                </tr>
              </thead>

              <tbody>
                {exceptions.map((item) => (
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
                            setAiAnalysis(
                              item.ai_analysis
                            );
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
                            aiLoading === item.id
                          }
                        >
                          {aiLoading === item.id
                            ? "Analyzing..."
                            : "✨ Analyze"}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {exceptions.length === 0 && (
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
                  Financial exception identified by the
                  reconciliation engine.
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

              <div>
                <span>
                  EXCEPTION TYPE
                </span>
                <strong>
                  {selectedException.exception_type}
                </strong>
              </div>

              <div>
                <span>
                  FINANCIAL DIFFERENCE
                </span>
                <strong>
                  {selectedException.difference
                    ? `₹${selectedException.difference}`
                    : "—"}
                </strong>
              </div>

              <div>
                <span>
                  MANUAL REVIEW
                </span>
                <strong>
                  {selectedException.requires_manual_review
                    ? "REQUIRED"
                    : "NOT REQUIRED"}
                </strong>
              </div>

              <div>
                <span>
                  RECONCILIATION ID
                </span>
                <strong>
                  #{selectedException.id}
                </strong>
              </div>

            </div>

            <div className="investigation-evidence">

              <div className="investigation-section-label">
                DETERMINISTIC EVIDENCE
              </div>

              <div className="evidence-grid">

                <div>
                  <span>PAYMENT</span>
                  <strong>
                    ₹{selectedException.payment_amount}
                  </strong>
                </div>

                <div>
                  <span>FEE</span>
                  <strong>
                    ₹{selectedException.fee}
                  </strong>
                </div>

                <div>
                  <span>REFUND</span>
                  <strong>
                    ₹{selectedException.refund}
                  </strong>
                </div>

                <div>
                  <span>ADJUSTMENT</span>
                  <strong>
                    ₹{selectedException.adjustment}
                  </strong>
                </div>

                <div>
                  <span>EXPECTED SETTLEMENT</span>
                  <strong>
                    ₹{selectedException.expected_settlement}
                  </strong>
                </div>

                <div>
                  <span>ACTUAL SETTLEMENT</span>
                  <strong>
                    ₹{selectedException.actual_settlement}
                  </strong>
                </div>

                <div>
                  <span>PAYMENT STATUS</span>
                  <strong>
                    {selectedException.payment_status}
                  </strong>
                </div>

                <div>
                  <span>SETTLEMENT STATUS</span>
                  <strong>
                    {selectedException.settlement_status}
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
                    aiLoading === selectedException.id
                  }
                >
                  {aiLoading === selectedException.id
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

      {aiAnalysis && selectedException && (
        <section className="section">
          <div className="ai-analysis-card">

            <div className="ai-role-banner">
              <strong>
                AI EXCEPTION ANALYSIS
              </strong>

              <span>
                AI explains and classifies deterministic
                exceptions using evidence provided by the
                reconciliation system.
                It does not calculate or override financial
                results.
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
                  {(() => {
                    const value =
                      aiAnalysis
                        .evidence_summary
                        ?.financial_difference;

                    const isNumeric =
                      value !== null &&
                      value !== undefined &&
                      value !== "" &&
                      value !== "None" &&
                      value !== "N/A" &&
                      /^-?\d+(\.\d+)?$/.test(
                        String(value).trim()
                      );

                    return isNumeric
                      ? `₹${value}`
                      : "—";
                  })()}
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
                  {aiAnalysis.recommended_action}
                </p>
              </div>

            </div>

            <div className="human-resolution">

              <div className="human-resolution-header">

                <div>
                  <span className="ai-label">
                    STEP 4 · HUMAN CONTROLLER DECISION
                  </span>

                  <h3>
                    Review and Resolve Exception
                  </h3>
                </div>

                <span className="resolution-status">
                  STATUS:{" "}
                  {selectedException
                    ?.resolution_status || "PENDING"}
                </span>

              </div>

              <p>
                The controller makes the final decision.
                This does not modify the deterministic
                reconciliation result.
              </p>

              <div className="resolution-actions">

                <button
                  type="button"
                  onClick={() =>
                    resolveException(
                      selectedException.id,
                      "APPROVED"
                    )
                  }
                  disabled={
                    selectedException
                      ?.resolution_status !== "PENDING"
                  }
                >
                  APPROVE
                </button>

                <button
                  type="button"
                  onClick={() =>
                    resolveException(
                      selectedException.id,
                      "REJECTED"
                    )
                  }
                  disabled={
                    selectedException
                      ?.resolution_status !== "PENDING"
                  }
                >
                  REJECT
                </button>

                <button
                  type="button"
                  onClick={() =>
                    resolveException(
                      selectedException.id,
                      "ESCALATED"
                    )
                  }
                  disabled={
                    selectedException
                      ?.resolution_status !== "PENDING"
                  }
                >
                  ESCALATE
                </button>

              </div>

              {selectedException?.resolved_by && (
                <div className="resolution-meta">
                  Resolved by{" "}
                  <strong>
                    {selectedException.resolved_by}
                  </strong>
                  {" · "}
                  {new Date(
                    selectedException.resolved_at
                  ).toLocaleString()}
                </div>
              )}

            </div>

            <div className="ai-footer">
              Prompt version:{" "}
              {aiAnalysis.prompt_version}
            </div>

          </div>
        </section>
      )}
    </>
  );
}

export default ExceptionInvestigation;
