function InvestigationCoverage({
  controllerReport,
  exceptionRecords,
}) {
  return (
    <section className="section">

      <div className="section-header">

        <div>

          <span className="eyebrow">
            INVESTIGATION COVERAGE
          </span>

          <h3>
            Controller Investigation Coverage
          </h3>

        </div>

        <span className="metric-description">
          AI investigation progress for the selected batch
        </span>

      </div>

      <div className="coverage-visualization">

        <div className="coverage-stat">

          <strong>
            {controllerReport?.investigation?.exceptions_inspected ?? 0}
          </strong>

          <span>
            Inspected
          </span>

        </div>

        <div className="coverage-stat">

          <strong>
            {controllerReport?.investigation?.uninspected_exceptions ??
              exceptionRecords}
          </strong>

          <span>
            Uninspected
          </span>

        </div>

        <div className="coverage-stat">

          <strong>
            {controllerReport?.investigation?.investigation_coverage ?? 0}%
          </strong>

          <span>
            Coverage
          </span>

        </div>

      </div>

      <div className="coverage-bar-track">

        <div
          className="coverage-bar-fill"
          style={{
            width: `${
              controllerReport?.investigation?.investigation_coverage ?? 0
            }%`,
          }}
        />

      </div>

      <p className="metric-description">
        Coverage reflects exceptions actually investigated by the
        controller, not merely exceptions detected by reconciliation.
      </p>

    </section>
  );
}

export default InvestigationCoverage;