from rest_framework import status
from .agent.controller import run_controller_agent
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Batch,
    ReconciliationResult,
    AIAnalysis,
)
from .serializers import (
    BatchSerializer,
    ReconciliationResultSerializer,
    AIAnalysisSerializer,
)
from .reconciliation_service import reconcile_batch
from .ai_analysis_service import (
    analyze_exception,
)



class BatchListCreateView(APIView):

    def get(self, request):
        batches = Batch.objects.all().order_by("-created_at")

        serializer = BatchSerializer(
            batches,
            many=True
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = BatchSerializer(
            data=request.data
        )

        if serializer.is_valid():
            batch = serializer.save()

            return Response(
                BatchSerializer(batch).data,
                status=status.HTTP_201_CREATED
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )


class BatchReconcileView(APIView):

    def post(self, request, batch_id):

        try:
            batch = Batch.objects.get(
                id=batch_id
            )

        except Batch.DoesNotExist:

            return Response(
                {
                    "error": "Batch not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if batch.status == "COMPLETED":

            return Response(
                {
                    "error": "This batch has already been reconciled."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            # ============================================
            # DETERMINISTIC RECONCILIATION ONLY
            # ============================================

            batch = reconcile_batch(
                batch.id
            )

            # ============================================
            # RESPONSE
            # ============================================

            response_data = BatchSerializer(
                batch
            ).data

            return Response(
                response_data,
                status=status.HTTP_200_OK
            )

        except Exception as error:

            batch.status = "FAILED"

            batch.save(
                update_fields=["status"]
            )

            return Response(
                {
                    "error": str(error)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class BatchResultsView(APIView):

    def get(self, request, batch_id):

        results = (
            ReconciliationResult.objects
            .filter(
                transaction__batch_id=batch_id
            )
            .select_related("transaction")
            .order_by(
                "transaction__transaction_id"
            )
        )

        serializer = ReconciliationResultSerializer(
            results,
            many=True
        )

        return Response(serializer.data)


class BatchExceptionsView(APIView):

    def get(self, request, batch_id):

        results = (
            ReconciliationResult.objects
            .filter(
                transaction__batch_id=batch_id,
                result="EXCEPTION",
            )
            .select_related("transaction")
            .order_by(
                "transaction__transaction_id"
            )
        )

        serializer = ReconciliationResultSerializer(
            results,
            many=True
        )

        return Response(serializer.data)


class BatchMetricsView(APIView):

    def get(self, request, batch_id):

        try:
            batch = Batch.objects.get(
                id=batch_id
            )

        except Batch.DoesNotExist:

            return Response(
                {
                    "error": "Batch not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({
            "batch_id": batch.id,
            "batch_name": batch.name,
            "status": batch.status,
            "total_records": batch.total_records,
            "matched_records": batch.matched_records,
            "exception_records": batch.exception_records,
            "match_rate": float(
                batch.match_rate
            ),
            "exception_rate": round(
                (
                    batch.exception_records
                    / batch.total_records
                ) * 100,
                2
            ) if batch.total_records else 0,
            "processing_time_ms": (
                batch.processing_time_ms
            ),
        })


# ==========================================================
# AI EXCEPTION ANALYSIS
# ==========================================================

class AIAnalysisCreateView(APIView):

    def post(self, request, reconciliation_id):

        try:

            reconciliation = (
                ReconciliationResult.objects
                .select_related("transaction")
                .get(
                    id=reconciliation_id
                )
            )

        except ReconciliationResult.DoesNotExist:

            return Response(
                {
                    "error": (
                        "Reconciliation result "
                        "not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # AI is ONLY allowed to analyze exceptions.
        if reconciliation.result != "EXCEPTION":

            return Response(
                {
                    "error": (
                        "AI analysis is only "
                        "available for exceptions."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            analysis = analyze_exception(
                reconciliation.id
            )

            serializer = AIAnalysisSerializer(
                analysis
            )

            return Response(
                serializer.data,
                status=status.HTTP_200_OK
            )

        except Exception as error:

            return Response(
                {
                    "error": "AI analysis unavailable.",
                    "reason": str(error),
                    "fallback": "MANUAL_REVIEW",
                    "deterministic_result": reconciliation.result,
                    "deterministic_exception": (
                        reconciliation.exception_type
                    ),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class AIAnalysisDetailView(APIView):

    def get(self, request, reconciliation_id):

        try:

            analysis = (
                AIAnalysis.objects
                .select_related(
                    "reconciliation",
                    "reconciliation__transaction",
                )
                .get(
                    reconciliation_id=reconciliation_id
                )
            )

        except AIAnalysis.DoesNotExist:

            return Response(
                {
                    "error": (
                        "AI analysis not found."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AIAnalysisSerializer(
            analysis
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )
class FinanceControllerAgentView(APIView):

    def post(self, request, batch_id):

        try:

            batch = Batch.objects.get(
                id=batch_id
            )

        except Batch.DoesNotExist:

            return Response(
                {
                    "error": "Batch not found."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if batch.status != "COMPLETED":

            return Response(
                {
                    "error": (
                        "Batch must be reconciled "
                        "before running the Finance "
                        "Controller Agent."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:

            report = run_controller_agent(
                batch.id
            )

            return Response(
                report,
                status=status.HTTP_200_OK
            )

        except Exception as error:

            return Response(
                {
                    "error": (
                        "Finance Controller Agent "
                        "failed."
                    ),
                    "reason": str(error),
                },
                status=(
                    status.HTTP_503_SERVICE_UNAVAILABLE
                )
            )