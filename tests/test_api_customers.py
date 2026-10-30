from fastapi.testclient import TestClient


def test_customer_api_full_crud(client: TestClient):
    # 1. Create
    res = client.post("/api/v1/customers", json={"name": "Alice Corp", "email": "alice@corp.com"})
    assert res.status_code == 201
    cust = res.json()
    cust_id = cust["id"]
    assert cust["name"] == "Alice Corp"
    assert cust["email"] == "alice@corp.com"

    # 2. Get by ID
    get_res = client.get(f"/api/v1/customers/{cust_id}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "alice@corp.com"

    # 3. List
    list_res = client.get("/api/v1/customers")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 4. Patch (Update)
    patch_res = client.patch(f"/api/v1/customers/{cust_id}", json={"name": "Alice Global Inc."})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Alice Global Inc."

    # 5. Get 404 for non-existent
    not_found = client.get("/api/v1/customers/99999")
    assert not_found.status_code == 404
