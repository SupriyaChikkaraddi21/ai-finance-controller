# AI Finance Controller

An AI-assisted financial reconciliation and exception-investigation system designed for human-in-the-loop finance operations.

The system combines deterministic financial controls with AI-assisted exception analysis, verification, risk prioritization, and controller-level investigation.

---

## Overview

Financial reconciliation is not just about finding transactions that do not match.

A finance controller also needs to know:

- Which transactions are exceptions?
- What evidence explains the exception?
- Can an AI system classify and explain the exception reliably?
- Can the AI conclusion be independently verified?
- Which exceptions should a human investigate first?
- What happened during the investigation?
- What should remain unresolved and be escalated to a human?

This project implements that workflow as a layered system.

```text
Financial Data
      |
      v
Deterministic Reconciliation
      |
      v
Exception Detection
      |
      v
AI Investigation
      |
      v
AI Verification
      |
      v
Risk Assessment
      |
      v
Finance Controller Agent
      |
      v
Human Review / Controller Report
```

The core design principle is:

> AI assists the finance controller. Deterministic controls protect financial truth.

---

## What the System Does

The current system processes a synthetic batch of financial transactions and performs:

1. Transaction validation
2. Deterministic reconciliation
3. Duplicate detection
4. Exception classification
5. Exception evidence extraction
6. AI-based exception analysis
7. AI classification verification
8. Risk assessment
9. Controller-level investigation
10. Audit logging
11. Batch-level metrics
12. Automated evaluation against ground truth
13. AI reliability evaluation
14. API failure recording

---

## System Architecture

The system is divided into separate control layers.

### Layer 1 — Financial Data

Synthetic transaction data is used to simulate a financial reconciliation workload.

Each transaction contains fields such as:

- Transaction ID
- Order ID
- Payment amount
- Fee
- Refund
- Adjustment
- Expected settlement
- Actual settlement
- Payment status
- Settlement status

The current evaluation dataset contains:

- 100 transactions
- 100 ground-truth records
- 100 reconciliation results

---

### Layer 2 — Deterministic Reconciliation Engine

The deterministic engine is the financial source of truth.

It does not use AI to determine whether money reconciles.

The engine validates:

- Missing payments
- Missing settlements
- Settlement calculations
- Actual vs expected settlement amounts
- Payment and settlement status consistency
- Duplicate orders

The expected settlement formula is:

```text
Expected Settlement
= Payment Amount
- Fee
- Refund
+ Adjustment
```

Amount differences are detected deterministically.

For example:

```text
Expected Settlement = ₹783.02
Actual Settlement   = ₹783.02

Difference = ₹0.00

Result = MATCHED
```

If the actual settlement differs from the expected settlement beyond the configured tolerance, the transaction becomes an exception.

---

## Exception Types

The deterministic engine currently identifies:

- `AMOUNT_MISMATCH`
- `DUPLICATE`
- `MISSING_PAYMENT`
- `MISSING_SETTLEMENT`
- `STATUS_MISMATCH`

The engine can also detect calculation inconsistencies internally through:

- `CALCULATION_MISMATCH`

The final persisted exception classification is controlled by deterministic rules.

---

## Duplicate Detection

Duplicate detection is performed using the order ID.

The first occurrence of an order is treated as valid.

Subsequent occurrences are classified as duplicates.

Example:

```text
ORD0001 → MATCHED
ORD0001 → DUPLICATE
```

This prevents the system from incorrectly treating the first valid occurrence as an exception.

---

## Layer 3 — AI Exception Investigation

AI is not used to replace the reconciliation engine.

Instead, Gemini is used after deterministic reconciliation to analyze exceptions.

The AI receives controlled financial evidence produced by the system.

The evidence can include:

- Transaction ID
- Order ID
- Payment amount
- Fee
- Refund
- Adjustment
- Expected settlement
- Actual settlement
- Payment status
- Settlement status
- Deterministic result
- Deterministic exception
- Difference
- Manual-review requirement
- Rule version

The AI is explicitly instructed not to:

- Change the deterministic result
- Invent transactions
- Invent missing records
- Change financial amounts
- Override reconciliation results
- Claim an exception is resolved
- Invent fees or other financial causes
- Invent unsupported root causes

This creates a controlled boundary between deterministic financial logic and generative AI.

---

## AI Classification

The AI converts deterministic exception types into higher-level investigation classifications.

For example:

```text
Deterministic:
AMOUNT_MISMATCH

AI Classification:
AMOUNT_DISCREPANCY
```

The important design rule is that an amount discrepancy does not automatically imply a known root cause.

If the evidence only proves:

```text
Expected = ₹1000
Actual   = ₹980
```

the AI must classify the issue as:

```text
AMOUNT_DISCREPANCY
```

It must not invent a processing fee, tax, refund, or processor charge unless the evidence explicitly contains that information.

---

## AI Evidence Boundary

The AI analysis layer follows a controlled-evidence approach.

The model receives financial information that has already been produced or stored by the reconciliation system.

This prevents the model from becoming the source of financial truth.

The architecture is therefore:

```text
Financial Data
      |
      v
Deterministic Rules
      |
      +------> Financial Truth
      |
      v
Exception
      |
      v
Controlled Evidence
      |
      v
AI Analysis
      |
      v
Verification
```

---

## Layer 4 — AI Verification

AI output is independently evaluated against predefined classification mappings.

The evaluation checks whether the AI classification matches the expected classification.

The current AI evaluation covers:

- Amount discrepancies
- Duplicate records
- Missing payments
- Missing settlements
- Status issues

The latest recorded evaluation shows:

```text
Total exceptions evaluated : 25
Evaluation coverage        : 100%

Valid responses            : 25
Invalid responses          : 0

Correct classifications    : 25
Wrong classifications      : 0

Classification accuracy    : 100%

Average confidence         : 0.986
```

Per-class evaluation currently reports:

```text
AMOUNT_DISCREPANCY
Precision : 100%
Recall    : 100%
F1        : 100%

DUPLICATE
Precision : 100%
Recall    : 100%
F1        : 100%

MISSING_RECORD
Precision : 100%
Recall    : 100%
F1        : 100%

STATUS_ISSUE
Precision : 100%
Recall    : 100%
F1        : 100%
```

These results are based on the current synthetic evaluation dataset and should not be interpreted as production-level accuracy.

---

## Layer 5 — Risk Assessment

Not every exception has the same operational importance.

The controller system therefore assigns risk levels to exceptions.

Risk assessment considers the available exception evidence and prioritizes investigation.

The current risk levels are:

```text
HIGH
MEDIUM
LOW
```

The controller uses risk information to determine which exceptions require deeper investigation.

---

## Layer 6 — Finance Controller Agent

The Finance Controller Agent acts as an investigation orchestrator.

The controller architecture is separated into focused components:

- `controller.py` — controller entry point and orchestration
- `agent_loop.py` — bounded Gemini/tool-call investigation loop
- `tools.py` — investigation and financial evidence tools
- `tool_registry.py` — controller tool declarations and dispatch
- `prompts.py` — controller system and task prompts
- `loop_state.py` — investigation coverage and operational state
- `decisions.py` — investigation and finalization decisions
- `reporting.py` — authoritative controller report construction

It is not the financial reconciliation engine.

The controller can inspect:

- Batch-level metrics
- Exception populations
- Investigation scope
- Individual transaction evidence
- Existing AI analyses
- AI analysis verification
- Exception risk
- Controller-level reports

The controller follows a bounded investigation process.
The controller operates within a configured Gemini model-call budget. If that budget is reached before all required exceptions are investigated, the controller reports partial investigation coverage and leaves the remaining exceptions for further automated investigation or manual review.

The deterministic reconciliation engine remains the authoritative source of financial truth. AI analysis and controller reasoning do not override deterministic reconciliation results.

It can identify which deterministic exceptions require individual investigation and prioritize them using risk level.

For the current 100-record dataset:

```text
Total records : 100
Matched       : 75
Exceptions    : 25
```

The controller therefore has a concrete exception population to investigate rather than operating on arbitrary generated text.

---

## Controller Investigation Flow

The controller workflow is approximately:

```text
Inspect Batch
     |
     v
Inspect Investigation Scope
     |
     v
Identify Exceptions
     |
     v
Prioritize by Risk
     |
     v
Inspect Individual Evidence
     |
     v
Analyze / Inspect AI Result
     |
     v
Verify AI Analysis
     |
     v
Build Controller Report
     |
     v
Human Review
```

The system maintains a distinction between:

```text
Automated conclusion
        |
        v
Verified conclusion
        |
        v
Human decision
```

The controller does not blindly trust an AI-generated explanation.

---

## Layer 7 — Audit Logging

Controller activity is recorded through audit logs.

The system records important workflow events such as reconciliation execution and controller activity.

This provides traceability for:

- What action occurred
- Which batch was involved
- What stage of the workflow was reached
- What investigation was performed

Auditability is important because a finance control system must be able to explain how a conclusion was reached.

---

## Batch Metrics

The reconciliation system records batch-level operational metrics.

Current metrics include:

- Total records
- Matched records
- Exception records
- Match rate
- Exception rate
- Processing time
- Throughput

Latest deterministic evaluation:

```text
Total records       : 100
Matched             : 75
Exceptions          : 25
Match rate          : 75.00%
Exception rate      : 25.00%
```
Performance metrics are environment- and dataset-dependent. The reconciliation API reports processing time and throughput for each completed batch. These values should not be treated as production benchmarks.
---

## Deterministic Evaluation

The reconciliation output is evaluated against a predefined ground-truth dataset.

The latest evaluation result is:

```text
Total records : 100
Correct       : 100
Wrong         : 0
Accuracy      : 100.00%
```

The current confusion matrix is:

```text
AMOUNT_MISMATCH
12 correct

DUPLICATE
3 correct

MATCHED
75 correct

MISSING_PAYMENT
3 correct

MISSING_SETTLEMENT
4 correct

STATUS_MISMATCH
3 correct
```

Every evaluated record currently matches the expected deterministic classification.

---

## Ground Truth Distribution

The current synthetic dataset contains:

```text
AMOUNT_MISMATCH       12
DUPLICATE              3
MISSING_PAYMENT        3
MISSING_SETTLEMENT     4
STATUS_MISMATCH        3
```

Total exceptions:

```text
25
```

Matched records:

```text
75
```

Total records:

```text
100
```

---

## Reliability Testing

The project includes a dedicated AI reliability test.

The reliability layer is intended to verify that the AI classification contract remains stable across repeated evaluation.

The repository contains:

```text
scripts/test_reliability.py
```

and:

```text
scripts/evaluate_ai.py
```

These provide automated evaluation of AI outputs and reliability-related behavior.

---

## API Failure Recording

External AI APIs can fail.

The system therefore records AI API failures rather than silently ignoring them.

Failures are persisted in:

```text
data/ai_api_failures.json
```

Recorded information includes:

- Timestamp
- Reconciliation ID
- Model name
- Prompt version
- Error type
- Error message

This makes model-service failures observable during evaluation.

---

## Important AI Safety Design

The most important architectural decision is the separation of financial truth from AI interpretation.

The system follows:

```text
                FINANCIAL TRUTH
                      |
                      v
          Deterministic Engine
                      |
                      v
                Exception
                      |
                      v
              Evidence Layer
                      |
                      v
                 AI Layer
                      |
                      v
                Verification
                      |
                      v
              Risk Assessment
                      |
                      v
          Controller Investigation
                      |
                      v
              Human Decision
```

The AI cannot redefine the financial result.

It can only analyze and explain an exception using the evidence provided by the system.

---

## Technology Stack

### Backend

- Python
- Django
- Django REST Framework
- PostgreSQL
- Google Gemini API

### Frontend

- React
- Vite
- JavaScript
- CSS

### Data and Evaluation

- CSV
- JSON
- Synthetic financial dataset
- Deterministic ground truth
- Automated evaluation scripts

### Development

- Git
- GitHub
- Python virtual environment

---
## Project Structure

```text
ai-finance-controller/
│
├── backend/
│   ├── core/
│   │   ├── agent/
│   │   │   ├── controller.py
│   │   │   ├── agent_loop.py
│   │   │   ├── tools.py
│   │   │   ├── tool_registry.py
│   │   │   ├── prompts.py
│   │   │   ├── loop_state.py
│   │   │   ├── decisions.py
│   │   │   └── reporting.py
│   │   │
│   │   ├── ai_analysis_service.py
│   │   ├── reconciliation_rules.py
│   │   ├── reconciliation_service.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests.py
│   │
│   ├── manage.py
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AuditTrail.jsx
│   │   │   ├── ControllerReview.jsx
│   │   │   ├── ExceptionDistribution.jsx
│   │   │   ├── ExceptionInvestigation.jsx
│   │   │   ├── FinancialOverview.jsx
│   │   │   ├── InvestigationCoverage.jsx
│   │   │   └── PerformanceBenchmark.jsx
│   │   │
│   │   ├── styles/
│   │   │   ├── audit.css
│   │   │   ├── benchmark.css
│   │   │   ├── controller.css
│   │   │   ├── exceptions.css
│   │   │   ├── financial.css
│   │   │   └── investigation.css
│   │   │
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   ├── transactions.csv
│   ├── ground_truth.csv
│   ├── reconciliation_results.csv
│   ├── evaluation_results.json
│   ├── ai_evaluation_results.json
│   └── ai_api_failures.json
│
├── scripts/
│   ├── generate_dataset.py
│   ├── reconcile.py
│   ├── evaluate.py
│   ├── evaluate_ai.py
│   └── test_reliability.py
│
├── requirements.txt
└── README.md

---

## API Endpoints

The backend exposes endpoints for the reconciliation workflow.

### Batch

```text
GET /api/batches/
POST /api/batches/
```

### Reconciliation

```text
POST /api/batches/<batch_id>/reconcile/
```

### Results

```text
GET /api/batches/<batch_id>/results/
```

### Exceptions

```text
GET /api/batches/<batch_id>/exceptions/
```

### Metrics

```text
GET /api/batches/<batch_id>/metrics/
```

### AI Analysis

```text
POST /api/reconciliations/<reconciliation_id>/ai-analysis/
GET  /api/reconciliations/<reconciliation_id>/ai-analysis/detail/
```

### Finance Controller

```text
POST /api/batches/<batch_id>/controller/
```

---

## Running the Project

### 1. Clone the repository

```bash
git clone https://github.com/SupriyaChikkaraddi21/ai-finance-controller.git
cd ai-finance-controller
```

### 2. Create a Python environment

```bash
python -m venv venv
```

Activate it on Linux / WSL:

```bash
source venv/bin/activate
```

### 3. Install backend dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create:

```text
backend/.env
```

using:

```text
backend/.env.example
```

The Gemini API key should be configured as:

```text
GEMINI_API_KEY=your_api_key
```

Do not commit the real API key to Git.

---

## Running the Backend

From the repository root:

```bash
cd backend
python manage.py migrate
python manage.py runserver
```

The backend will be available through the Django development server.

---

## Running the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The React frontend provides the controller dashboard for interacting with batches, metrics, exceptions, AI analysis, and controller investigation.

---
---

## Demo Workflow

After starting the backend and frontend, use the React dashboard for the complete finance-controller workflow:

1. Open the React dashboard in the browser.
2. Click **Run Reconciliation** to create a new reconciliation batch.
3. The system processes the synthetic financial dataset and displays the deterministic results:
   - 100 total records
   - 75 matched records
   - 25 exceptions
   - 75% match rate
4. Select an exception to inspect its deterministic financial evidence.
5. Click **Analyze Exception** for AI-assisted interpretation of the exception.
6. Review the AI classification, evidence summary, confidence, and recommended action.
7. Run the **Finance Controller** to investigate the exception population.
8. Review deterministic risk prioritization and investigation coverage.
9. The controller uses a bounded investigation process and reports partial coverage when its model-call budget prevents complete investigation.
10. Make the final human controller decision:
    - **Approve**
    - **Reject**
    - **Escalate**
11. Review the **Audit Trail** for reconciliation, investigation, AI analysis, and human-review events.
12. Use **Export Controller Report** to export the controller investigation report as JSON.

> Each intentional **Run Reconciliation** execution creates a new reconciliation batch. Previous batches remain available for historical review and auditability.

## Running Deterministic Reconciliation

From the repository root:

```bash
python scripts/reconcile.py
```

Expected output is similar to:

```text
Starting reconciliation...

Loaded transactions: 100
Duplicate orders detected: 3

========================================
RECONCILIATION COMPLETE
========================================
Total transactions : 100
Matched            : 75
Exceptions         : 25
Match rate         : 75.0%
Exception rate     : 25.0%
```

The results are written to:

```text
data/reconciliation_results.csv
```

---

## Running Deterministic Evaluation

Run:

```bash
python scripts/evaluate.py
```

The evaluation compares:

```text
Ground Truth
      vs
Reconciliation Results
```

and generates:

```text
data/evaluation_results.json
```

---

## Running AI Evaluation

Run:

```bash
python scripts/evaluate_ai.py
```

This evaluates persisted AI exception analyses against the expected classification mapping.

The generated report is:

```text
data/ai_evaluation_results.json
```

---

## Running Reliability Tests

Run:

```bash
python scripts/test_reliability.py
```

The reliability tests verify the expected AI classification contract and record relevant failures.

---

## Current Project Status

## Current Project Status

The current implementation has:

- Synthetic financial transaction dataset
- Ground-truth dataset
- Deterministic reconciliation engine
- Duplicate detection
- Financial exception classification
- PostgreSQL-backed reconciliation persistence
- Batch metrics
- Performance benchmarking
- AI exception analysis
- Controlled AI evidence
- AI classification verification
- AI failure and quota fallback handling
- Deterministic exception risk assessment
- Financial-exposure-based exception prioritization
- Finance Controller Agent
- Bounded controller investigation loop
- Investigation coverage tracking
- Controller investigation tools
- Controller report generation
- Exportable controller report
- Human-in-the-loop exception resolution
- Approve / Reject / Escalate workflow
- Audit logging and audit trail
- Exception distribution visualization
- Investigation coverage visualization
- Automated deterministic evaluation
- Automated AI evaluation
- AI reliability testing
- AI API failure recording
- React dashboard
- Modular controller and investigation UI
- Modular frontend styling
- Git/GitHub version control
---

## Current Evaluation Snapshot

The latest deterministic evaluation:

```text
Dataset size : 100 records
Deterministic accuracy : 100.00%
Matched : 75
Exceptions : 25
```

The latest AI exception evaluation:

```text
Exceptions evaluated : 25
Evaluation coverage  : 100%
AI classification accuracy : 100%
Average confidence : 0.986
```

These results are from the current synthetic dataset and evaluation setup.

They demonstrate system correctness under the defined test cases, not guaranteed production accuracy.

---

## Limitations

This is currently a prototype / internship-level finance operations system rather than a production financial control platform.

Important limitations include:

- The dataset is synthetic.
- The current workload is only 100 records.
- The system does not yet integrate with real payment processors or banks.
- AI analysis depends on an external Gemini API.
- API failures can occur and are recorded.
- The current risk model is rule-based rather than statistically calibrated.
- Production authentication and authorization are not yet implemented.
- Production-grade observability and deployment infrastructure are not yet implemented.
- The current evaluation does not prove real-world financial accuracy.

These limitations are intentionally documented rather than hidden.

---

## Design Philosophy

The system is built around three principles.

### 1. Deterministic financial truth

Financial reconciliation should not depend on a language model deciding whether two monetary values match.

The deterministic engine establishes the financial result.

### 2. AI-assisted investigation

AI is useful for analyzing exceptions, summarizing evidence, classifying issues, and assisting the controller.

It should not silently override financial controls.

### 3. Human-in-the-loop control

High-impact financial decisions should remain auditable and reviewable by humans.

The system therefore treats AI as an investigation assistant rather than an autonomous financial authority.

---

## Why This Architecture

A naive architecture would look like:

```text
Transactions
     |
     v
LLM
     |
     v
Financial Decision
```

That creates a serious control problem because the language model becomes responsible for financial truth.

This project instead uses:

```text
Transactions
     |
     v
Deterministic Financial Controls
     |
     v
Exception
     |
     v
AI Investigation
     |
     v
Verification
     |
     v
Risk Prioritization
     |
     v
Controller
     |
     v
Human Review
```

This architecture provides a clearer separation of responsibilities and makes AI behavior easier to evaluate and audit.

---

## Key Result

The project demonstrates a complete finance-operations loop:

```text
Detect
  ↓
Investigate
  ↓
Explain
  ↓
Verify
  ↓
Prioritize
  ↓
Report
  ↓
Human Review
```

The goal is not simply to build an AI chatbot for finance.

The goal is to build an AI-assisted finance controller that can operate on structured financial evidence while keeping deterministic controls and human review at the center of the workflow.

---

## Author

Supriya Chikkaraddi

GitHub:

https://github.com/SupriyaChikkaraddi21/ai-finance-controller