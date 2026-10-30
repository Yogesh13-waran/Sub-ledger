from fastapi.testclient import TestClient


def test_payment_api_endpoints_and_history(client: TestClient):
    # Setup Customer, Plan, Subscription, Invoice
    c_res = client.post("/api/v1/customers", json={"name": "Payer", "email": "payer@demo.com"})
    cust_id = c_res.json()["id"]

    p_res = client.post("/api/v1/plans", json={"name": "Pay Plan", "price": "100.00"})
    plan_id = p_res.json()["id"]

    s_res = client.post("/api/v1/subscriptions", json={"customer_id": cust_id, "plan_id": plan_id})
    sub_id = s_res.json()["id"]

    inv_res = client.post("/api/v1/invoices/generate", json={"subscription_id": sub_id})
    inv_id = inv_res.json()["id"]

    # 1. Failed payment attempt
    fail_res = client.post("/api/v1/payments", json={
        "invoice_id": inv_id,
        "amount": "100.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "TX_TEST_FAIL",
        "failure_reason": "Insufficient funds",
    })
    assert fail_res.status_code == 201
    assert fail_res.json()["payment_attempt"]["status"] == "failed"

    # 2. Successful payment
    succ_res = client.post("/api/v1/payments", json={
        "invoice_id": inv_id,
        "amount": "50.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_TEST_SUCC",
    })
    assert succ_res.status_code == 201
    assert succ_res.json()["invoice"]["status"] == "partially_paid"

    # 3. List Payments for Invoice
    history_res = client.get(f"/api/v1/payments/invoice/{inv_id}")
    assert history_res.status_code == 200
    attempts = history_res.json()
    assert len(attempts) == 2
    refs = [a["provider_reference"] for a in attempts]
    assert "TX_TEST_FAIL" in refs
    assert "TX_TEST_SUCC" in refs

    # 4. Duplicate provider reference rejection
    dup_ref = client.post("/api/v1/payments", json={
        "invoice_id": inv_id,
        "amount": "10.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_TEST_SUCC",
    })
    assert dup_ref.status_code == 409
