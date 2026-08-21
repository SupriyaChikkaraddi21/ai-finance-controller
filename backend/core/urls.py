from django.urls import path

from .views import (
    BatchListCreateView,
    BatchReconcileView,
    BatchResultsView,
    BatchExceptionsView,
    BatchMetricsView,
    AIAnalysisCreateView,
    AIAnalysisDetailView,
)


urlpatterns = [

    # ------------------------------------------------------
    # BATCH
    # ------------------------------------------------------

    path(
        "batches/",
        BatchListCreateView.as_view(),
        name="batch-list-create",
    ),

    path(
        "batches/<int:batch_id>/reconcile/",
        BatchReconcileView.as_view(),
        name="batch-reconcile",
    ),

    path(
        "batches/<int:batch_id>/results/",
        BatchResultsView.as_view(),
        name="batch-results",
    ),

    path(
        "batches/<int:batch_id>/exceptions/",
        BatchExceptionsView.as_view(),
        name="batch-exceptions",
    ),

    path(
        "batches/<int:batch_id>/metrics/",
        BatchMetricsView.as_view(),
        name="batch-metrics",
    ),

    # ------------------------------------------------------
    # AI EXCEPTION ANALYSIS
    # ------------------------------------------------------

    path(
        "reconciliations/<int:reconciliation_id>/ai-analysis/",
        AIAnalysisCreateView.as_view(),
        name="ai-analysis-create",
    ),

    path(
        "reconciliations/<int:reconciliation_id>/ai-analysis/detail/",
        AIAnalysisDetailView.as_view(),
        name="ai-analysis-detail",
    ),
]