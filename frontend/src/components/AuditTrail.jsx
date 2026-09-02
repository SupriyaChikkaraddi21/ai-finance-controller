function AuditTrail({
  auditLogs,
  auditLoading,
  auditError,
}) {
  return (
    <section className="section">
      <div className="section-header">
        <div>
          <span className="eyebrow">
            CONTROL AUDIT
          </span>

          <h3>
            Audit Trail
          </h3>
        </div>

        <span className="metric-description">
          Persistent record of reconciliation, AI, and human controller actions
        </span>
      </div>

      <div className="audit-trail">

        {auditLoading && (
          <div className="benchmark-empty">
            Loading audit history...
          </div>
        )}

        {!auditLoading && auditError && (
          <div className="benchmark-empty">
            {auditError}
          </div>
        )}

        {!auditLoading &&
          !auditError &&
          auditLogs.length === 0 && (
            <div className="benchmark-empty">
              No audit events recorded for this batch.
            </div>
          )}

        {!auditLoading &&
          !auditError &&
          auditLogs.map((log) => (
            <div
              className="audit-event"
              key={log.id}
            >
              <div className="audit-event-marker">
                <span />
              </div>

              <div className="audit-event-content">

                <div className="audit-event-header">
                  <strong>
                    {log.action.replaceAll(
                      "_",
                      " "
                    )}
                  </strong>

                  <span>
                    {new Date(
                      log.created_at
                    ).toLocaleString()}
                  </span>
                </div>

                <p>
                  {log.message}
                </p>

                {log.transaction && (
                  <div className="audit-event-meta">
                    Transaction #{log.transaction}
                  </div>
                )}

                {log.metadata &&
                  Object.keys(log.metadata).length > 0 && (
                    <div className="audit-event-metadata">
                      {Object.entries(
                        log.metadata
                      ).map(
                        ([key, value]) => (
                          <span key={key}>
                            <strong>
                              {key.replaceAll(
                                "_",
                                " "
                              )}
                              :
                            </strong>{" "}
                            {String(value)}
                          </span>
                        )
                      )}
                    </div>
                  )}

              </div>
            </div>
          ))}
      </div>
    </section>
  );
}

export default AuditTrail;