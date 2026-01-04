### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Customer Schemas -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Customer Schemas

Pydantic models for customer data validation and serialization.
Based on GlassTrax 'customer' and 'customer_contacts' tables.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CustomerContact(BaseModel):
    """Customer contact information from customer_contacts table"""

    contact_no: int = Field(..., description="Contact number")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    email: Optional[str] = None
    work_phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    fax: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerAddress(BaseModel):
    """Customer address information"""

    name: Optional[str] = None
    address1: Optional[str] = None
    address2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    fax: Optional[str] = None


class CustomerBase(BaseModel):
    """Base customer fields"""

    customer_id: str = Field(..., max_length=6, description="Customer ID (6 char)")
    customer_name: str = Field(..., max_length=30, description="Customer name")
    route_id: Optional[str] = Field(None, max_length=2, description="Delivery route ID")


class CustomerResponse(CustomerBase):
    """Full customer response with all details"""

    # Basic info
    lookup_description: Optional[str] = None
    customer_type: Optional[str] = None
    inside_salesperson: Optional[str] = None
    territory: Optional[str] = None
    branch_id: Optional[str] = None

    # Main address
    main_address: Optional[CustomerAddress] = None

    # Billing address
    bill_address: Optional[CustomerAddress] = None

    # Shipping address
    ship_address: Optional[CustomerAddress] = None

    # Financial
    credit_limit: Optional[float] = None
    credit_terms_code: Optional[str] = None
    credit_hold: Optional[bool] = None
    taxable: Optional[bool] = None

    # Stats
    ytd_sales: Optional[float] = None
    last_sale_date: Optional[str] = None
    customer_since_date: Optional[str] = None

    # Contacts
    contacts: Optional[List[CustomerContact]] = None

    # Route info (joined)
    route_name: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Simplified customer for list views"""

    customer_id: str
    customer_name: str
    route_id: Optional[str] = None
    route_name: Optional[str] = None
    main_city: Optional[str] = None
    main_state: Optional[str] = None
    customer_type: Optional[str] = None
    inside_salesperson: Optional[str] = None

    class Config:
        from_attributes = True


class CustomerQueryParams(BaseModel):
    """Query parameters for customer list endpoint"""

    search: Optional[str] = Field(None, description="Search by name or ID")
    route_id: Optional[str] = Field(None, description="Filter by route ID")
    customer_type: Optional[str] = Field(None, description="Filter by customer type")
    city: Optional[str] = Field(None, description="Filter by city")
    state: Optional[str] = Field(None, description="Filter by state")
    salesperson: Optional[str] = Field(None, description="Filter by salesperson")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
