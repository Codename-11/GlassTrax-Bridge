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


from pydantic import BaseModel, Field


class CustomerContact(BaseModel):
    """Customer contact information from customer_contacts table"""

    contact_no: int = Field(..., description="Contact number")
    first_name: str | None = None
    last_name: str | None = None
    title: str | None = None
    email: str | None = None
    work_phone: str | None = None
    mobile_phone: str | None = None
    fax: str | None = None

    class Config:
        from_attributes = True


class CustomerAddress(BaseModel):
    """Customer address information"""

    name: str | None = None
    address1: str | None = None
    address2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    zip_code: str | None = None
    phone: str | None = None
    fax: str | None = None


class CustomerBase(BaseModel):
    """Base customer fields"""

    customer_id: str = Field(..., max_length=6, description="Customer ID (6 char)")
    customer_name: str = Field(..., max_length=30, description="Customer name")
    route_id: str | None = Field(None, max_length=2, description="Delivery route ID")


class CustomerResponse(CustomerBase):
    """Full customer response with all details"""

    # Basic info
    lookup_description: str | None = None
    customer_type: str | None = None
    inside_salesperson: str | None = None
    territory: str | None = None
    branch_id: str | None = None

    # Main address
    main_address: CustomerAddress | None = None

    # Billing address
    bill_address: CustomerAddress | None = None

    # Shipping address
    ship_address: CustomerAddress | None = None

    # Financial
    credit_limit: float | None = None
    credit_terms_code: str | None = None
    credit_hold: bool | None = None
    taxable: bool | None = None

    # Stats
    ytd_sales: float | None = None
    last_sale_date: str | None = None
    customer_since_date: str | None = None

    # Contacts
    contacts: list[CustomerContact] | None = None

    # Route info (joined)
    route_name: str | None = None

    class Config:
        from_attributes = True


class CustomerListResponse(BaseModel):
    """Simplified customer for list views"""

    customer_id: str
    customer_name: str
    route_id: str | None = None
    route_name: str | None = None
    main_city: str | None = None
    main_state: str | None = None
    customer_type: str | None = None
    inside_salesperson: str | None = None

    class Config:
        from_attributes = True


class CustomerQueryParams(BaseModel):
    """Query parameters for customer list endpoint"""

    search: str | None = Field(None, description="Search by name or ID")
    route_id: str | None = Field(None, description="Filter by route ID")
    customer_type: str | None = Field(None, description="Filter by customer type")
    city: str | None = Field(None, description="Filter by city")
    state: str | None = Field(None, description="Filter by state")
    salesperson: str | None = Field(None, description="Filter by salesperson")
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
