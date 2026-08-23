from rest_framework import serializers

from .models import (
    Batch,
    Transaction,
    ReconciliationResult,
    AIAnalysis,
    AuditLog,
)


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = [
            "id",
            "name",
            "total_records",
            "matched_records",
            "exception_records",
            "match_rate",
            "processing_time_ms",
            "status",
            "created_at",
            "completed_at",
        ]


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = [
            "id",
            "transaction_id",
            "order_id",
            "payment_amount",
            "fee",
            "refund",
            "adjustment",
            "expected_settlement",
            "actual_settlement",
            "payment_status",
            "settlement_status",
            "batch",
            "created_at",
        ]

class AIAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnalysis
        fields = [
            "id",
            "reconciliation",
            "classification",
            "explanation",
            "confidence",
            "recommended_action",
            "evidence_summary",
            "model_name",
            "prompt_version",
            "created_at",
        ]
class ReconciliationResultSerializer(
    serializers.ModelSerializer
):
    transaction_id = serializers.CharField(
        source="transaction.transaction_id",
        read_only=True,
    )

    order_id = serializers.CharField(
        source="transaction.order_id",
        read_only=True,
    )

    ai_analysis = AIAnalysisSerializer(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ReconciliationResult
        fields = [
            "id",
            "transaction",
            "transaction_id",
            "order_id",
            "result",
            "exception_type",
            "difference",
            "requires_manual_review",
            "rule_version",
            "created_at",
            "ai_analysis",
        ]



class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "batch",
            "transaction",
            "action",
            "message",
            "metadata",
            "created_at",
        ]