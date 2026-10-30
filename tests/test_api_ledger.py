from fastapi.testclient import TestClient


def test_ledger_api_endpoints_and_queries(client: TestClient):
    # Setup Customer, Plan, Subscription, Invoice, Payment
    c_res = client.post("/api/v1/customers", json={"name": "Audit User", "email": "audit@demo.com"})
    cust_id = c_res.json()["id"]

    p_res = client.post("/api/v1/plans", json={"name": "Audit Plan", "price": "80.00"})
    plan_id = p_res.json()["id"]

    s_res = client.post("/api/v1/subscriptions", json={"customer_id": cust_id, "plan_id": plan_id})
    sub_id = s_res.json()["id"]

    inv_res = client.post("/api/v1/invoices/generate", json={"subscription_id": sub_id})
    inv_id = inv_res.json()["id"]

    pay_res = client.post("/api/v1/payments", json={
        "invoice_id": inv_id,
        "amount": "80.00",
        "status": "success",
        "provider_reference": "TX_AUDIT_FINAL",
    })
    assert pay_res.status_code == 201

    # 1. List Ledger Entries with filters
    list_res = client.get(f"/api/v1/ledger?customer_id={cust_id}")
    assert list_res.status_code == 200
    entries = list_res.json()
    assert len(entries) >= 2  # invoice_created, payment_success

    # 2. Get Ledger Entry by ID
    first_entry_id = entries[0]["id"]
    get_res = client.get(f"/api/v1/ledger/{first_entry_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == first_entry_id

    # 3. Get Ledger Entries by Reference ID
    ref_res = client.get("/api/v1/ledger/reference/TX_AUDIT_FINAL")
    assert ref_res.status_code == 200
    ref_entries = ref_res.json()
    assert len(ref_entries) == 1
    assert ref_entries[0]["reference_id"] == "TX_AUDIT_FINAL"

    # 4. Get non-existent ledger entry -> 404
    not_found = client.get("/api/v1/ledger/99999")
    assert not_found.status_code == 404
