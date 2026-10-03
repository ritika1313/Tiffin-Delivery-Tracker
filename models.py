from enum import Enum
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

# OrderStatus (Enum) -> preparing, picked_up, in_transit, delivered
class OrderStatus(str, Enum):
    PREPARING = "preparing"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"

# Database table for orders
# id (primary key), customer_name(str), delivery_address(str), items(str), status(OrderStatus), created_at, updated_at
class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: str
    delivery_address: str
    items: str
    status: OrderStatus = Field(default=OrderStatus.PREPARING)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# schema for creating a new order
class OrderCreate(SQLModel):
    customer_name: str
    delivery_address: str
    items: str

# Schema for updating an order's status
class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = None
    delivery_address: Optional[str] = None

# statuslog, order_id, old_status, new_status, changed_at (datetime)
class StatusLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int
    old_status: str
    new_status: str
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))