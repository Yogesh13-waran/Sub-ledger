from fastapi import APIRouter
from app.api.v1.customers import router as customers_router
from app.api.v1.plans import router as plans_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.invoices import router as invoices_router
from app.api.v1.payments import router as payments_router
from app.api.v1.ledger import router as ledger_router

api_router = APIRouter()
api_router.include_router(customers_router)
api_router.include_router(plans_router)
api_router.include_router(subscriptions_router)
api_router.include_router(invoices_router)
api_router.include_router(payments_router)
api_router.include_router(ledger_router)

