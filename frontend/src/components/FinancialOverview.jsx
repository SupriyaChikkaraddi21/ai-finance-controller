function FinancialOverview({
  selectedBatch,
  totalRecords,
  matchedRecords,
  exceptionRecords,
  matchRate,
  exceptionRate,
  metrics,
}) {
  return (
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
  );
}

export default FinancialOverview;