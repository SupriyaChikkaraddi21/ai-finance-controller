function ExceptionDistribution({
  exceptionRecords,
  exceptionVisualization,
}) {
  return (
    <section className="section">

      <div className="section-header">

        <div>

          <span className="eyebrow">
            EXCEPTION ANALYSIS
          </span>

          <h3>
            Exception Distribution
          </h3>

        </div>

        <span className="metric-description">
          {exceptionRecords} exceptions identified by deterministic reconciliation
        </span>

      </div>

      <div className="visualization-card">

        {exceptionVisualization.length > 0 ? (

          exceptionVisualization.map((item) => (

            <div
              className="exception-bar-row"
              key={item.type}
            >

              <div className="exception-bar-label">

                <span>
                  {item.type.replaceAll("_", " ")}
                </span>

                <strong>
                  {item.count} · {item.percentage}%
                </strong>

              </div>

              <div className="exception-bar-track">

                <div
                  className="exception-bar-fill"
                  style={{
                    width: `${item.percentage}%`,
                  }}
                />

              </div>

            </div>

          ))

        ) : (

          <div className="benchmark-empty">
            No exceptions identified in this batch.
          </div>

        )}

      </div>

    </section>
  );
}

export default ExceptionDistribution;