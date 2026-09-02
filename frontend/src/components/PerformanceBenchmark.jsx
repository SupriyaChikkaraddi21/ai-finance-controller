function PerformanceBenchmark({
  metrics,
  benchmarkBatches,
}) {
  return (
    <section className="section">

      <div className="section-header">

        <div>

          <span className="eyebrow">
            ENGINE PERFORMANCE
          </span>

          <h3>
            Performance Benchmark
          </h3>

        </div>

        <span className="completed">
          ● DETERMINISTIC ENGINE
        </span>

      </div>

      <div className="metrics-grid">

        <div className="metric-card">

          <span className="metric-label">
            RECORDS PROCESSED
          </span>

          <strong className="metric-value">
            {metrics.total_records}
          </strong>

          <span className="metric-description">
            Transactions in this benchmark batch
          </span>

        </div>

        <div className="metric-card matched">

          <span className="metric-label">
            MATCH RATE
          </span>

          <strong className="metric-value">
            {metrics.match_rate}%
          </strong>

          <span className="metric-description">
            Deterministic reconciliation accuracy
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
            End-to-end local reconciliation runtime
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
            Records reconciled per second
          </span>

        </div>

      </div>

      <div className="benchmark-comparison">

        <div className="section-header">

          <div>

            <span className="eyebrow">
              RECENT BATCHES
            </span>

            <h3>
              Benchmark Comparison
            </h3>

          </div>

          <span className="metric-description">
            Latest 10 completed batches
          </span>

        </div>

        <div className="benchmark-table">

          <div className="benchmark-row benchmark-header">

            <span>BATCH</span>
            <span>RECORDS</span>
            <span>PROCESSING</span>
            <span>THROUGHPUT</span>
            <span>MATCH RATE</span>

          </div>

          {benchmarkBatches.length > 0 ? (

            benchmarkBatches.map((batch) => (

              <div
                className="benchmark-row"
                key={batch.id}
              >

                <span>
                  <strong>
                    #{batch.id}
                  </strong>
                  {" "}
                  {batch.name}
                </span>

                <span>
                  {batch.total_records}
                </span>

                <span>
                  {batch.processing_time_ms} ms
                </span>

                <span>
                  {batch.throughput} records/s
                </span>

                <span>
                  {batch.match_rate}%
                </span>

              </div>

            ))

          ) : (

            <div className="benchmark-empty">
              No completed benchmark batches available.
            </div>

          )}

        </div>

      </div>

      <div className="controller-safety-banner">

        <strong>
          BENCHMARK SCOPE
        </strong>

        <span>
          Measures the deterministic reconciliation engine
          on the selected batch. AI investigation latency
          is not included in this benchmark.
        </span>

      </div>

    </section>
  );
}

export default PerformanceBenchmark;