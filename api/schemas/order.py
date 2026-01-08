### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Order Schemas -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Order Schemas

Pydantic models for order data validation and serialization.
Based on GlassTrax 'sales_orders_headers' and 'sales_order_detail' tables.

Date format in GlassTrax: YYYYMMDD (stored as CHAR 8)
Status: open_closed_flag - 'O' = Open, 'C' = Closed
"""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field, field_validator


def _coerce_str(v):
    """Coerce int/float to string for database fields that may return numeric types."""
    if v is None:
        return None
    return str(v).strip() if not isinstance(v, str) else v.strip()


# Type that accepts int/float and coerces to str (for fields like customer_id, po_no, pay_type)
CoercedStr = Annotated[str, BeforeValidator(_coerce_str)]
CoercedStrOrNone = Annotated[str | None, BeforeValidator(_coerce_str)]


def parse_glasstrax_date(date_str: str | None) -> date | None:
    """Convert GlassTrax YYYYMMDD string to date object"""
    if not date_str or len(date_str) != 8 or date_str == "18991230":
        return None
    try:
        return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        return None


class OrderLineItem(BaseModel):
    """Order line item from sales_order_detail table"""

    so_line_no: int = Field(..., description="Line number")
    item_id: str | None = Field(None, max_length=25, description="Item ID")
    item_description: str | None = Field(None, max_length=50, description="Item description")
    cust_part_no: str | None = Field(None, description="Customer part number")
    order_qty: float | None = Field(None, description="Ordered quantity")
    shipped_qty: float | None = Field(None, description="Shipped quantity")
    bill_qty: float | None = Field(None, description="Billed quantity")
    unit_price: float | None = Field(None, description="Unit price")
    total_extended_price: float | None = Field(None, description="Extended price (qty * unit)")
    size_1: float | None = Field(None, description="Size dimension 1 (width)")
    size_2: float | None = Field(None, description="Size dimension 2 (height)")
    block_size: str | None = Field(None, description="Formatted size (size_1 x size_2)")
    open_closed_flag: str | None = Field(None, description="Line status (O/C)")

    # Glass product details
    overall_thickness: float | None = Field(None, description="Glass thickness")
    pattern: str | None = Field(None, max_length=30, description="Pattern type")

    # Processing info (from so_processing + processing_charges)
    has_fab: bool | None = Field(None, description="Has fabrication processing")
    edgework: str | None = Field(None, description="Edgework description")

    class Config:
        from_attributes = True


class OrderAddress(BaseModel):
    """Order shipping/billing address"""

    name: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None


class OrderBase(BaseModel):
    """Base order fields"""

    so_no: int = Field(..., description="Sales order number")
    customer_id: CoercedStr = Field(..., max_length=6, description="Customer ID")
    order_date: date | None = Field(None, description="Order date")


class OrderResponse(OrderBase):
    """Full order response with details"""

    # Header info
    branch_id: str | None = None
    job_name: CoercedStrOrNone = None
    quotation_no: int | None = None
    type: str | None = None  # Order type

    # Customer info (joined)
    customer_name: str | None = None

    # Status
    open_closed_flag: str | None = Field(None, description="O=Open, C=Closed")
    status: str | None = Field(None, description="Status description")
    credit_hold_flag: str | None = None
    verification_hold: str | None = None

    # Dates
    ship_date: date | None = None
    delivery_date: date | None = None
    quotation_date: date | None = None
    expiration_date: date | None = None

    # References
    customer_po_no: CoercedStrOrNone = None
    inside_salesperson: str | None = None
    route_id: CoercedStrOrNone = None

    # Contact
    buyer_first_name: str | None = None
    buyer_last_name: str | None = None
    phone: str | None = None
    email: str | None = None

    # Addresses
    bill_address: OrderAddress | None = None
    ship_address: OrderAddress | None = None

    # Shipping
    ship_method: str | None = None
    warehouse_id: str | None = None

    # Financial
    pay_type: CoercedStrOrNone = None
    taxable: bool | None = None
    currency_id: str | None = None
    amount_paid: float | None = None
    surcharge: float | None = None

    # Line items
    line_items: list[OrderLineItem] | None = None

    # Calculated totals
    total_lines: int | None = None
    total_qty: float | None = None
    total_amount: float | None = None

    @field_validator("status", mode="before")
    @classmethod
    def convert_status(cls, v, info):
        """Convert open_closed_flag to readable status"""
        flag = info.data.get("open_closed_flag") if hasattr(info, "data") else None
        if flag == "O":
            return "Open"
        elif flag == "C":
            return "Closed"
        return v

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """Simplified order for list views"""

    so_no: int
    customer_id: CoercedStr
    customer_name: str | None = None
    order_date: date | None = None
    job_name: CoercedStrOrNone = None
    open_closed_flag: str | None = None
    status: str | None = None
    ship_method: str | None = None
    customer_po_no: CoercedStrOrNone = None
    inside_salesperson: str | None = None
    route_id: CoercedStrOrNone = None
    line_count: int | None = None
    total_amount: float | None = None

    @field_validator("status", mode="before")
    @classmethod
    def convert_status(cls, v, info):
        """Convert open_closed_flag to readable status"""
        flag = info.data.get("open_closed_flag") if hasattr(info, "data") else None
        if flag == "O":
            return "Open"
        elif flag == "C":
            return "Closed"
        return v

    class Config:
        from_attributes = True


class OrderQueryParams(BaseModel):
    """Query parameters for order list endpoint"""

    customer_id: str | None = Field(None, description="Filter by customer ID")
    status: str | None = Field(None, description="Filter by status (O=Open, C=Closed)")
    date_from: date | None = Field(None, description="Orders from this date")
    date_to: date | None = Field(None, description="Orders to this date")
    search: str | None = Field(None, description="Search SO#, job name, or PO#")
    route_id: str | None = Field(None, description="Filter by route")
    salesperson: str | None = Field(None, description="Filter by salesperson")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")


class OrderExistsResponse(BaseModel):
    """Lightweight order validation response"""

    exists: bool = Field(..., description="Whether the order exists")
    so_no: int | None = Field(None, description="Sales order number (if exists)")
    customer_id: CoercedStrOrNone = Field(None, description="Customer ID (if exists)")
    customer_name: str | None = Field(None, description="Customer name (if exists)")
    customer_po_no: CoercedStrOrNone = Field(None, description="Customer PO number (if exists)")
    job_name: CoercedStrOrNone = Field(None, description="Job name (if exists)")
    status: str | None = Field(None, description="Order status - Open/Closed (if exists)")
