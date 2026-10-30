from fastapi.testclient import TestClient


def test_health_and_root(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"


def test_complete_billing_lifecycle_e2e(client: TestClient):
    """
    End-to-End integration test covering the entire SaaS billing lifecycle:
    1. Register customer
    2. Create active and inactive plans
    3. Attempt subscription to inactive plan (fails with 400)
    4. Create active subscription
    5. Attempt duplicate subscription to same plan (fails with 409)
    6. Generate invoice for subscription (verifies snapshot pricing and invoice_created ledger entry)
    7. Record failed payment (verifies status 201, invoice unpaid, ledger failure entry)
    8. Attempt overpayment (fails with 400)
    9. Record partial payment (verifies status moves to partially_paid)
    10. Record remaining payment (verifies status moves to paid)
    11. Attempt additional payment on paid invoice (fails with 400)
    12. Cancel subscription
    13. Verify comprehensive ledger audit trail
    """
    # 1. Register customer
    cust_res = client.post("/api/v1/customers", json={"name": "Starlight SaaS", "email": "finance@starlight.io"})
    assert cust_res.status_code == 201
    customer_id = cust_res.json()["id"]

    # 1b. Duplicate customer email
    dup_cust = client.post("/api/v1/customers", json={"name": "Duplicate", "email": "FINANCE@starlight.io"})
    assert dup_cust.status_code == 409

    # 2. Create Plans
    plan_res = client.post("/api/v1/plans", json={
        "name": "Enterprise Plan",
        "price": "100.00",
        "currency": "USD",
        "billing_interval": "monthly",
        "is_active": True,
    })
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    inactive_plan_res = client.post("/api/v1/plans", json={
        "name": "Deprecated Plan",
        "price": "20.00",
        "currency": "USD",
        "billing_interval": "monthly",
        "is_active": False,
    })
    assert inactive_plan_res.status_code == 201
    inactive_plan_id = inactive_plan_res.json()["id"]

    # 2b. Plan with price 0 fails
    zero_price = client.post("/api/v1/plans", json={"name": "Zero", "price": "0.00"})
    assert zero_price.status_code == 422

    # 3. Attempt subscription to inactive plan -> 400
    sub_fail = client.post("/api/v1/subscriptions", json={"customer_id": customer_id, "plan_id": inactive_plan_id})
    assert sub_fail.status_code == 400
    assert "inactive" in sub_fail.json()["message"].lower()

    # 4. Create active subscription
    sub_res = client.post("/api/v1/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    assert sub_res.status_code == 201
    subscription_id = sub_res.json()["id"]

    # 5. Attempt duplicate subscription to same plan -> 409
    dup_sub = client.post("/api/v1/subscriptions", json={"customer_id": customer_id, "plan_id": plan_id})
    assert dup_sub.status_code == 409
    assert "already has an active subscription" in dup_sub.json()["message"].lower()

    # 6. Generate Invoice
    inv_res = client.post("/api/v1/invoices/generate", json={"subscription_id": subscription_id})
    assert inv_res.status_code == 201
    invoice = inv_res.json()
    invoice_id = invoice["id"]
    assert invoice["amount_due"] == "100.00"
    assert invoice["amount_paid"] == "0.00"
    assert invoice["remaining_balance"] == "100.00"
    assert invoice["status"] == "issued"

    # 7. Record Failed Payment
    pay_fail = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "100.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "TX_GATEWAY_FAIL_1",
        "failure_reason": "Card expired",
    })
    assert pay_fail.status_code == 201
    assert pay_fail.json()["payment_attempt"]["status"] == "failed"
    assert pay_fail.json()["invoice"]["amount_paid"] == "0.00"
    assert pay_fail.json()["invoice"]["status"] == "issued"

    # 8. Attempt Overpayment -> 400
    overpay = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "150.00",
        "status": "success",
        "provider_reference": "TX_OVERPAY",
    })
    assert overpay.status_code == 400
    assert "exceeds" in overpay.json()["message"].lower()

    # 9. Record Partial Payment ($40.00)
    pay_part = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "40.00",
        "status": "success",
        "provider_reference": "TX_SUCCESS_PART",
    })
    assert pay_part.status_code == 201
    assert pay_part.json()["invoice"]["amount_paid"] == "40.00"
    assert pay_part.json()["invoice"]["remaining_balance"] == "60.00"
    assert pay_part.json()["invoice"]["status"] == "partially_paid"

    # 10. Record Remaining Payment ($60.00)
    pay_full = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "60.00",
        "status": "success",
        "provider_reference": "TX_SUCCESS_FULL",
    })
    assert pay_full.status_code == 201
    assert pay_full.json()["invoice"]["amount_paid"] == "100.00"
    assert pay_full.json()["invoice"]["remaining_balance"] == "0.00"
    assert pay_full.json()["invoice"]["status"] == "paid"

    # 11. Additional Payment Attempt on Paid Invoice -> 400
    extra_pay = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "10.00",
        "status": "success",
        "provider_reference": "TX_EXTRA",
    })
    assert extra_pay.status_code == 400
    assert "already fully paid" in extra_pay.json()["message"].lower()

    # 12. Cancel Subscription
    cancel_res = client.post(f"/api/v1/subscriptions/{subscription_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 13. Audit Ledger Verification
    ledger_res = client.get("/api/v1/ledger", params={"invoice_id": invoice_id})
    assert ledger_res.status_code == 200
    entries = ledger_res.json()
    assert len(entries) == 4  # invoice_created, payment_failure, payment_success (part), payment_success (full)
    entry_types = [e["entry_type"] for e in entries]
    assert "invoice_created" in entry_types
    assert "payment_failure" in entry_types
    assert "payment_success" in entry_types
