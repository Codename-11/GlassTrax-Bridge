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
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


def parse_glasstrax_date(date_str: Optional[str]) -> Optional[date]:
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
    item_id: Optional[str] = Field(None, max_length=25, description="Item ID")
    item_description: Optional[str] = Field(None, max_length=50, description="Item description")
    cust_part_no: Optional[str] = Field(None, description="Customer part number")
    order_qty: Optional[float] = Field(None, description="Ordered quantity")
    shipped_qty: Optional[float] = Field(None, description="Shipped quantity")
    bill_qty: Optional[float] = Field(None, description="Billed quantity")
    unit_price: Optional[float] = Field(None, description="Unit price")
    total_extended_price: Optional[float] = Field(None, description="Extended price (qty * unit)")
    size_1: Optional[float] = Field(None, description="Size dimension 1")
    size_2: Optional[float] = Field(None, description="Size dimension 2")
    open_closed_flag: Optional[str] = Field(None, description="Line status (O/C)")

    class Config:
        from_attributes = True


class OrderAddress(BaseModel):
    """Order shipping/billing address"""

    name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None


class OrderBase(BaseModel):
    """Base order fields"""

    so_no: int = Field(..., description="Sales order number")
    customer_id: str = Field(..., max_length=6, description="Customer ID")
    order_date: Optional[date] = Field(None, description="Order date")


class OrderResponse(OrderBase):
    """Full order response with details"""

    # Header info
    branch_id: Optional[str] = None
    job_name: Optional[str] = None
    quotation_no: Optional[int] = None
    type: Optional[str] = None  # Order type

    # Customer info (joined)
    customer_name: Optional[str] = None

    # Status
    open_closed_flag: Optional[str] = Field(None, description="O=Open, C=Closed")
    status: Optional[str] = Field(None, description="Status description")
    credit_hold_flag: Optional[str] = None
    verification_hold: Optional[str] = None

    # Dates
    ship_date: Optional[date] = None
    delivery_date: Optional[date] = None
    quotation_date: Optional[date] = None
    expiration_date: Optional[date] = None

    # References
    customer_po_no: Optional[str] = None
    inside_salesperson: Optional[str] = None
    route_id: Optional[str] = None

    # Contact
    buyer_first_name: Optional[str] = None
    buyer_last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    # Addresses
    bill_address: Optional[OrderAddress] = None
    ship_address: Optional[OrderAddress] = None

    # Shipping
    ship_method: Optional[str] = None
    warehouse_id: Optional[str] = None

    # Financial
    pay_type: Optional[str] = None
    taxable: Optional[bool] = None
    currency_id: Optional[str] = None
    amount_paid: Optional[float] = None
    surcharge: Optional[float] = None

    # Line items
    line_items: Optional[List[OrderLineItem]] = None

    # Calculated totals
    total_lines: Optional[int] = None
    total_qty: Optional[float] = None
    total_amount: Optional[float] = None

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
    customer_id: str
    customer_name: Optional[str] = None
    order_date: Optional[date] = None
    job_name: Optional[str] = None
    open_closed_flag: Optional[str] = None
    status: Optional[str] = None
    ship_method: Optional[str] = None
    customer_po_no: Optional[str] = None
    inside_salesperson: Optional[str] = None
    route_id: Optional[str] = None
    line_count: Optional[int] = None
    total_amount: Optional[float] = None

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

    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    status: Optional[str] = Field(None, description="Filter by status (O=Open, C=Closed)")
    date_from: Optional[date] = Field(None, description="Orders from this date")
    date_to: Optional[date] = Field(None, description="Orders to this date")
    search: Optional[str] = Field(None, description="Search SO#, job name, or PO#")
    route_id: Optional[str] = Field(None, description="Filter by route")
    salesperson: Optional[str] = Field(None, description="Filter by salesperson")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
