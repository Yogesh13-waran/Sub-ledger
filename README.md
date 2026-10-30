# SubLedger - SaaS Subscription & Billing System

A clean, production-grade billing backend engineered with **FastAPI**, **SQLAlchemy 2.0**, and **Pydantic v2**, following **SOLID Principles**, the **Repository Pattern**, **Domain-Driven Design (DDD)**, and an **Append-Only Financial Ledger**.

---

## 🌟 Key Architectural Features

- **Strict Layered Separation**:
  - `Routes` (FastAPI APIRouters) $\to$ `Services` (Business Logic) $\to$ `Repositories` (Data Persistence) $\to$ `Models` (SQLAlchemy ORM Entities)
- **100% SOLID Principles Compliance**: Decoupled, extensible, testable, and maintainable.
- **Financial Precision**: Eliminates floating-point inaccuracies by enforcing `Numeric(12, 2)` / Python `Decimal` across all currency operations.
- **Snapshot Pricing Pattern**: Guarantees invoice amounts are permanently locked to plan prices at generation time.
- **Append-Only Financial Audit Ledger**: Immutability enforced at the repository layer (`update` and `delete` are strictly prohibited).
- **Payment Reconciliation**: Full support for failed payment tracking, partial payment state progression (`issued` $\to$ `partially_paid` $\to$ `paid`), overpayment protection, and idempotency keying.

---

## 📋 Required Business Rules Compliance

| Business Rule | Status | Implementation Details |
|---|:---:|---|
| **1. Plan price must be > 0** | ✅ | Validated in `PlanCreate` Pydantic validator & `PlanService.create_plan` |
| **2. Customer email must be unique** | ✅ | Database unique constraint & `CustomerRepository.get_by_email` lookup |
| **3. Cannot subscribe to inactive plan** | ✅ | Enforced in `SubscriptionService.create_subscription` (`InactivePlanException`) |
| **4. No duplicate active subscriptions** | ✅ | Enforced in `SubscriptionRepository.get_active_by_customer_and_plan` (`DuplicateActiveSubscriptionException`) |
| **5. Invoice amount_due from plan price snapshot** | ✅ | Snapshot copied into `Invoice.amount_due` at generation time |
| **6. Successful payment cannot exceed unpaid balance** | ✅ | Enforced in `PaymentService.record_payment` (`InvalidPaymentAmountException`) |
| **7. Invoice status moves to paid / partially_paid** | ✅ | Dynamic status transitions based on cumulative `amount_paid` |
| **8. Failed payment does not increase amount_paid** | ✅ | Isolated failure branch in `PaymentService` recording `payment_failure` ledger entry |
| **9. Append-only ledger traceable by reference_id** | ✅ | Mutating methods blocked in `LedgerRepository`; searchable by `reference_id` |

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- Virtual environment (recommended)

### 2. Installation
```bash
# Clone or navigate to the repository
cd python-subledger

# Install dependencies
pip install -r requirements.txt
```

### 3. Running the Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- **API Root**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Running the Test Suite
```bash
pytest -v
```
All unit, repository, service, and end-to-end integration tests execute against an isolated in-memory SQLite database.

---

## 📡 API Reference & cURL Walkthrough

### 1. Register a Customer
```bash
curl -X POST "http://localhost:8000/api/v1/customers" \
  -H "Content-Type: application/json" \
  -d '{"name": "Starlight SaaS", "email": "finance@starlight.io"}'
```

### 2. Create a Plan
```bash
curl -X POST "http://localhost:8000/api/v1/plans" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Enterprise Tier",
    "description": "Full-featured monthly subscription",
    "price": "100.00",
    "currency": "USD",
    "billing_interval": "monthly",
    "is_active": true
  }'
```

### 3. Create a Subscription
```bash
curl -X POST "http://localhost:8000/api/v1/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "plan_id": 1}'
```

### 4. Generate an Invoice
```bash
curl -X POST "http://localhost:8000/api/v1/invoices/generate" \
  -H "Content-Type: application/json" \
  -d '{"subscription_id": 1}'
```
*Returns invoice with `amount_due: 100.00`, `amount_paid: 0.00`, and `status: "issued"`.*

### 5. Record a Partial Payment ($40.00)
```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 1,
    "amount": "40.00",
    "currency": "USD",
    "status": "success",
    "provider_reference": "TX_GW_PARTIAL_001"
  }'
```
*Invoice status automatically transitions to `"partially_paid"` with `remaining_balance: 60.00`.*

### 6. Record Remaining Payment ($60.00)
```bash
curl -X POST "http://localhost:8000/api/v1/payments" \
  -H "Content-Type: application/json" \
  -d '{
    "invoice_id": 1,
    "amount": "60.00",
    "currency": "USD",
    "status": "success",
    "provider_reference": "TX_GW_FULL_002"
  }'
```
*Invoice status transitions to `"paid"` with `remaining_balance: 0.00`.*

### 7. Inspect the Audit Ledger Trail
```bash
curl -X GET "http://localhost:8000/api/v1/ledger?invoice_id=1"
```
*Returns complete chronological audit history: `invoice_created`, `payment_success` (partial), and `payment_success` (final).*

---

## 📂 Project Structure

```
python-subledger/
├── app/
│   ├── main.py                     # App factory, CORS, and Global Exception Handlers
│   ├── db.py                       # Engine, SessionLocal, get_db dependency, Base
│   ├── core/
│   │   ├── config.py               # Settings & Environment variables
│   │   └── exceptions.py           # Domain exceptions (EntityNotFound, InactivePlan, etc.)
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── base.py                 # TimestampMixin and UTC helper
│   │   ├── customer.py             # Customer entity
│   │   ├── plan.py                 # Plan entity
│   │   ├── subscription.py         # Subscription entity
│   │   ├── invoice.py              # Invoice entity (with snapshot pricing & balance properties)
│   │   ├── payment_attempt.py      # PaymentAttempt entity
│   │   └── ledger_entry.py         # Append-only LedgerEntry entity
│   ├── schemas/                    # Pydantic DTOs for validation and serialization
│   │   ├── common.py               # Generic API envelopes and BaseSchema
│   │   ├── customer.py             # Customer DTOs
│   │   ├── plan.py                 # Plan DTOs (price > 0 validator)
│   │   ├── subscription.py         # Subscription DTOs
│   │   ├── invoice.py              # Invoice DTOs
│   │   ├── payment.py              # Payment DTOs
│   │   └── ledger.py               # Ledger DTOs
│   ├── repositories/               # Data access layer
│   │   ├── base.py                 # Generic BaseRepository[T]
│   │   ├── customer_repository.py  # Customer queries
│   │   ├── plan_repository.py      # Plan queries
│   │   ├── subscription_repository.py # Subscription queries
│   │   ├── invoice_repository.py   # Invoice queries
│   │   ├── payment_attempt_repository.py # Payment attempt queries (idempotency check)
│   │   └── ledger_repository.py    # Append-only repository (blocks updates/deletions)
│   ├── services/                   # Business logic layer
│   │   ├── customer_service.py     # Customer lifecycle & email uniqueness
│   │   ├── plan_service.py         # Plan lifecycle & price > 0 check
│   │   ├── subscription_service.py # Subscription rules (active plan, single active sub)
│   │   ├── invoice_service.py      # Invoice generation & snapshot pricing
│   │   ├── payment_service.py      # Payment processing & balance reconciliation
│   │   └── ledger_service.py       # Append-only audit logging
│   └── api/                        # Presentation layer
│       ├── deps.py                 # FastAPI Dependency Injection provider
│       └── v1/                     # Version 1 REST API routers
│           ├── api_router.py       # Combined router aggregator
│           ├── customers.py        # Customer endpoints
│           ├── plans.py            # Plan endpoints
│           ├── subscriptions.py    # Subscription endpoints
│           ├── invoices.py         # Invoice endpoints
│           ├── payments.py         # Payment endpoints
│           └── ledger.py           # Audit ledger endpoints
├── tests/                          # Test suite
│   ├── conftest.py                 # In-memory SQLite fixtures & mock DI
│   ├── test_models.py              # Model unit tests
│   ├── test_repositories.py        # Repository unit tests (append-only enforcement)
│   ├── test_services.py            # Domain business rule unit tests
│   └── test_api_e2e.py             # End-to-end integration tests
├── DESIGN.md                       # Comprehensive Low-Level Design (LLD) with Mermaid diagrams
├── CONCEPTS_AND_ARCHITECTURE_DEEP_DIVE.md # File-by-file concept breakdown and interview guide
├── pytest.ini                      # Pytest configuration
└── requirements.txt                # Python package dependencies
```

---

## 📚 Deep-Dive Documentation

For an exhaustive, file-by-file breakdown of every design choice, SOLID principles analysis, and billing interview preparation questions, see:
- [DESIGN.md](DESIGN.md): Low-Level Design (LLD) specification with Mermaid diagrams.
- [CONCEPTS_AND_ARCHITECTURE_DEEP_DIVE.md](CONCEPTS_AND_ARCHITECTURE_DEEP_DIVE.md): Masterclass educational guide covering all architectural concepts in deep detail.

