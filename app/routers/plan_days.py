from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import PlanDay, User
from app.schemas import PlanDayCreate, PlanDayOut
from app.security import get_current_user


router = APIRouter(prefix="/plan_days", tags=["plan_days"])


@router.post("", response_model=PlanDayOut, status_code=201)
def create_plan_day(
    payload: PlanDayCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    plan_day = PlanDay(
        calender=payload.calender,
        add_date=payload.add_date,
        user_id=current_user.user_id,
    )
    session.add(plan_day)
    session.commit()
    session.refresh(plan_day)
    return plan_day


@router.get("", response_model=list[PlanDayOut])
def list_plan_days(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return session.scalars(
        select(PlanDay)
        .where(PlanDay.user_id == current_user.user_id)
        .order_by(PlanDay.plan_id)
    ).all()


@router.get("/{plan_id}", response_model=PlanDayOut)
def get_plan_day(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    plan_day = session.scalar(
        select(PlanDay).where(
            PlanDay.plan_id == plan_id,
            PlanDay.user_id == current_user.user_id,
        )
    )
    if plan_day is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return plan_day
