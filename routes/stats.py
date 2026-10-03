from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select, func
from models import Order, OrderStatus
from database import get_session


router = APIRouter(prefix="/stats", tags=["orders"])
@router.get("/daily")
def daily_summary(
    summary_date: date | None = Query(default=None, description="Date for summary (YYYY-MM-DD)"),
    session: Session = Depends(get_session)
):
    if summary_date is None:
        summary_date = date.today()

    start = datetime.combine(summary_date, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(summary_date, datetime.max.time(), tzinfo=timezone.utc)

    summary = {}
    total = 0

    for status in OrderStatus:
        count = session.exec(
            select(func.count(Order.id)).where(
                Order.created_at >= start,
                Order.created_at <= end,
                Order.status == status
            )
        ).one()
        summary[status.value] = count
        total += count

    return {
        "date": summary_date.isoformat(),
        "total_orders": total,
        "by_status": summary
    }