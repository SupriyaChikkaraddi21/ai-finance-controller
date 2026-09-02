from decimal import Decimal

from unittest.mock import patch

from django.test import TestCase
from .models import (
    AIAnalysis,
    AuditLog,
    Batch,
    ReconciliationResult,
    Transaction,
)


class FinanceControllerModelTests(TestCase):
    def setUp(self):
        self.batch = Batch.objects.create(
            name="Test Batch",
            total_records=1,
            status="COMPLETED",
        )

        self.transaction = Transaction.objects.create(
            transaction_id="TEST_TXN_001",
            order_id="TEST_ORDER_001",
            payment_amount=Decimal("1000.00"),
            fee=Decimal("20.00"),
            refund=Decimal("0.00"),
            adjustment=Decimal("0.00"),
            expected_settlement=Decimal("980.00"),
            actual_settlement=Decimal("980.00"),
            payment_status="SUCCESS",
            settlement_status="SETTLED",
            batch=self.batch,
        )

        self.reconciliation = ReconciliationResult.objects.create(
            transaction=self.transaction,
            result="MATCHED",
            exception_type="",
            difference=Decimal("0.00"),
            requires_manual_review=False,
            rule_version="v1",
        )

    def test_matched_reconciliation_has_zero_difference(self):
        """A matched transaction should have no financial difference."""
        self.assertEqual(self.reconciliation.result, "MATCHED")
        self.assertEqual(
            self.reconciliation.difference,
            Decimal("0.00"),
        )
        self.assertFalse(
            self.reconciliation.requires_manual_review
        )

    def test_exception_reconciliation_requires_manual_review(self):
        """An exception can be marked for human review."""
        exception = ReconciliationResult.objects.create(
            transaction=Transaction.objects.create(
                transaction_id="TEST_TXN_002",
                order_id="TEST_ORDER_002",
                payment_amount=Decimal("1000.00"),
                fee=Decimal("20.00"),
                refund=Decimal("0.00"),
                adjustment=Decimal("0.00"),
                expected_settlement=Decimal("980.00"),
                actual_settlement=Decimal("900.00"),
                payment_status="SUCCESS",
                settlement_status="SETTLED",
                batch=self.batch,
            ),
            result="EXCEPTION",
            exception_type="AMOUNT_MISMATCH",
            difference=Decimal("80.00"),
            requires_manual_review=True,
            rule_version="v1",
        )

        self.assertEqual(exception.result, "EXCEPTION")
        self.assertEqual(
            exception.exception_type,
            "AMOUNT_MISMATCH",
        )
        self.assertEqual(
            exception.difference,
            Decimal("80.00"),
        )
        self.assertTrue(
            exception.requires_manual_review
        )

    def test_ai_analysis_is_linked_to_reconciliation(self):
        """AI analysis must remain tied to the deterministic result."""
        analysis = AIAnalysis.objects.create(
            reconciliation=self.reconciliation,
            classification="PROCESSING_FEE",
            explanation="The difference is consistent with a processing fee.",
            confidence=Decimal("0.95"),
            recommended_action="Verify the processing fee against the fee record.",
            evidence_summary={
                "expected_settlement": "980.00",
                "actual_settlement": "980.00",
            },
            model_name="test-model",
            prompt_version="v1",
        )

        self.assertEqual(
            analysis.reconciliation,
            self.reconciliation,
        )
        self.assertEqual(
            analysis.classification,
            "PROCESSING_FEE",
        )
        self.assertEqual(
            analysis.confidence,
            Decimal("0.95"),
        )
        self.assertEqual(
            analysis.evidence_summary["expected_settlement"],
            "980.00",
        )

    def test_ai_analysis_one_to_one_relationship(self):
        """A reconciliation result should have at most one AI analysis."""
        AIAnalysis.objects.create(
            reconciliation=self.reconciliation,
            classification="UNKNOWN",
            explanation="Insufficient evidence.",
            confidence=Decimal("0.20"),
            recommended_action="Send for manual review.",
            evidence_summary={},
            model_name="test-model",
            prompt_version="v1",
        )

        self.assertEqual(
            AIAnalysis.objects.filter(
                reconciliation=self.reconciliation
            ).count(),
            1,
        )

    def test_audit_log_records_system_action(self):
        """Important system actions should be auditable."""
        audit = AuditLog.objects.create(
            batch=self.batch,
            transaction=self.transaction,
            action="RECONCILIATION_COMPLETED",
            message="Test reconciliation completed.",
            metadata={
                "rule_version": "v1",
                "result": "MATCHED",
            },
        )

        self.assertEqual(
            audit.action,
            "RECONCILIATION_COMPLETED",
        )
        self.assertEqual(
            audit.batch,
            self.batch,
        )
        self.assertEqual(
            audit.transaction,
            self.transaction,
        )
        self.assertEqual(
            audit.metadata["rule_version"],
            "v1",
        )

    @patch("core.ai_analysis_service.get_gemini_client")
    @patch("core.ai_analysis_service.build_prompt")
    @patch("core.ai_analysis_service.build_exception_evidence")
    def test_ai_analysis_creation_creates_audit_log(
        self,
        mock_build_evidence,
        mock_build_prompt,
        mock_get_client,
    ):
        """Creating a new AI analysis should create an audit log."""
        self.reconciliation.result = "EXCEPTION"
        self.reconciliation.exception_type = "AMOUNT_MISMATCH"
        self.reconciliation.difference = Decimal("80.00")
        self.reconciliation.requires_manual_review = True
        self.reconciliation.save()

        mock_build_evidence.return_value = {
            "reconciliation_id": self.reconciliation.id,
            "exception_type": "AMOUNT_MISMATCH",
        }

        mock_build_prompt.return_value = "test prompt"

        mock_response = type(
            "MockResponse",
            (),
            {
                "text": (
                    '{"classification":"AMOUNT_DISCREPANCY",'
                    '"explanation":"Test explanation",'
                    '"confidence":0.95,'
                    '"recommended_action":"Manual review",'
                    '"evidence_summary":{"difference":"80.00"}}'
                )
            },
        )()

        mock_client = mock_get_client.return_value
        mock_client.models.generate_content.return_value = (
            mock_response
        )

        from .ai_analysis_service import analyze_exception

        analysis = analyze_exception(
            self.reconciliation.id
        )

        self.assertEqual(
            analysis.classification,
            "AMOUNT_DISCREPANCY",
        )

        audit = AuditLog.objects.get(
            action="AI_ANALYSIS_CREATED",
            transaction=self.transaction,
        )

        self.assertEqual(
            audit.batch,
            self.batch,
        )
        self.assertEqual(
            audit.transaction,
            self.transaction,
        )
        self.assertEqual(
            audit.metadata["reconciliation_id"],
            self.reconciliation.id,
        )
        self.assertEqual(
            audit.metadata["model_name"],
            "gemini-3.5-flash-lite",
        )
    def test_human_resolution_records_decision_and_audit_log(self):
        """Human resolution should record the decision without changing financial truth."""
        exception = ReconciliationResult.objects.create(
            transaction=Transaction.objects.create(
                transaction_id="TEST_TXN_003",
                order_id="TEST_ORDER_003",
                payment_amount=Decimal("1000.00"),
                fee=Decimal("20.00"),
                refund=Decimal("0.00"),
                adjustment=Decimal("0.00"),
                expected_settlement=Decimal("980.00"),
                actual_settlement=Decimal("900.00"),
                payment_status="SUCCESS",
                settlement_status="SETTLED",
                batch=self.batch,
            ),
            result="EXCEPTION",
            exception_type="AMOUNT_MISMATCH",
            difference=Decimal("80.00"),
            requires_manual_review=True,
            rule_version="v1",
        )

        from rest_framework.test import APIClient

        client = APIClient()

        response = client.post(
            f"/api/reconciliations/{exception.id}/resolve/",
            {
                "resolution_status": "APPROVED",
                "resolved_by": "finance_controller",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        exception.refresh_from_db()

        self.assertEqual(
            exception.result,
            "EXCEPTION",
        )

        self.assertEqual(
            exception.resolution_status,
            "APPROVED",
        )

        self.assertEqual(
            exception.resolved_by,
            "finance_controller",
        )

        self.assertIsNotNone(
            exception.resolved_at
        )

        audit = AuditLog.objects.get(
            action="MANUAL_REVIEW",
            transaction=exception.transaction,
        )

        self.assertEqual(
            audit.metadata["previous_status"],
            "PENDING",
        )

        self.assertEqual(
            audit.metadata["resolution_status"],
            "APPROVED",
        )

        self.assertEqual(
            audit.metadata["resolved_by"],
            "finance_controller",
        )