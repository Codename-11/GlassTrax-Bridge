### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Order API Router -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Order API Endpoints

Provides REST endpoints for order data access:
- GET /orders - List orders with pagination and filtering
- GET /orders/{so_no} - Get single order details with line items
"""

import math
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.schemas.order import (
    OrderListResponse,
    OrderResponse,
    OrderLineItem,
    OrderAddress,
)
from api.schemas.responses import PaginatedResponse, PaginationMeta, APIResponse
from api.middleware import get_api_key, require_orders_read, APIKeyInfo
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
    response_model=PaginatedResponse[OrderListResponse],
    summary="List orders",
    description="Retrieve a paginated list of orders with optional filtering",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def list_orders(
    request: Request,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_orders_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    order_status: Optional[str] = Query(None, alias="status", description="Filter by status (O=Open, C=Closed)"),
    date_from: Optional[date] = Query(None, description="Orders from this date"),
    date_to: Optional[date] = Query(None, description="Orders to this date"),
    search: Optional[str] = Query(None, description="Search SO#, job name, or PO#"),
    route_id: Optional[str] = Query(None, description="Filter by route"),
    salesperson: Optional[str] = Query(None, description="Filter by salesperson"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PaginatedResponse[OrderListResponse]:
    """
    List orders with pagination and filtering

    - **customer_id**: Filter by customer
    - **status**: Filter by order status (O=Open, C=Closed)
    - **date_from**: Start date for date range filter
    - **date_to**: End date for date range filter
    - **search**: Search in SO#, job name, or customer PO#
    - **route_id**: Filter by delivery route
    - **salesperson**: Filter by inside salesperson
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 100)
    """
    try:
        orders_data, total = await service.get_orders(
            customer_id=customer_id,
            status=order_status,
            date_from=date_from,
            date_to=date_to,
            search=search,
            route_id=route_id,
            salesperson=salesperson,
            page=page,
            page_size=page_size,
        )

        # Convert to response models
        orders = [
            OrderListResponse(
                so_no=o.get("so_no"),
                customer_id=o.get("customer_id"),
                customer_name=o.get("customer_name"),
                order_date=o.get("order_date"),
                job_name=o.get("job_name"),
                open_closed_flag=o.get("open_closed_flag"),
                status=o.get("status"),
                ship_method=o.get("ship_method"),
                customer_po_no=o.get("customer_po_no"),
                inside_salesperson=o.get("inside_salesperson"),
                route_id=o.get("route_id"),
                line_count=o.get("line_count"),
                total_amount=o.get("total_amount"),
            )
            for o in orders_data
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedResponse(
            success=True,
            data=orders,
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
    "/{so_no}",
    response_model=APIResponse[OrderResponse],
    summary="Get order details",
    description="Retrieve detailed information for a specific order including line items",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def get_order(
    request: Request,
    so_no: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_orders_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
) -> APIResponse[OrderResponse]:
    """
    Get detailed order information including line items

    - **so_no**: The sales order number (numeric)
    """
    try:
        order_data = await service.get_order_by_number(so_no)

        if not order_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Order '{so_no}' not found",
            )

        # Build address objects
        bill_address = None
        if order_data.get("bill_address"):
            addr = order_data["bill_address"]
            if any(addr.values()):
                bill_address = OrderAddress(**addr)

        ship_address = None
        if order_data.get("ship_address"):
            addr = order_data["ship_address"]
            if any(addr.values()):
                ship_address = OrderAddress(**addr)

        # Build line items
        line_items = None
        if order_data.get("line_items"):
            line_items = [
                OrderLineItem(**item)
                for item in order_data["line_items"]
            ]

        order = OrderResponse(
            so_no=order_data.get("so_no"),
            customer_id=order_data.get("customer_id"),
            order_date=order_data.get("order_date"),
            branch_id=order_data.get("branch_id"),
            job_name=order_data.get("job_name"),
            quotation_no=order_data.get("quotation_no"),
            type=order_data.get("type"),
            customer_name=order_data.get("customer_name"),
            open_closed_flag=order_data.get("open_closed_flag"),
            status=order_data.get("status"),
            credit_hold_flag=order_data.get("credit_hold_flag"),
            verification_hold=order_data.get("verification_hold"),
            ship_date=order_data.get("ship_date"),
            delivery_date=order_data.get("delivery_date"),
            quotation_date=order_data.get("quotation_date"),
            expiration_date=order_data.get("expiration_date"),
            customer_po_no=order_data.get("customer_po_no"),
            inside_salesperson=order_data.get("inside_salesperson"),
            route_id=order_data.get("route_id"),
            buyer_first_name=order_data.get("buyer_first_name"),
            buyer_last_name=order_data.get("buyer_last_name"),
            phone=order_data.get("phone"),
            email=order_data.get("email"),
            bill_address=bill_address,
            ship_address=ship_address,
            ship_method=order_data.get("ship_method"),
            warehouse_id=order_data.get("warehouse_id"),
            pay_type=order_data.get("pay_type"),
            taxable=order_data.get("taxable"),
            currency_id=order_data.get("currency_id"),
            amount_paid=order_data.get("amount_paid"),
            surcharge=order_data.get("surcharge"),
            line_items=line_items,
            total_lines=order_data.get("total_lines"),
            total_qty=order_data.get("total_qty"),
            total_amount=order_data.get("total_amount"),
        )

        return APIResponse(success=True, data=order)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )
