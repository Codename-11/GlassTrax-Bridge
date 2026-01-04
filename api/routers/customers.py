### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Customer API Router -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Customer API Endpoints

Provides REST endpoints for customer data access:
- GET /customers - List customers with pagination and filtering
- GET /customers/{customer_id} - Get single customer details
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.schemas.customer import (
    CustomerListResponse,
    CustomerResponse,
    CustomerAddress,
    CustomerContact,
)
from api.schemas.responses import PaginatedResponse, PaginationMeta, APIResponse
from api.middleware import get_api_key, require_customers_read, APIKeyInfo
from api.middleware.rate_limit import limiter
from api.dependencies import get_glasstrax_service
from api.services.glasstrax import GlassTraxService

router = APIRouter()


def get_api_key_identifier(request: Request) -> str:
    """Get rate limit key from API key header"""
    api_key = request.headers.get("X-API-Key", "anonymous")
    return f"key:{api_key[:12]}" if api_key else "anonymous"


@router.get(
    "",
    response_model=PaginatedResponse[CustomerListResponse],
    summary="List customers",
    description="Retrieve a paginated list of customers with optional filtering",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def list_customers(
    request: Request,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_customers_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
    search: Optional[str] = Query(None, description="Search by name or customer ID"),
    route_id: Optional[str] = Query(None, description="Filter by route ID"),
    customer_type: Optional[str] = Query(None, description="Filter by customer type"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    salesperson: Optional[str] = Query(None, description="Filter by salesperson"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[CustomerListResponse]:
    """
    List customers with pagination and filtering

    - **search**: Search in customer name or ID
    - **route_id**: Filter by delivery route ID
    - **customer_type**: Filter by customer type
    - **city**: Filter by city
    - **state**: Filter by state
    - **salesperson**: Filter by inside salesperson
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    """
    try:
        customers_data, total = await service.get_customers(
            search=search,
            route_id=route_id,
            customer_type=customer_type,
            city=city,
            state=state,
            salesperson=salesperson,
            page=page,
            page_size=page_size,
        )

        # Convert to response models
        customers = [
            CustomerListResponse(
                customer_id=c.get("customer_id", "").strip(),
                customer_name=c.get("customer_name", "").strip() if c.get("customer_name") else "",
                route_id=c.get("route_id", "").strip() if c.get("route_id") else None,
                route_name=c.get("route_name", "").strip() if c.get("route_name") else None,
                main_city=c.get("main_city", "").strip() if c.get("main_city") else None,
                main_state=c.get("main_state", "").strip() if c.get("main_state") else None,
                customer_type=c.get("customer_type", "").strip() if c.get("customer_type") else None,
                inside_salesperson=c.get("inside_salesperson", "").strip() if c.get("inside_salesperson") else None,
            )
            for c in customers_data
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse(
            success=True,
            data=customers,
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@router.get(
    "/{customer_id}",
    response_model=APIResponse[CustomerResponse],
    summary="Get customer details",
    description="Retrieve detailed information for a specific customer",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def get_customer(
    request: Request,
    customer_id: str,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_customers_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
) -> APIResponse[CustomerResponse]:
    """
    Get detailed customer information

    - **customer_id**: The unique customer identifier (6 char)
    """
    try:
        customer_data = await service.get_customer_by_id(customer_id)

        if not customer_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer '{customer_id}' not found",
            )

        # Build address objects
        main_address = None
        if customer_data.get("main_address"):
            addr = customer_data["main_address"]
            if any(addr.values()):
                main_address = CustomerAddress(**addr)

        bill_address = None
        if customer_data.get("bill_address"):
            addr = customer_data["bill_address"]
            if any(addr.values()):
                bill_address = CustomerAddress(**addr)

        ship_address = None
        if customer_data.get("ship_address"):
            addr = customer_data["ship_address"]
            if any(addr.values()):
                ship_address = CustomerAddress(**addr)

        # Build contacts list
        contacts = None
        if customer_data.get("contacts"):
            contacts = [
                CustomerContact(**contact)
                for contact in customer_data["contacts"]
            ]

        customer = CustomerResponse(
            customer_id=customer_data.get("customer_id"),
            customer_name=customer_data.get("customer_name"),
            route_id=customer_data.get("route_id"),
            route_name=customer_data.get("route_name"),
            lookup_description=customer_data.get("lookup_description"),
            customer_type=customer_data.get("customer_type"),
            inside_salesperson=customer_data.get("inside_salesperson"),
            territory=customer_data.get("territory"),
            branch_id=customer_data.get("branch_id"),
            main_address=main_address,
            bill_address=bill_address,
            ship_address=ship_address,
            credit_limit=customer_data.get("credit_limit"),
            credit_terms_code=customer_data.get("credit_terms_code"),
            credit_hold=customer_data.get("credit_hold"),
            taxable=customer_data.get("taxable"),
            ytd_sales=customer_data.get("ytd_sales"),
            last_sale_date=customer_data.get("last_sale_date"),
            customer_since_date=customer_data.get("customer_since_date"),
            contacts=contacts,
        )

        return APIResponse(success=True, data=customer)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
