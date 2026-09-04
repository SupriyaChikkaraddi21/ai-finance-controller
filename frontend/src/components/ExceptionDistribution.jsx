function ExceptionDistribution({
  exceptionRecords,
  exceptionVisualization,
  selectedExceptionType,
  setSelectedExceptionType,
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

          exceptionVisualization.map((item) => {

            const isSelected = selectedExceptionType === item.type;

            return (
              <div
                className={`exception-bar-row ${
                  isSelected ? "exception-bar-row-selected" : ""
                }`}
                key={item.type}
                onClick={() =>
                  setSelectedExceptionType(
                    isSelected ? null : item.type
                  )
                }
                style={{ cursor: "pointer" }}
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
            );
          })

        ) : (

          <div className="benchmark-empty">
            No exceptions identified in this batch.
          </div>

        )}

      </div>

      {selectedExceptionType && (
        <div className="metric-description" style={{ marginTop: "12px" }}>
          Showing: {selectedExceptionType.replaceAll("_", " ")} · Click again to clear
        </div>
      )}

    </section>
  );
}

export default ExceptionDistribution;