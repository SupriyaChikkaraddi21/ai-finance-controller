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
    payment_amount = serializers.DecimalField(
        source="transaction.payment_amount",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    fee = serializers.DecimalField(
        source="transaction.fee",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    refund = serializers.DecimalField(
        source="transaction.refund",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    adjustment = serializers.DecimalField(
        source="transaction.adjustment",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    expected_settlement = serializers.DecimalField(
        source="transaction.expected_settlement",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    actual_settlement = serializers.DecimalField(
        source="transaction.actual_settlement",
        max_digits=12,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )
    payment_status = serializers.CharField(
        source="transaction.payment_status",
        read_only=True,
    )

    settlement_status = serializers.CharField(
        source="transaction.settlement_status",
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
            "payment_amount",
            "fee",
            "refund",
            "adjustment",
            "expected_settlement",
            "actual_settlement",
            "payment_status",
            "settlement_status",
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