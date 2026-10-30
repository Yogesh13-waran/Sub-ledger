from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_subscription_service
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import SubscriptionCreate, SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.post(
    "",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Subscription",
    description="Subscribe a customer to a plan. Plan must be active, and no duplicate active subscription for the same plan is permitted.",
)
def create_subscription(
    data: SubscriptionCreate,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = service.create_subscription(data)
    return SubscriptionResponse.model_validate(sub)


@router.get(
    "",
    response_model=List[SubscriptionResponse],
    summary="List Subscriptions",
    description="Retrieve subscriptions with optional customer or status filters.",
)
def list_subscriptions(
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    status: Optional[str] = Query(None, description="Filter by status: active, cancelled"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: SubscriptionService = Depends(get_subscription_service),
) -> List[SubscriptionResponse]:
    subs = service.list_subscriptions(
        customer_id=customer_id,
        status=status,
        skip=skip,
        limit=limit,
    )
    return [SubscriptionResponse.model_validate(s) for s in subs]


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get Subscription",
    description="Fetch a subscription by ID.",
)
def get_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = service.get_subscription(subscription_id)
    return SubscriptionResponse.model_validate(sub)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Cancel Subscription",
    description="Cancel an active subscription, setting cancelled_at timestamp.",
)
def cancel_subscription(
    subscription_id: int,
    service: SubscriptionService = Depends(get_subscription_service),
) -> SubscriptionResponse:
    sub = service.cancel_subscription(subscription_id)
    return SubscriptionResponse.model_validate(sub)

