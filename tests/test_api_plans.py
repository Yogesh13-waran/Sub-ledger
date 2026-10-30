from fastapi.testclient import TestClient


def test_plan_api_full_crud_and_filters(client: TestClient):
    # 1. Create Active Plan
    res = client.post("/api/v1/plans", json={
        "name": "Standard Plan",
        "description": "Mid-tier",
        "price": "39.99",
        "currency": "USD",
        "billing_interval": "monthly",
        "is_active": True,
    })
    assert res.status_code == 201
    plan_id = res.json()["id"]

    # 2. Create Inactive Plan
    res_inact = client.post("/api/v1/plans", json={
        "name": "Retired Plan",
        "price": "9.99",
        "is_active": False,
    })
    assert res_inact.status_code == 201

    # 3. Get by ID
    get_res = client.get(f"/api/v1/plans/{plan_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Standard Plan"

    # 4. List Active Only
    act_res = client.get("/api/v1/plans?active_only=true")
    assert act_res.status_code == 200
    names = [p["name"] for p in act_res.json()]
    assert "Standard Plan" in names
    assert "Retired Plan" not in names

    # 5. Patch (Update price and description)
    patch_res = client.patch(f"/api/v1/plans/{plan_id}", json={"price": "45.00", "description": "Updated price"})
    assert patch_res.status_code == 200
    assert patch_res.json()["price"] == "45.00"

    # 6. Non-existent plan -> 404
    not_found = client.get("/api/v1/plans/99999")
    assert not_found.status_code == 404
