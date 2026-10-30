# SubLedger - Architectural Concepts & File-by-File Masterclass Guide

This document is an exhaustive, deep-dive educational companion for **SubLedger**. It leaves no stone unturned: every architectural decision, every pattern, every design principle, and **every single file** in the codebase is analyzed with its exact engineering rationale, problem statement, and production best practices.

---

## Table of Contents
1. [Architectural Philosophy: Clean Architecture in Python](#1-architectural-philosophy-clean-architecture-in-python)
2. [File-by-File Deep Dive: Role, Rationale & Mechanics](#2-file-by-file-deep-dive-role-rationale--mechanics)
   - [Core Infrastructure (`app/core/`, `app/db.py`, `app/main.py`)](#21-core-infrastructure)
   - [Domain Model Layer (`app/models/`)](#22-domain-model-layer)
   - [Validation & DTO Layer (`app/schemas/`)](#23-validation--dto-layer)
   - [Persistence / Repository Layer (`app/repositories/`)](#24-persistence--repository-layer)
   - [Business Logic / Service Layer (`app/services/`)](#25-business-logic--service-layer)
   - [Presentation / API Layer (`app/api/`)](#26-presentation--api-layer)
   - [Testing Framework (`tests/`, `pytest.ini`)](#27-testing-framework)
3. [Core Software Engineering Concepts Deep-Dive](#3-core-software-engineering-concepts-deep-dive)
   - [1. Data Mapper (SQLAlchemy) vs Active Record (Django ORM)](#31-data-mapper-sqlalchemy-vs-active-record-django-orm)
   - [2. Why `float` is Forbidden in Financial Systems (`Decimal` vs IEEE 754)](#32-why-float-is-forbidden-in-financial-systems-decimal-vs-ieee-754)
   - [3. The Snapshot Pricing Pattern](#33-the-snapshot-pricing-pattern)
   - [4. The Append-Only Audit Ledger Pattern](#34-the-append-only-audit-ledger-pattern)
   - [5. Dependency Injection (DI) and Inversion of Control (IoC)](#35-dependency-injection-di-and-inversion-of-control-ioc)
   - [6. Idempotency and Webhook Race Conditions](#36-idempotency-and-webhook-race-conditions)
4. [SOLID Principles in Action: Before and After Code Comparisons](#4-solid-principles-in-action-before-and-after-code-comparisons)
5. [Senior Backend Engineer Interview Preparation (SaaS Billing)](#5-senior-backend-engineer-interview-preparation-saas-billing)

---

## 1. Architectural Philosophy: Clean Architecture in Python

In typical tutorial code or junior implementations, developers often place SQL queries, serialization, validation, HTTP handling, and business rules inside a single file (such as a Django view or FastAPI route handler). This leads to what engineers call the **"Smart Controller / Fat View" anti-pattern**.

### What Goes Wrong Without Clean Architecture?
1. **Untestable Logic**: You cannot test whether a subscription business rule works without booting up a web server and generating mock HTTP requests.
2. **Coupling to the Framework**: If you want to run invoice generation from a Celery background worker, a CLI script, or a Lambda function, you cannot reuse view code without importing HTTP request objects.
3. **Fragile Persistence**: Changing a column name or switching databases breaks business calculations.
4. **Race Conditions & Transaction Leaks**: If transaction boundaries (`commit`, `rollback`) are scattered across views, database deadlocks and partial state mutations occur.

### The SubLedger Solution: The 4-Tier Clean Architecture
SubLedger strictly separates responsibilities into four unidirectional tiers:

$$\text{Routes (API)} \longrightarrow \text{Services (Business Logic)} \longrightarrow \text{Repositories (Data Access)} \longrightarrow \text{Models (Database)}$$

- **Routes (`app/api/`)**: Speak **HTTP**. They know about status codes (200, 201, 400, 404), headers, cookies, and JSON envelopes. They do *no* business validation and *no* database queries.
- **Services (`app/services/`)**: Speak **Domain Rules**. They know that a customer cannot have two active subscriptions, that payments cannot exceed the unpaid balance, and that invoices must record ledger entries. They know *nothing* about HTTP status codes, request objects, or SQL queries.
- **Repositories (`app/repositories/`)**: Speak **Data Queries**. They execute `select`, `insert`, `update`, and filter logic via SQLAlchemy. They know *nothing* about business rules.
- **Models (`app/models/`)**: Speak **Relational Schema**. They define table structures, column datatypes, foreign keys, and indexes.

---

## 2. File-by-File Deep Dive: Role, Rationale & Mechanics

Let's dissect every file created in the project.

---

### 2.1. Core Infrastructure

#### `app/core/config.py`
- **Purpose**: Centralizes environment variables, app names, database connection strings, and debug settings.
- **Why it exists**: Hardcoding strings like `"sqlite:///./subledger.db"` or API prefixes across multiple files violates the **DRY (Don't Repeat Yourself)** principle. If the database URL changes to PostgreSQL in production (`postgresql://user:pass@aws-rds/db`), only `DATABASE_URL` in `.env` needs to be updated.
- **Key Concepts Used**: Pydantic `BaseModel` default values, `os.getenv` fallback pattern.

#### `app/core/exceptions.py`
- **Purpose**: Declares semantic domain exceptions (`EntityNotFoundException`, `InactivePlanException`, `DuplicateActiveSubscriptionException`, `InvalidPaymentAmountException`, etc.).
- **Why it exists**: **Single Responsibility Principle (SRP)**. If a service were to raise `fastapi.HTTPException(status_code=400)`, that service would become tightly coupled to FastAPI's web framework. By raising pure Python domain exceptions, the service remains 100% agnostic of the delivery mechanism (CLI, REST API, gRPC, or Queue Worker).
- **Key Concepts Used**: Custom exception hierarchy inheriting from a root `SubLedgerException`, structured error context payloads (`details: dict`).

#### `app/db.py`
- **Purpose**: Instantiates the SQLAlchemy database `engine`, `SessionLocal` factory, declarative `Base`, and the `get_db()` dependency generator.
- **Why it exists**: Manages the database connection pool and ensures safe request-scoped session lifecycles.
- **Key Mechanics**:
  - `check_same_thread=False` allows multi-threaded request processing in SQLite.
  - `get_db()` uses Python's `yield` generator to implement the **Context Manager Pattern**. It guarantees that whether an endpoint succeeds or crashes with an unhandled exception, `db.rollback()` and `db.close()` are called deterministically, preventing connection pool exhaustion.
  - `init_db()` provides auto-creation of tables for development and testing.

#### `app/main.py`
- **Purpose**: Application factory and entry point.
- **Why it exists**: Bootstraps FastAPI, configures OpenAPI documentation (`/docs`, `/redoc`), applies CORS middleware, registers routers, and sets up **Global Exception Handlers**.
- **Key Mechanics**:
  - Translates domain exceptions into structured HTTP JSON responses:
    - `EntityNotFoundException` $\to$ `404 Not Found`
    - `DuplicateResourceException` $\to$ `409 Conflict`
    - `DuplicateActiveSubscriptionException` $\to$ `409 Conflict`
    - `InvalidPaymentAmountException` $\to$ `400 Bad Request`
    - `InactivePlanException` $\to$ `400 Bad Request`
  - Utilizes modern FastAPI `lifespan` context manager rather than deprecated `@app.on_event("startup")`.

---

### 2.2. Domain Model Layer

#### `app/models/base.py`
- **Purpose**: Defines shared table columns and helpers (`TimestampMixin`, `utc_now()`).
- **Why it exists**: Eliminates copy-pasting `created_at` and `updated_at` definitions across all models.
- **Key Concepts**: `timezone.utc` ensures all timestamps are stored in UTC, avoiding timezone bugs across distributed servers.

#### `app/models/customer.py`
- **Purpose**: Defines the `customers` database table.
- **Why it exists**: Stores subscriber profiles.
- **Key Fields**: `email` is indexed (`index=True`) and marked `unique=True` at the database level to provide hardware-enforced uniqueness. Relationships define cascades so deleting a customer safely cleans up orphaned records in test teardowns.

#### `app/models/plan.py`
- **Purpose**: Defines the `plans` catalog table.
- **Why it exists**: Stores plan tiers (e.g. Starter $19/mo, Pro $49/mo, Enterprise $299/mo).
- **Key Fields**: `price` is declared as `Numeric(12, 2)` (fixed-point arithmetic), and `is_active` acts as a feature flag to gracefully discontinue old tiers without breaking historical subscriptions.

#### `app/models/subscription.py`
- **Purpose**: Defines the `subscriptions` table joining `Customer` and `Plan`.
- **Why it exists**: Represents an ongoing contract. Tracks billing frequency periods (`current_period_start`, `current_period_end`) and cancellation timestamps (`cancelled_at`).

#### `app/models/invoice.py`
- **Purpose**: Defines the `invoices` table.
- **Why it exists**: Represents a deterministic point-in-time bill.
- **Key Fields**:
  - `amount_due`: Snapshots the plan price at the time of issuance.
  - `amount_paid`: Accumulates successful payments.
  - `status`: Tracks lifecycle (`issued`, `partially_paid`, `paid`, `cancelled`, `void`).
  - `@property remaining_balance`: Computes `amount_due - amount_paid` dynamically using `Decimal`.

#### `app/models/payment_attempt.py`
- **Purpose**: Defines the `payment_attempts` table.
- **Why it exists**: Separates the *invoice* (what is owed) from the *transaction* (the payment attempt). In the real world, a user might fail twice due to an expired credit card before succeeding on the third attempt. Storing every attempt maintains a 100% accurate audit trail.

#### `app/models/ledger_entry.py`
- **Purpose**: Defines the `ledger_entries` audit log table.
- **Why it exists**: Financial compliance requires an **append-only record** of every debit and credit event. Unlike mutable tables, the ledger cannot be altered after insertion.

---

### 2.3. Validation & DTO Layer

#### `app/schemas/common.py`
- **Purpose**: Standardized API response wrappers (`APIResponse[T]`, `PaginatedResponse[T]`) and `BaseSchema` with `from_attributes = True`.
- **Why it exists**: `from_attributes = True` allows Pydantic v2 to automatically serialize SQLAlchemy ORM models into JSON responses without manual dictionary conversion.

#### `app/schemas/customer.py`, `plan.py`, `subscription.py`, `invoice.py`, `payment.py`, `ledger.py`
- **Purpose**: Separate Request DTOs (`*Create`, `*Update`) from Response DTOs (`*Response`).
- **Why it exists**:
  - **Security (Mass-Assignment Vulnerability Prevention)**: Clients should never be allowed to pass `id`, `amount_paid`, or `created_at` in a request body. DTOs restrict input fields strictly to what the client is permitted to provide.
  - **Domain Validation**: `PlanCreate` validates `price > 0` before any database query is even initiated. `PaymentCreateRequest` validates that `status` must be `"success"` or `"failed"`.

---

### 2.4. Persistence / Repository Layer

#### `app/repositories/base.py`
- **Purpose**: Implements generic `BaseRepository[T]` providing typed CRUD operations (`get_by_id`, `list`, `count`, `create`, `update`, `delete`).
- **Why it exists**: Eliminates repetitive query boilerplate across entities while utilizing Python Generic Types (`TypeVar("T")`).
- **Key Mechanics**: Calls `self.db.flush()` and `self.db.refresh()` so newly generated auto-increment IDs and database defaults are immediately accessible.

#### `app/repositories/customer_repository.py`
- **Purpose**: Specializes in Customer queries.
- **Key Method**: `get_by_email(email)` performs case-insensitive lookups (`ilike`) to guarantee email uniqueness.

#### `app/repositories/plan_repository.py`
- **Purpose**: Specializes in Plan queries.
- **Key Method**: `list_active()` filters plans where `is_active == True`.

#### `app/repositories/subscription_repository.py`
- **Purpose**: Specializes in Subscription queries.
- **Key Method**: `get_active_by_customer_and_plan(customer_id, plan_id)` checks for existing active subscriptions to enforce Business Rule 4.

#### `app/repositories/invoice_repository.py`
- **Purpose**: Specializes in Invoice lookups by customer, subscription, and payment status.

#### `app/repositories/payment_attempt_repository.py`
- **Purpose**: Specializes in Payment Attempt persistence.
- **Key Method**: `get_by_provider_reference(ref)` powers idempotency verification.

#### `app/repositories/ledger_repository.py`
- **Purpose**: Dedicated data access for the financial audit ledger.
- **Crucial Design Choice**: **Explicitly overrides `update()` and `delete()` to raise `BusinessRuleViolationException`**. This architectural guardrail makes it programmatically impossible for any service or developer to mutate or destroy ledger history.

---

### 2.5. Business Logic / Service Layer

#### `app/services/customer_service.py`
- **Role**: Coordinates customer registration and updates.
- **Business Rule Ownership**: Enforces that no two customers share the same email address.

#### `app/services/plan_service.py`
- **Role**: Manages plan creation, pricing validation, and activation status.
- **Business Rule Ownership**: Enforces that plan price must strictly exceed 0.

#### `app/services/subscription_service.py`
- **Role**: Coordinates subscription lifecycle.
- **Business Rule Ownership**:
  1. Validates customer exists.
  2. Validates plan exists.
  3. Enforces that subscription cannot be created on an inactive plan (`InactivePlanException`).
  4. Enforces that a customer cannot hold two active subscriptions to the same plan (`DuplicateActiveSubscriptionException`).
  5. Computes start and end billing period dates.

#### `app/services/invoice_service.py`
- **Role**: Orchestrates the core invoice generation flow.
- **Business Rule Ownership**:
  1. Verifies subscription is currently `active`.
  2. Fetches the plan snapshot price.
  3. Creates the invoice with `amount_due = plan.price` and `amount_paid = 0.00`.
  4. Immediately calls `LedgerService.record_entry()` with `entry_type="invoice_created"`.

#### `app/services/payment_service.py`
- **Role**: Orchestrates payment recording and balance reconciliation.
- **Business Rule Ownership**:
  1. Validates that invoice exists.
  2. Checks for payment idempotency via `provider_reference`.
  3. Verifies invoice is not already paid (`InvoiceAlreadyPaidException`).
  4. For successful payments: verifies `amount <= invoice.remaining_balance` (`InvalidPaymentAmountException`).
  5. Records the `PaymentAttempt` record.
  6. **On Failure**: leaves `amount_paid` unchanged and records `payment_failure` ledger entry.
  7. **On Success**: increments `amount_paid`, advances status to `partially_paid` or `paid`, updates invoice, and records `payment_success` ledger entry.

#### `app/services/ledger_service.py`
- **Role**: Centralized audit writer.
- **Business Rule Ownership**: Appends structured immutable records (`amount`, `currency`, `reference_id`, `description`, `entry_type`).

---

### 2.6. Presentation / API Layer

#### `app/api/deps.py`
- **Purpose**: Central Dependency Injection wiring file.
- **Why it exists**: Uses FastAPI's `Depends` mechanism to compose repositories with the database session, and services with repositories.
- **Significance**: By separating dependency wiring from route handlers, test suites can override `get_db` or any individual service with a single line of code (`app.dependency_overrides`).

#### `app/api/v1/customers.py`, `plans.py`, `subscriptions.py`, `invoices.py`, `payments.py`, `ledger.py`
- **Purpose**: REST endpoints exposing API functionality.
- **Why it exists**: Translates HTTP JSON payloads into validated Pydantic models, calls the corresponding service method, and returns serialized responses with proper HTTP status codes (`201 Created`, `200 OK`).

---

### 2.7. Testing Framework

#### `tests/conftest.py`
- **Purpose**: Pytest configuration, fixtures, and database lifecycle.
- **Why it exists**: Configures an in-memory SQLite database (`sqlite:///:memory:`) using `StaticPool`. Every test run starts with a completely pristine database schema (`create_all` before, `drop_all` after). Overrides FastAPI's `get_db` dependency to ensure API tests run in memory without touching disk.

#### `tests/test_services.py`, `test_repositories.py`, `test_models.py`, `test_api_e2e.py`
- **Purpose**: Complete testing pyramid:
  - **Model Unit Tests**: Test entity representations and property calculations.
  - **Repository Unit Tests**: Test persistence, filters, and append-only immutability.
  - **Service Unit Tests**: Test every single domain business rule in isolation.
  - **E2E Integration Tests**: Test the full HTTP API from customer creation through partial payments to complete invoice fulfillment and audit ledger inspection.

---

## 3. Core Software Engineering Concepts Deep-Dive

### 3.1. Data Mapper (SQLAlchemy) vs Active Record (Django ORM)

| Dimension | Active Record (Django ORM) | Data Mapper (SQLAlchemy + Repository Pattern) |
|---|---|---|
| **Core Concept** | An object represents a single database row AND contains all database persistence methods (`user.save()`, `user.delete()`). | Domain entities are pure Python classes. The database persistence mechanism (`Session`, `Repository`) is completely separated from the entity. |
| **Coupling** | High. Domain models inherit from `models.Model`, making it impossible to use them without Django's runtime and database. | Low. Models are independent mapping declarations. Business services operate on pure attributes. |
| **Transaction Boundary** | Implicit. Calling `.save()` performs immediate writes. Complex multi-table transactions require manual `transaction.atomic()` blocks scattered in views. | Explicit. Unit of Work pattern. Repositories perform `.flush()` within a session, and commit/rollback occurs at the request boundary. |
| **Testability** | Requires mocking the entire Django database engine or hitting a test database. | Repositories can be cleanly swapped with in-memory dicts or mock classes in unit tests. |

**Why SubLedger uses Data Mapper / Repository Pattern**:
Financial and billing engines require strict transaction boundaries and high testability. By decoupling entities from persistence, SubLedger ensures that business calculations (like remaining invoice balance) can never be corrupted by accidental auto-saves.

---

### 3.2. Why `float` is Forbidden in Financial Systems (`Decimal` vs IEEE 754)

In standard computing, floating-point numbers (`float`) follow the **IEEE 754 standard**, which represents numbers using binary fractions ($2^{-1}, 2^{-2}, 2^{-3}\dots$). Because values like $0.1$ or $0.01$ cannot be represented precisely in base-2 binary, rounding errors occur:

```python
# Try this in any Python REPL:
>>> 0.1 + 0.2
0.30000000000000004

>>> 0.1 + 0.2 == 0.3
False
```

In a billing engine:
- If a customer owes `$0.30` and pays `$0.10` followed by `$0.20`, floating-point arithmetic calculates `$0.30 - 0.10 - 0.20 = 0.0000000000000000555...`
- The system would mark the invoice as **unpaid** because the remaining balance is not strictly equal to zero!
- Over millions of transactions, rounding discrepancies lead to unbalanced balance sheets and audit failures.

**How SubLedger Solves This**:
1. All financial fields (`amount_due`, `amount_paid`, `amount`) are declared as `Numeric(12, 2)` in SQLAlchemy and `decimal.Decimal` in Python.
2. In Python, `Decimal("0.1") + Decimal("0.2") == Decimal("0.3")` is mathematically exact.
3. Every payment amount is quantized to two decimal places (`.quantize(Decimal("0.01"))`).

---

### 3.3. The Snapshot Pricing Pattern

Consider this scenario:
1. On **January 1**, Acme Corp subscribes to the "Pro Plan" for **$50.00/month**.
2. An invoice is generated for January: `$50.00`.
3. On **June 1**, the marketing team increases the price of the "Pro Plan" to **$75.00/month**.
4. In **July**, Acme Corp downloads their invoice receipt from January.

**The Flawed Approach**:
The invoice table has a foreign key `plan_id` but *no* `amount_due` column. The code computes the invoice amount dynamically: `invoice.plan.price`.
*Result*: Acme's January invoice retroactively changes from $50 to $75! This violates accounting standards and constitutes illegal tax/financial reporting.

**The SubLedger Snapshot Pattern**:
When `InvoiceService.generate_invoice` runs, it copies the plan price into `invoice.amount_due`:

```python
# Snapshot captured at time of invoice creation:
invoice = Invoice(
    subscription_id=subscription.id,
    customer_id=subscription.customer_id,
    amount_due=plan.price,  # <-- SNAPSHOT COPIED HERE
    amount_paid=Decimal("0.00"),
    status=InvoiceStatus.ISSUED,
)
```
Even if the Plan is edited, re-priced, or deleted later, historical invoices remain 100% immutable and accurate.

---

### 3.4. The Append-Only Audit Ledger Pattern

In traditional CRUD, developers frequently update table columns in place:
`UPDATE accounts SET balance = balance + 100 WHERE id = 1;`

**The Fatal Flaw of In-Place Mutation**:
If the account balance says `$450`, *why* is it $450? Who paid? Did a payment fail? Was there a discount or refund? The historical context is permanently lost. If a database corruption or bug occurs, you cannot reconstruct what happened.

**The Append-Only Ledger Approach**:
1. You never overwrite financial data.
2. Every financial event is written as a new immutable row in `ledger_entries`.
3. In SubLedger:
   - When an invoice is issued $\to$ an `invoice_created` entry is appended.
   - When a payment fails $\to$ a `payment_failure` entry is appended (explaining the decline reason).
   - When a payment succeeds $\to$ a `payment_success` entry is appended with the gateway reference.
4. An auditor can re-calculate account state at any historical timestamp simply by summing ledger entries up to that timestamp.

---

### 3.5. Dependency Injection (DI) and Inversion of Control (IoC)

In tightly coupled code, classes create their own dependencies:

```python
# TIGHTLY COUPLED (Bad Practice):
class InvoiceService:
    def __init__(self):
        self.invoice_repo = InvoiceRepository(SessionLocal())  # Hardcoded dependency!
```

If you want to test `InvoiceService`, you are forced to connect to that hardcoded database.

**SubLedger's Dependency Injection Approach**:

```python
# DECOUPLED VIA DEPENDENCY INVERSION (SubLedger Practice):
class InvoiceService:
    def __init__(self, subscription_repo, plan_repo, invoice_repo, ledger_service):
        self.subscription_repo = subscription_repo
        self.plan_repo = plan_repo
        self.invoice_repo = invoice_repo
        self.ledger_service = ledger_service
```

`InvoiceService` does not know or care *how* `InvoiceRepository` was constructed. In production, FastAPI's `Depends(get_invoice_service)` provides real SQLAlchemy repositories. In unit tests, we can pass mock repositories without touching a real database.

---

### 3.6. Idempotency and Webhook Race Conditions

In payment gateways (Stripe, Razorpay, Adyen), webhooks notify your server when a charge succeeds. Due to network retries, payment gateways often send the exact same webhook **multiple times**.

If your server receives the same webhook twice:
- Without idempotency: `amount_paid` is incremented twice, and the user is credited twice!
- **SubLedger's Solution**: Every payment attempt requires a `provider_reference` (gateway transaction ID). Before processing, `PaymentService` checks:

```python
existing_attempt = self.payment_attempt_repo.get_by_provider_reference(provider_reference)
if existing_attempt and existing_attempt.status == PaymentStatus.SUCCESS:
    raise DuplicateResourceException(
        f"Payment with provider reference '{provider_reference}' was already processed successfully."
    )
```
Duplicate transactions are rejected immediately, protecting against double-billing.

---

## 4. SOLID Principles in Action: Before and After Code Comparisons

### 1. Single Responsibility Principle (SRP)
> *A module should have one, and only one, reason to change.*

- **Violation**: Putting SQL queries, price validation, email uniqueness checking, and HTTP status codes inside a FastAPI route function.
- **SubLedger Implementation**:
  - `PlanCreate` validates input types and `price > 0`.
  - `PlanService` enforces business logic.
  - `PlanRepository` executes database queries.
  - `plans.py` route formats HTTP responses.

---

### 2. Open/Closed Principle (OCP)
> *Software entities should be open for extension, but closed for modification.*

- **SubLedger Implementation**:
  - `BaseRepository[T]` defines reusable query operations. When we needed specialized customer email lookup, we extended `BaseRepository` into `CustomerRepository` without altering a single line of `BaseRepository`.
  - The exception hierarchy extends `SubLedgerException`. When adding new domain errors (like `InvoiceAlreadyPaidException`), we don't modify existing error handling code.

---

### 3. Liskov Substitution Principle (LSP)
> *Objects of a superclass should be replaceable with objects of a subclass without breaking application correctness.*

- **SubLedger Implementation**:
  - `CustomerRepository`, `PlanRepository`, and `InvoiceRepository` can be substituted wherever `BaseRepository` is expected.
  - In `LedgerRepository`, mutation methods (`update`, `delete`) raise semantic domain exceptions rather than silently corrupting data, ensuring that callers cannot violate the append-only invariant.

---

### 4. Interface Segregation Principle (ISP)
> *No client should be forced to depend on methods it does not use.*

- **SubLedger Implementation**:
  - `PaymentService` requires only `invoice_repo`, `payment_attempt_repo`, and `ledger_service`. It is not forced to accept `customer_repo` or `plan_repo`.
  - Schemas are segregated: `CustomerCreate` requires only `name` and `email`; `CustomerResponse` includes `id` and timestamps. Clients creating customers are not forced to provide output fields.

---

### 5. Dependency Inversion Principle (DIP)
> *High-level modules should not depend on low-level modules. Both should depend on abstractions.*

- **SubLedger Implementation**:
  - `InvoiceService` (high-level business rules) does not import database sessions or construct database connections.
  - Repositories are passed into the constructor via dependency injection in `app/api/deps.py`.

---

## 5. Senior Backend Engineer Interview Preparation (SaaS Billing)

Here are the top questions asked in Staff / Senior Backend engineering interviews for billing infrastructure, with answers demonstrating SubLedger's design:

### Q1: "How do you handle partial payments and prevent overpayment race conditions?"
**Answer**:
"In SubLedger, we model `Invoice` with an explicit `amount_due` snapshot and an accumulated `amount_paid`. Before applying a payment, `PaymentService` inspects the dynamic property `remaining_balance = amount_due - amount_paid`. If `attempted_amount > remaining_balance`, the system rejects the transaction with an `InvalidPaymentAmountException`. For high-concurrency environments, we use `SELECT ... FOR UPDATE` (pessimistic locking) on the invoice row within the database transaction to prevent concurrent webhooks from both passing the balance check simultaneously."

### Q2: "Why did you implement an append-only ledger instead of simply updating an account balance?"
**Answer**:
"Directly updating an account balance destroys the historical audit trail and makes forensic reconciliation impossible. In SaaS accounting (ASC 606 / IFRS 15 revenue recognition), businesses must prove every credit and debit event. SubLedger's append-only ledger records `invoice_created`, `payment_success`, and `payment_failure` events with persistent transaction references (`reference_id`). By forbidding updates and deletions at the repository layer, the ledger guarantees complete audit integrity."

### Q3: "What happens if a subscription's plan price changes in the middle of a billing cycle?"
**Answer**:
"SubLedger employs the **Snapshot Pricing Pattern**. When an invoice is generated, the current plan price is copied into `Invoice.amount_due`. Even if the plan is subsequently price-hiked or discontinued (`is_active = False`), existing invoices remain untouched. Future invoices generated for new billing cycles will read the updated plan price."

### Q4: "How does your architecture support multi-gateway redundancy (e.g. Stripe + Razorpay fallback)?"
**Answer**:
"Because `PaymentService` depends on domain abstractions rather than gateway SDKs, payment gateways are treated as external providers. Route handlers or adapter workers normalize gateway webhooks into a standard `PaymentCreateRequest` containing `amount`, `currency`, `provider_reference`, and `status`. The payment attempt repository records the provider reference for idempotency, and the invoice status reconciles identically regardless of which gateway processed the charge."
