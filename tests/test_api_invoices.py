from fastapi.testclient import TestClient


def test_invoice_api_endpoints_and_queries(client: TestClient):
    # Setup Customer, Plan, Subscription
    c_res = client.post("/api/v1/customers", json={"name": "Inv Client", "email": "inv@client.com"})
    cust_id = c_res.json()["id"]

    p_res = client.post("/api/v1/plans", json={"name": "Tier A", "price": "60.00"})
    plan_id = p_res.json()["id"]

    s_res = client.post("/api/v1/subscriptions", json={"customer_id": cust_id, "plan_id": plan_id})
    sub_id = s_res.json()["id"]

    # 1. Generate Invoice
    inv_res = client.post("/api/v1/invoices/generate", json={"subscription_id": sub_id})
    assert inv_res.status_code == 201
    invoice = inv_res.json()
    inv_id = invoice["id"]
    assert invoice["amount_due"] == "60.00"
    assert invoice["status"] == "issued"

    # 2. Get Invoice by ID
    get_res = client.get(f"/api/v1/invoices/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == inv_id

    # 3. List Invoices with filter
    list_res = client.get(f"/api/v1/invoices?customer_id={cust_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Generate Invoice for non-existent subscription -> 404
    not_found_sub = client.post("/api/v1/invoices/generate", json={"subscription_id": 99999})
    assert not_found_sub.status_code == 404

    # 5. Get non-existent invoice -> 404
    not_found_inv = client.get("/api/v1/invoices/99999")
    assert not_found_inv.status_code == 404
