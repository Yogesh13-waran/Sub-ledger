from fastapi.testclient import TestClient


def test_subscription_api_endpoints_and_lifecycle(client: TestClient):
    # Setup Customer & Plan
    c_res = client.post("/api/v1/customers", json={"name": "Sub User", "email": "subuser@corp.com"})
    cust_id = c_res.json()["id"]

    p_res = client.post("/api/v1/plans", json={"name": "Dev Plan", "price": "15.00"})
    plan_id = p_res.json()["id"]

    # 1. Create Subscription
    sub_res = client.post("/api/v1/subscriptions", json={"customer_id": cust_id, "plan_id": plan_id})
    assert sub_res.status_code == 201
    sub_id = sub_res.json()["id"]
    assert sub_res.json()["status"] == "active"

    # 2. Get Subscription by ID
    get_res = client.get(f"/api/v1/subscriptions/{sub_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == sub_id

    # 3. List Subscriptions with customer filter
    list_res = client.get(f"/api/v1/subscriptions?customer_id={cust_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 4. Cancel Subscription
    cancel_res = client.post(f"/api/v1/subscriptions/{sub_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
    assert cancel_res.json()["cancelled_at"] is not None

    # 5. Cancel already cancelled -> 400
    cancel_dup = client.post(f"/api/v1/subscriptions/{sub_id}/cancel")
    assert cancel_dup.status_code == 400

    # 6. Non-existent subscription -> 404
    not_found = client.get("/api/v1/subscriptions/99999")
    assert not_found.status_code == 404
