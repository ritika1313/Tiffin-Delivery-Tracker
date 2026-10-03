from datetime import datetime, date, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Order, OrderCreate, OrderUpdate, StatusLog, OrderStatus


router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=Order)
def create_order(
    order: OrderCreate,
    session: Session = Depends(get_session)
):
    db_order = Order(**order.model_dump())

    session.add(db_order)
    session.commit()
    session.refresh(db_order)

    return db_order


@router.get("/", response_model=list[Order])
def list_orders(
    status: OrderStatus | None = Query(
        default=None,
        description="Filter by order status"
    ),
    created_date: date | None = Query(
        default=None,
        description="Filter by creation date (YYYY-MM-DD)"
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session)
):
    query = select(Order)

    if status:
        query = query.where(Order.status == status)

    if created_date:
        start = datetime.combine(
            created_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )

        end = datetime.combine(
            created_date,
            datetime.max.time(),
            tzinfo=timezone.utc,
        )

        query = query.where(
            Order.created_at.between(start, end)
        )

    query = query.offset(skip).limit(limit)

    return session.exec(query).all()

@router.patch("/{order_id}/status", response_model=Order)
def update_order_status(
    order_id: int,
    order_update: OrderUpdate,
    session: Session = Depends(get_session)
):
    # Find order
    order = session.get(Order, order_id)

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    # Store old status
    old_status = order.status

    # Update status
    if order_update.status is not None:
        order.status = order_update.status

        # Create status history
        status_log = StatusLog(
            order_id=order.id,
            old_status=old_status.value,
            new_status=order_update.status.value,
            changed_at=datetime.now(timezone.utc)
        )

        session.add(status_log)

    # Update address if provided
    if order_update.delivery_address is not None:
        order.delivery_address = order_update.delivery_address

    # Update timestamp
    order.updated_at = datetime.now(timezone.utc)

    session.add(order)
    session.commit()
    session.refresh(order)

    return order