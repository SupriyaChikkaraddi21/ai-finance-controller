from django.db import models


class Batch(models.Model):
    """
    Represents one reconciliation batch/run.
    """

    STATUS_CHOICES = [
        ("UPLOADED", "Uploaded"),
        ("PROCESSING", "Processing"),
        ("COMPLETED", "Completed"),
        ("FAILED", "Failed"),
    ]

    name = models.CharField(max_length=255)

    total_records = models.PositiveIntegerField(default=0)
    matched_records = models.PositiveIntegerField(default=0)
    exception_records = models.PositiveIntegerField(default=0)

    match_rate = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
    )

    processing_time_ms = models.PositiveIntegerField(
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="UPLOADED",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """
    Financial evidence for one transaction.
    """

    transaction_id = models.CharField(
        max_length=100
    )

    order_id = models.CharField(
        max_length=100
    )

    payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    fee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    refund = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    adjustment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    expected_settlement = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    actual_settlement = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    payment_status = models.CharField(
        max_length=30
    )

    settlement_status = models.CharField(
        max_length=30
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="transactions",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["transaction_id"]
            ),
            models.Index(
                fields=["order_id"]
            ),
        ]

    def __str__(self):
        return self.transaction_id


class ReconciliationResult(models.Model):
    """
    Deterministic reconciliation decision.
    """

    RESULT_CHOICES = [
        ("MATCHED", "Matched"),
        ("EXCEPTION", "Exception"),
    ]

    EXCEPTION_CHOICES = [
        ("", "None"),
        ("DUPLICATE", "Duplicate"),
        ("MISSING_PAYMENT", "Missing Payment"),
        ("MISSING_SETTLEMENT", "Missing Settlement"),
        ("CALCULATION_MISMATCH", "Calculation Mismatch"),
        ("AMOUNT_MISMATCH", "Amount Mismatch"),
        ("STATUS_MISMATCH", "Status Mismatch"),
        ("UNKNOWN", "Unknown"),
    ]

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="reconciliation",
    )

    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
    )

    exception_type = models.CharField(
        max_length=40,
        choices=EXCEPTION_CHOICES,
        blank=True,
        default="",
    )

    difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    requires_manual_review = models.BooleanField(
        default=False
    )

    rule_version = models.CharField(
        max_length=50,
        default="v1",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.transaction.transaction_id} - "
            f"{self.result}"
        )


class AIAnalysis(models.Model):
    """
    AI-generated analysis of a reconciliation exception.

    AI does not determine the financial truth.
    It only analyzes evidence already produced by
    the deterministic reconciliation engine.
    """

    CLASSIFICATION_CHOICES = [
        ("PROCESSING_FEE", "Processing Fee"),
        ("REFUND", "Refund"),
        ("DUPLICATE", "Duplicate"),
        ("STATUS_ISSUE", "Status Issue"),
        ("MISSING_RECORD", "Missing Record"),
        ("AMOUNT_DISCREPANCY", "Amount Discrepancy"),
        ("UNKNOWN", "Unknown"),
    ]

    reconciliation = models.OneToOneField(
        ReconciliationResult,
        on_delete=models.CASCADE,
        related_name="ai_analysis",
    )

    classification = models.CharField(
        max_length=50,
        choices=CLASSIFICATION_CHOICES,
    )

    explanation = models.TextField()

    confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    recommended_action = models.TextField(
        blank=True
    )

    evidence_summary = models.JSONField(
        default=dict,
        blank=True,
    )

    model_name = models.CharField(
        max_length=100,
        blank=True,
    )

    prompt_version = models.CharField(
        max_length=50,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"AI Analysis - "
            f"{self.reconciliation.transaction.transaction_id}"
        )


class AuditLog(models.Model):
    """
    Immutable-style record of important system actions.
    """

    ACTION_CHOICES = [
        ("BATCH_CREATED", "Batch Created"),
        ("RECONCILIATION_STARTED", "Reconciliation Started"),
        ("RECONCILIATION_COMPLETED", "Reconciliation Completed"),
        ("AI_ANALYSIS_CREATED", "AI Analysis Created"),
        ("MANUAL_REVIEW", "Manual Review"),
    ]

    batch = models.ForeignKey(
        Batch,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        null=True,
        blank=True,
    )

    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
    )

    message = models.TextField()

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"{self.action} - {self.created_at}"