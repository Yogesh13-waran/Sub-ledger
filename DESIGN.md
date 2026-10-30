# SubLedger - Low-Level Design (LLD) Document
**System**: SaaS Subscription, Invoicing & Billing Engine  
**Standard**: SOLID Principles, Clean Layered Architecture, Repository Pattern, Append-Only Financial Ledger

---

## 1. System Overview & Objectives

**SubLedger** is a billing and ledger backend designed for SaaS applications. The system orchestrates customers, recurring plans, lifecycle subscriptions, deterministic invoice generation, payment attempt recording with partial payment reconciliation, and an immutable financial audit ledger.

### Key Architectural Objectives:
1. **Separation of Concerns**: Strict boundary separation across Presentation (Routes), Business Logic (Services), Data Persistence (Repositories), Relational Schemas (Models), and Data Transfer Objects (Pydantic Schemas).
2. **SOLID Compliance**: Systematic adherence to all five SOLID design principles across classes and interfaces.
3. **Data Integrity & Financial Precision**: Use of exact fixed-point decimals (`Numeric(12, 2)` / `decimal.Decimal`) to eliminate floating-point inaccuracies.
4. **Auditability**: An immutable, append-only ledger tracking all revenue and transaction events linked by persistent reference IDs.

---

## 2. Domain Model & Entity Relationships

The domain contains 6 core entities:
- **`Customer`**: Holds account identity and unique email.
- **`Plan`**: Represents a recurring pricing plan with `price > 0`, billing frequency, and active availability.
- **`Subscription`**: Couples a `Customer` to a `Plan` with lifecycle states (`active`, `cancelled`).
- **`Invoice`**: Point-in-time billing document capturing a snapshot of plan pricing (`amount_due`) and cumulative successful payments (`amount_paid`).
- **`PaymentAttempt`**: Records external payment transactions (gateway reference, status, failure reasons).
- **`LedgerEntry`**: Append-only chronological financial record.

### Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    CUSTOMER ||--o{ SUBSCRIPTION : "has many"
    CUSTOMER ||--o{ INVOICE : "billed via"
    CUSTOMER ||--o{ LEDGER_ENTRY : "associated with"
    
    PLAN ||--o{ SUBSCRIPTION : "subscribed to"
    
    SUBSCRIPTION ||--o{ INVOICE : "generates"
    
    INVOICE ||--o{ PAYMENT_ATTEMPT : "receives"
    INVOICE ||--o{ LEDGER_ENTRY : "traces"

    CUSTOMER {
        int id PK
        string name
        string email UK "Unique, Indexed"
        datetime created_at
        datetime updated_at
    }

    PLAN {
        int id PK
        string name
        string description
        numeric price "Strictly > 0"
        string currency "e.g. USD"
        string billing_interval "monthly, yearly"
        boolean is_active "Controls eligibility"
        datetime created_at
        datetime updated_at
    }

    SUBSCRIPTION {
        int id PK
        int customer_id FK
        int plan_id FK
        string status "active, cancelled"
        datetime start_date
        datetime current_period_start
        datetime current_period_end
        datetime cancelled_at
        datetime created_at
        datetime updated_at
    }

    INVOICE {
        int id PK
        int subscription_id FK
        int customer_id FK
        numeric amount_due "Plan price snapshot"
        numeric amount_paid "Default 0.00"
        string currency
        string status "issued, partially_paid, paid, cancelled"
        datetime period_start
        datetime period_end
        datetime due_date
        datetime created_at
        datetime updated_at
    }

    PAYMENT_ATTEMPT {
        int id PK
        int invoice_id FK
        numeric amount "Strictly > 0"
        string currency
        string status "success, failed, pending"
        string provider_reference "Gateway TX ID, Indexed"
        string failure_reason
        datetime created_at
    }

    LEDGER_ENTRY {
        int id PK
        int customer_id FK "Nullable"
        int invoice_id FK "Nullable"
        string entry_type "invoice_created, payment_success, payment_failure"
        numeric amount
        string currency
        string reference_id "Traceable Ref ID, Indexed"
        string description
        datetime created_at "Append-only timestamp"
    }
```

---

## 3. Layered Architecture

SubLedger employs a classic 4-Tier Clean Architecture:

```mermaid
flowchart TD
    Client(["HTTP Client / Frontend / Webhooks"]) -->|JSON Request| API["Presentation Layer (app/api/v1)"]
    
    subgraph Presentation ["Presentation Layer"]
        API --> Controllers["FastAPI APIRouters\n• customers.py\n• plans.py\n• subscriptions.py\n• invoices.py\n• payments.py\n• ledger.py"]
        Schemas["Pydantic DTOs (app/schemas)\n• Validation & Serialization\n• Positive price / amount checks"]
        Controllers -.-> Schemas
    end

    Controllers -->|Depends(get_service)| Services["Service Layer (app/services)"]
    
    subgraph BusinessLogic ["Business Logic Layer"]
        Services --> CustServ["CustomerService"]
        Services --> PlanServ["PlanService"]
        Services --> SubServ["SubscriptionService"]
        Services --> InvServ["InvoiceService"]
        Services --> PayServ["PaymentService"]
        Services --> LedgServ["LedgerService"]
    end

    BusinessLogic -->|Injected Repositories| Repositories["Data Access Layer (app/repositories)"]

    subgraph DataAccess ["Repository Layer"]
        Repositories --> BaseRepo["BaseRepository[T]"]
        Repositories --> CustRepo["CustomerRepository"]
        Repositories --> PlanRepo["PlanRepository"]
        Repositories --> SubRepo["SubscriptionRepository"]
        Repositories --> InvRepo["InvoiceRepository"]
        Repositories --> PayRepo["PaymentAttemptRepository"]
        Repositories --> LedgRepo["LedgerRepository (Append-Only)"]
    end

    DataAccess -->|SQLAlchemy Sessions| Database[("Database Engine\n• SQLite / PostgreSQL\n• ACID Transactions")]
```

---

## 4. Sequence Diagrams for Core Flows

### 4.1. Flow 1: Invoice Generation Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as API Consumer / Cron
    participant Route as invoices.py (Router)
    participant Service as InvoiceService
    participant SubRepo as SubscriptionRepository
    participant PlanRepo as PlanRepository
    participant InvRepo as InvoiceRepository
    participant LedgService as LedgerService
    participant DB as Database Session

    Client->>Route: POST /api/v1/invoices/generate {subscription_id: 10}
    Route->>Service: generate_invoice(subscription_id=10)
    Service->>SubRepo: get_by_id(10)
    SubRepo->>DB: SELECT * FROM subscriptions WHERE id = 10
    DB-->>SubRepo: Subscription record
    SubRepo-->>Service: subscription
    
    alt Subscription not found
        Service-->>Route: Raise EntityNotFoundException(404)
        Route-->>Client: 404 Not Found
    else Subscription is inactive/cancelled
        Service-->>Route: Raise BusinessRuleViolationException(400)
        Route-->>Client: 400 Bad Request ("Subscription is cancelled")
    end

    Service->>PlanRepo: get_by_id(subscription.plan_id)
    PlanRepo->>DB: SELECT * FROM plans WHERE id = plan_id
    DB-->>PlanRepo: Plan record
    PlanRepo-->>Service: plan

    Note over Service: Snapshot Pricing Calculation:<br/>amount_due = plan.price<br/>period = billing cycle dates

    Service->>InvRepo: create(Invoice(amount_due=plan.price, status="issued"))
    InvRepo->>DB: INSERT INTO invoices ...
    DB-->>InvRepo: Persisted Invoice (id=101)
    InvRepo-->>Service: invoice

    Service->>LedgService: record_entry(type="invoice_created", amount=invoice.amount_due, ref="INV-101")
    LedgService->>DB: INSERT INTO ledger_entries ...
    DB-->>LedgService: Persisted Ledger Entry

    Service-->>Route: invoice
    Route-->>Client: 201 Created (InvoiceResponse JSON)
```

---

### 4.2. Flow 2: Payment Recording Flow

```mermaid
sequenceDiagram
    autonumber
    actor Gateway as Payment Gateway Webhook / User
    participant Route as payments.py (Router)
    participant Service as PaymentService
    participant InvRepo as InvoiceRepository
    participant PayRepo as PaymentAttemptRepository
    participant LedgService as LedgerService
    participant DB as Database Session

    Gateway->>Route: POST /api/v1/payments {invoice_id: 101, amount: 40.00, status: "success", ref: "TX_1"}
    Route->>Service: record_payment(invoice_id, amount, status, ref)
    Service->>InvRepo: get_by_id(101)
    InvRepo->>DB: SELECT * FROM invoices WHERE id = 101
    DB-->>InvRepo: Invoice record (due: 100.00, paid: 0.00)
    InvRepo-->>Service: invoice

    alt Invoice does not exist
        Service-->>Route: Raise EntityNotFoundException(404)
    else Invoice is already paid (status == "paid")
        Service-->>Route: Raise InvoiceAlreadyPaidException(400)
    else Attempted amount > remaining balance (100.00)
        Service-->>Route: Raise InvalidPaymentAmountException(400)
    end

    Service->>PayRepo: create(PaymentAttempt(amount=40.00, status="success", ref="TX_1"))
    PayRepo->>DB: INSERT INTO payment_attempts ...
    DB-->>PayRepo: Persisted Attempt (id=501)
    PayRepo-->>Service: payment_attempt

    alt Payment Status == "failed"
        Note over Service: Failed payment: DO NOT modify amount_paid!
        Service->>LedgService: record_entry(type="payment_failure", amount=40.00, ref="TX_1")
        LedgService->>DB: INSERT INTO ledger_entries ...
        Service-->>Route: (payment_attempt, invoice)
    else Payment Status == "success"
        Note over Service: Reconcile Invoice Balance:<br/>amount_paid += 40.00 (now 40.00)<br/>remaining = 60.00 > 0 -> status = "partially_paid"
        Service->>InvRepo: update(invoice)
        InvRepo->>DB: UPDATE invoices SET amount_paid=40.00, status='partially_paid'
        Service->>LedgService: record_entry(type="payment_success", amount=40.00, ref="TX_1")
        LedgService->>DB: INSERT INTO ledger_entries ...
        Service-->>Route: (payment_attempt, updated_invoice)
    end

    Route-->>Gateway: 201 Created (PaymentResultResponse JSON)
```

---

## 5. State Machine Diagrams

### 5.1. Invoice Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> DRAFT : Created as Draft
    [*] --> ISSUED : Generated from Active Subscription
    DRAFT --> ISSUED : Finalized
    ISSUED --> PARTIALLY_PAID : Successful payment (amount < remaining_balance)
    PARTIALLY_PAID --> PARTIALLY_PAID : Additional partial payment (amount < remaining_balance)
    PARTIALLY_PAID --> PAID : Final payment (amount == remaining_balance)
    ISSUED --> PAID : Full payment in single transaction (amount == amount_due)
    ISSUED --> CANCELLED : Admin void/cancellation
    PARTIALLY_PAID --> VOID : Write-off/Refund
    PAID --> [*]
    CANCELLED --> [*]
    VOID --> [*]
```

### 5.2. Subscription Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : Subscribed to Active Plan
    ACTIVE --> PAUSED : Customer pauses account
    PAUSED --> ACTIVE : Customer resumes
    ACTIVE --> CANCELLED : Subscription cancelled (cancelled_at set)
    PAUSED --> CANCELLED : Cancelled while paused
    ACTIVE --> EXPIRED : Period passed without renewal
    CANCELLED --> [*]
    EXPIRED --> [*]
```

---

## 6. SOLID Principles Mapping & Implementation Proof

| Principle | Name | Where & How Applied in SubLedger |
|---|---|---|
| **S** | **Single Responsibility Principle (SRP)** | • **Routes** (`app/api/v1/*`): Responsible *only* for HTTP status codes, request parsing, and delegating to services.<br>• **Services** (`app/services/*`): Responsible *only* for business logic rules and orchestrating repositories.<br>• **Repositories** (`app/repositories/*`): Responsible *only* for database queries and ORM persistence.<br>• **Models** (`app/models/*`): Responsible *only* for database table schema and column mapping.<br>• **Schemas** (`app/schemas/*`): Responsible *only* for input validation and output serialization. |
| **O** | **Open/Closed Principle (OCP)** | • Repositories inherit from generic `BaseRepository[T]`. Concrete repositories extend functionality without modifying the base class.<br>• Custom exception hierarchy (`SubLedgerException`) permits adding new domain errors without modifying API handlers.<br>• Payment gateways can be extended via strategy patterns without altering `PaymentService`. |
| **L** | **Liskov Substitution Principle (LSP)** | • Concrete repositories (`CustomerRepository`, `PlanRepository`, etc.) can be substituted wherever `BaseRepository` is expected.<br>• In `LedgerRepository`, mutation methods (`update`, `delete`) explicitly reject modification to protect the immutable domain invariant while maintaining full interface compatibility. |
| **I** | **Interface Segregation Principle (ISP)** | • Services only declare and inject the exact repositories they need (e.g. `InvoiceService` takes `subscription_repo`, `plan_repo`, `invoice_repo`, `ledger_service`; it does not receive unrelated customer or payment repositories).<br>• Pydantic schemas segregate Create, Update, and Response views. |
| **D** | **Dependency Inversion Principle (DIP)** | • High-level modules (Services) do not create low-level dependencies (`Session`, raw SQL). Instead, dependencies are injected into constructors (`__init__`).<br>• FastAPI's `Depends()` provider layer (`app/api/deps.py`) manages dependency resolution and enables effortless mocking in test suites (`conftest.py`). |

---

## 7. Business Rule Ownership Matrix

| Business Rule | Owner (Entity / Service / Schema) | Enforcement Mechanism |
|---|---|---|
| **Plan price must be > 0** | `PlanCreate` Schema & `PlanService` | Pydantic `@field_validator("price")` + `PlanService.create_plan` condition check |
| **Customer email must be unique** | `Customer` Model & `CustomerService` | Database unique constraint + `CustomerRepository.get_by_email()` check raising `DuplicateResourceException` |
| **Cannot subscribe to inactive plan** | `SubscriptionService` | `Plan.is_active` check raising `InactivePlanException` |
| **No duplicate active subscription to same plan** | `SubscriptionService` | `SubscriptionRepository.get_active_by_customer_and_plan()` raising `DuplicateActiveSubscriptionException` |
| **Invoice amount_due from plan price at creation** | `InvoiceService` | Point-in-time snapshot of `plan.price` copied to `invoice.amount_due` |
| **Payment cannot exceed unpaid balance** | `PaymentService` | `amount <= invoice.remaining_balance` validation raising `InvalidPaymentAmountException` |
| **Invoice status moves to paid / partially_paid** | `PaymentService` | State transition logic comparing updated `amount_paid` to `amount_due` |
| **Failed payment does not increase amount_paid** | `PaymentService` | Explicit branch: only persist `PaymentAttempt` and emit `payment_failure` ledger event |
| **Append-only traceable ledger** | `LedgerRepository` & `LedgerService` | Explicit disallowing of `update` and `delete` in repository; `reference_id` indexing on each event |

