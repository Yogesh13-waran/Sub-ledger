"""
SubLedger - Complete End-to-End System Demonstration Script
Executes the full SaaS billing and subscription lifecycle in sequential order.
Run with: python run_e2e_demo.py
"""

import sys
import json
from decimal import Decimal

# Ensure safe output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

client = TestClient(app)

SEPARATOR = "=" * 70


def print_step(step_num: int, title: str, description: str):
    print(f"\n{SEPARATOR}")
    print(f">> STEP {step_num}: {title.upper()}")
    print(f"   {description}")
    print(SEPARATOR)


def print_json(data):
    print(json.dumps(data, indent=2, default=str))


def run_demo():
    # Ensure fresh tables for demo
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    print("\n========================================================")
    print("   STARTING SUBLEDGER FULL END-TO-END SYSTEM DEMO       ")
    print("========================================================\n")

    # 1. Health check
    print_step(1, "System Health Check", "Verify the API backend is healthy and responding.")
    res = client.get("/health")
    print(f"Status Code: {res.status_code}")
    print_json(res.json())
    assert res.status_code == 200

    # 2. Register Customer
    print_step(2, "Register Customer", "Create a new subscriber account with unique email.")
    res = client.post("/api/v1/customers", json={
        "name": "Starlight Technologies Inc.",
        "email": "finance@starlight.io"
    })
    print(f"Status Code: {res.status_code}")
    customer = res.json()
    print_json(customer)
    assert res.status_code == 201
    customer_id = customer["id"]

    # 3. Test Duplicate Email Rule
    print_step(3, "Business Rule: Unique Email Enforcement", "Attempt to register the same email again.")
    res = client.post("/api/v1/customers", json={
        "name": "Impostor Starlight",
        "email": "FINANCE@starlight.io"
    })
    print(f"Status Code: {res.status_code} (Expected 409 Conflict)")
    print_json(res.json())
    assert res.status_code == 409
    print("[PASS] Successfully rejected duplicate customer email!")

    # 4. Create Plans
    print_step(4, "Create Pricing Plans", "Create an active plan ($75.00/mo) and an inactive legacy plan.")
    res = client.post("/api/v1/plans", json={
        "name": "Pro Business",
        "description": "Full access to SaaS billing suite",
        "price": "75.00",
        "currency": "USD",
        "billing_interval": "monthly",
        "is_active": True
    })
    plan = res.json()
    plan_id = plan["id"]
    print(f"Active Plan Created (ID: {plan_id}, Price: ${plan['price']}):")
    print_json(plan)
    assert res.status_code == 201

    res_inactive = client.post("/api/v1/plans", json={
        "name": "Legacy Alpha Plan",
        "description": "Discontinued tier",
        "price": "25.00",
        "currency": "USD",
        "billing_interval": "monthly",
        "is_active": False
    })
    inactive_plan = res_inactive.json()
    inactive_plan_id = inactive_plan["id"]
    print(f"\nInactive Plan Created (ID: {inactive_plan_id}, Active: {inactive_plan['is_active']})")

    # 5. Test Inactive Plan Subscription Rule
    print_step(5, "Business Rule: Inactive Plan Guard", "Attempt to create a subscription for the inactive plan.")
    res = client.post("/api/v1/subscriptions", json={
        "customer_id": customer_id,
        "plan_id": inactive_plan_id
    })
    print(f"Status Code: {res.status_code} (Expected 400 Bad Request)")
    print_json(res.json())
    assert res.status_code == 400
    print("[PASS] Successfully prevented subscription to inactive plan!")

    # 6. Create Active Subscription
    print_step(6, "Create Active Subscription", "Subscribe customer to 'Pro Business' plan.")
    res = client.post("/api/v1/subscriptions", json={
        "customer_id": customer_id,
        "plan_id": plan_id
    })
    print(f"Status Code: {res.status_code}")
    subscription = res.json()
    print_json(subscription)
    assert res.status_code == 201
    subscription_id = subscription["id"]

    # 7. Test Duplicate Active Subscription Rule
    print_step(7, "Business Rule: Single Active Subscription Guard", "Attempt to create a 2nd active subscription to the same plan.")
    res = client.post("/api/v1/subscriptions", json={
        "customer_id": customer_id,
        "plan_id": plan_id
    })
    print(f"Status Code: {res.status_code} (Expected 409 Conflict)")
    print_json(res.json())
    assert res.status_code == 409
    print("[PASS] Successfully prevented duplicate active subscription!")

    # 8. Generate Invoice (Core Flow 1)
    print_step(8, "Generate Invoice (Snapshot Pricing Flow)", "Generate monthly invoice from subscription. Snapshots plan price.")
    res = client.post("/api/v1/invoices/generate", json={
        "subscription_id": subscription_id
    })
    print(f"Status Code: {res.status_code}")
    invoice = res.json()
    print_json(invoice)
    assert res.status_code == 201
    invoice_id = invoice["id"]
    assert invoice["amount_due"] == "75.00"
    assert invoice["amount_paid"] == "0.00"
    assert invoice["remaining_balance"] == "75.00"
    assert invoice["status"] == "issued"
    print("[PASS] Invoice generated with status 'issued' and amount_due snapshotted at $75.00!")

    # 9. Record Failed Payment Attempt (Core Flow 2 - Failure Branch)
    print_step(9, "Record Failed Payment Attempt", "Simulate a declined card transaction. Verifies amount_paid remains 0.")
    res = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "75.00",
        "currency": "USD",
        "status": "failed",
        "provider_reference": "TX_GW_DECLINED_999",
        "failure_reason": "Card expired / insufficient funds"
    })
    print(f"Status Code: {res.status_code}")
    pay_fail = res.json()
    print_json(pay_fail)
    assert pay_fail["payment_attempt"]["status"] == "failed"
    assert pay_fail["invoice"]["amount_paid"] == "0.00"
    assert pay_fail["invoice"]["status"] == "issued"
    print("[PASS] Failed payment recorded! Invoice amount_paid remains $0.00 without mutation.")

    # 10. Test Overpayment Protection Rule
    print_step(10, "Business Rule: Overpayment Protection", "Attempt to pay $120.00 when only $75.00 is due.")
    res = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "120.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_OVERPAY_ATTEMPT"
    })
    print(f"Status Code: {res.status_code} (Expected 400 Bad Request)")
    print_json(res.json())
    assert res.status_code == 400
    print("[PASS] Successfully blocked payment exceeding remaining invoice balance!")

    # 11. Record Partial Payment ($30.00 of $75.00)
    print_step(11, "Record Partial Payment ($30.00)", "Applies partial payment. Verifies invoice moves to 'partially_paid'.")
    res = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "30.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_PARTIAL_PAY_30"
    })
    print(f"Status Code: {res.status_code}")
    part_result = res.json()
    print_json(part_result)
    assert part_result["invoice"]["amount_paid"] == "30.00"
    assert part_result["invoice"]["remaining_balance"] == "45.00"
    assert part_result["invoice"]["status"] == "partially_paid"
    print("[PASS] Partial payment applied! Status is now 'partially_paid', remaining balance: $45.00.")

    # 12. Record Final Payment ($45.00)
    print_step(12, "Record Final Payment ($45.00)", "Applies remaining balance. Verifies invoice transitions to 'paid'.")
    res = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "45.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_FINAL_PAY_45"
    })
    print(f"Status Code: {res.status_code}")
    final_result = res.json()
    print_json(final_result)
    assert final_result["invoice"]["amount_paid"] == "75.00"
    assert final_result["invoice"]["remaining_balance"] == "0.00"
    assert final_result["invoice"]["status"] == "paid"
    print("[PASS] Final payment applied! Invoice is now fully 'paid'!")

    # 13. Test Payment on Already Paid Invoice Rule
    print_step(13, "Business Rule: Guard Paid Invoices", "Attempt another payment on the fully paid invoice.")
    res = client.post("/api/v1/payments", json={
        "invoice_id": invoice_id,
        "amount": "10.00",
        "currency": "USD",
        "status": "success",
        "provider_reference": "TX_EXTRA_POST_PAID"
    })
    print(f"Status Code: {res.status_code} (Expected 400 Bad Request)")
    print_json(res.json())
    assert res.status_code == 400
    print("[PASS] Successfully prevented payments on already paid invoice!")

    # 14. Cancel Subscription
    print_step(14, "Cancel Subscription", "Cancel customer subscription, setting status to 'cancelled'.")
    res = client.post(f"/api/v1/subscriptions/{subscription_id}/cancel")
    print(f"Status Code: {res.status_code}")
    cancelled_sub = res.json()
    print_json(cancelled_sub)
    assert cancelled_sub["status"] == "cancelled"
    print("[PASS] Subscription successfully cancelled!")

    # 15. Retrieve Audit Ledger Trail
    print_step(15, "Verify Append-Only Audit Ledger", "Inspect complete chronological financial audit trail for this invoice.")
    res = client.get(f"/api/v1/ledger?invoice_id={invoice_id}")
    print(f"Status Code: {res.status_code}")
    entries = res.json()
    print_json(entries)
    assert len(entries) == 4
    print("\nAudit Ledger Events Summary:")
    for idx, e in enumerate(reversed(entries), 1):
        print(f"  {idx}. [{e['created_at']}] Type: {e['entry_type']} | Amount: ${e['amount']} | Ref: {e['reference_id']}")
        print(f"     Description: {e['description']}")

    print(f"\n{SEPARATOR}")
    print("[SUCCESS] ALL 15 END-TO-END STEPS AND BUSINESS RULES PASSED PERFECTLY!")
    print(SEPARATOR + "\n")


if __name__ == "__main__":
    run_demo()
