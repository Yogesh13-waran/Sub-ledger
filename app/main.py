from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import (
    SubLedgerException,
    EntityNotFoundException,
    DuplicateResourceException,
    BusinessRuleViolationException,
    InactivePlanException,
    DuplicateActiveSubscriptionException,
    InvalidPaymentAmountException,
    InvoiceAlreadyPaidException,
)
from app.db import init_db
from app.api.v1.api_router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: initialize DB tables on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "SubLedger is a clean, production-grade SaaS Subscription & Billing System backend "
        "designed with Domain-Driven Design, Repository Pattern, and SOLID Principles."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Global Exception Handlers ---

@app.exception_handler(EntityNotFoundException)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "success": False,
            "error_type": "EntityNotFoundException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(DuplicateResourceException)
async def duplicate_resource_handler(request: Request, exc: DuplicateResourceException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error_type": "DuplicateResourceException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(DuplicateActiveSubscriptionException)
async def duplicate_subscription_handler(request: Request, exc: DuplicateActiveSubscriptionException):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "success": False,
            "error_type": "DuplicateActiveSubscriptionException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(InactivePlanException)
async def inactive_plan_handler(request: Request, exc: InactivePlanException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "InactivePlanException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(InvalidPaymentAmountException)
async def invalid_payment_amount_handler(request: Request, exc: InvalidPaymentAmountException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "InvalidPaymentAmountException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(InvoiceAlreadyPaidException)
async def invoice_already_paid_handler(request: Request, exc: InvoiceAlreadyPaidException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "InvoiceAlreadyPaidException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(BusinessRuleViolationException)
async def business_rule_violation_handler(request: Request, exc: BusinessRuleViolationException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "BusinessRuleViolationException",
            "message": exc.message,
            "details": exc.details,
        },
    )


@app.exception_handler(SubLedgerException)
async def generic_subledger_exception_handler(request: Request, exc: SubLedgerException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error_type": "SubLedgerException",
            "message": exc.message,
            "details": exc.details,
        },
    )


# --- Root & Health Endpoints ---

@app.get("/", tags=["Health"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "healthy",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": settings.VERSION}


# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

