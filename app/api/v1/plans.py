from typing import List
from fastapi import APIRouter, Depends, Query, status
from app.api.deps import get_plan_service
from app.services.plan_service import PlanService
from app.schemas.plan import PlanCreate, PlanUpdate, PlanResponse

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Plan",
    description="Create a new subscription plan. Price must be strictly greater than 0.",
)
def create_plan(
    data: PlanCreate,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.create_plan(data)
    return PlanResponse.model_validate(plan)


@router.get(
    "",
    response_model=List[PlanResponse],
    summary="List Plans",
    description="Retrieve plans with optional filtering for active plans.",
)
def list_plans(
    active_only: bool = Query(False, description="Filter for only active plans"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    service: PlanService = Depends(get_plan_service),
) -> List[PlanResponse]:
    plans = service.list_plans(active_only=active_only, skip=skip, limit=limit)
    return [PlanResponse.model_validate(p) for p in plans]


@router.get(
    "/{plan_id}",
    response_model=PlanResponse,
    summary="Get Plan",
    description="Fetch a plan by its primary identifier.",
)
def get_plan(
    plan_id: int,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.get_plan(plan_id)
    return PlanResponse.model_validate(plan)


@router.patch(
    "/{plan_id}",
    response_model=PlanResponse,
    summary="Update Plan",
    description="Update plan name, pricing, or active availability status.",
)
def update_plan(
    plan_id: int,
    data: PlanUpdate,
    service: PlanService = Depends(get_plan_service),
) -> PlanResponse:
    plan = service.update_plan(plan_id, data)
    return PlanResponse.model_validate(plan)
