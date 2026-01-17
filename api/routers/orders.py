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

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse

from api.dependencies import get_glasstrax_service
from api.middleware import APIKeyInfo, get_api_key, require_orders_read
from api.middleware.rate_limit import limiter
from api.schemas.order import (
    FabOrderResponse,
    OrderAddress,
    OrderExistsResponse,
    OrderLineItem,
    OrderListResponse,
    OrderResponse,
    ProcessingDetail,
)
from api.schemas.responses import APIResponse, PaginatedResponse, PaginationMeta
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
    customer_id: str | None = Query(None, description="Filter by customer ID"),
    order_status: str | None = Query(None, alias="status", description="Filter by status (O=Open, C=Closed)"),
    date_from: date | None = Query(None, description="Orders from this date"),
    date_to: date | None = Query(None, description="Orders to this date"),
    search: str | None = Query(None, description="Search SO#, job name, or PO#"),
    route_id: str | None = Query(None, description="Filter by route"),
    salesperson: str | None = Query(None, description="Filter by salesperson"),
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
            detail=f"Database error: {e!s}",
        ) from e


@router.get(
    "/fabs",
    response_model=PaginatedResponse[FabOrderResponse],
    summary="List fab orders for a date",
    description="Get fab orders (waterjet fabrication) for a specific date. For SilentFAB integration.",
)
@limiter.limit("60/minute", key_func=get_api_key_identifier)
async def list_fab_orders(
    request: Request,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_orders_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
    order_date: date | None = Query(None, alias="date", description="Order date (YYYY-MM-DD)"),
    ship_date: date | None = Query(None, description="Ship date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
) -> PaginatedResponse[FabOrderResponse]:
    """
    List fab orders for a specific date (for SilentFAB preprocessing).

    Fab orders are identified by internal_comment_1 starting with 'F# '.
    Returns line items with fabrication and edgework details.

    - **date**: Filter by order date (YYYY-MM-DD)
    - **ship_date**: Filter by ship date (YYYY-MM-DD) - use this for today's shipments
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page (max 500)

    At least one of `date` or `ship_date` must be provided.
    """
    # Require at least one date filter
    if not order_date and not ship_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'date' or 'ship_date' must be provided",
        )

    try:
        fab_orders, total = await service.get_fab_orders(
            order_date=order_date,
            ship_date=ship_date,
            page=page,
            page_size=page_size,
        )

        # Convert to response models
        orders = []
        for o in fab_orders:
            fab_details = None
            if o.get("fab_details"):
                fab_details = [ProcessingDetail(**d) for d in o["fab_details"]]
            edge_details = None
            if o.get("edge_details"):
                edge_details = [ProcessingDetail(**d) for d in o["edge_details"]]

            orders.append(
                FabOrderResponse(
                    fab_number=o.get("fab_number", ""),
                    so_no=o.get("so_no"),
                    line_no=o.get("line_no"),
                    customer_name=o.get("customer_name"),
                    customer_po=o.get("customer_po"),
                    job_name=o.get("job_name"),
                    item_description=o.get("item_description"),
                    width=o.get("width"),
                    height=o.get("height"),
                    shape_no=o.get("shape_no"),
                    quantity=o.get("quantity"),
                    thickness=o.get("thickness"),
                    order_date=o.get("order_date"),
                    ship_date=o.get("ship_date"),
                    order_attachment=o.get("order_attachment"),
                    line_attachment=o.get("line_attachment"),
                    edgework=o.get("edgework"),
                    fab_details=fab_details,
                    edge_details=edge_details,
                )
            )

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
            detail=f"Database error: {e!s}",
        ) from e


@router.get(
    "/{so_no}/exists",
    response_model=APIResponse[OrderExistsResponse],
    summary="Check if order exists",
    description="Lightweight validation to check if an order exists with basic info",
)
@limiter.limit("120/minute", key_func=get_api_key_identifier)
async def check_order_exists(
    request: Request,
    so_no: int,
    api_key: APIKeyInfo = Depends(get_api_key),
    _: None = Depends(require_orders_read),
    service: GlassTraxService = Depends(get_glasstrax_service),
) -> APIResponse[OrderExistsResponse]:
    """
    Lightweight order validation endpoint.

    Returns whether the order exists along with basic identifying information.
    Useful for form validation without fetching full order details.

    - **so_no**: The sales order number (numeric)

    Returns:
    - **exists**: Whether the order was found
    - **customer_id**: Customer ID (if exists)
    - **customer_name**: Customer name (if exists)
    - **customer_po_no**: Customer PO number (if exists)
    - **job_name**: Job name (if exists)
    - **status**: Order status - Open/Closed (if exists)
    """
    try:
        result = await service.check_order_exists(so_no)
        return APIResponse(success=True, data=OrderExistsResponse(**result))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e!s}",
        ) from e


def filter_response_fields(data: dict, fields: list[str]) -> dict:
    """
    Filter a response dict to only include specified fields.

    Supports nested fields with dot notation (e.g., 'line_items.item_description').
    Special handling for 'line_items' - if included, returns all line item fields
    unless specific line_items.* fields are requested.
    """
    if not fields:
        return data

    # Normalize field names (strip whitespace, lowercase for comparison)
    fields = [f.strip() for f in fields]

    # Check if line_items is requested (with or without subfields)
    line_item_fields = [f for f in fields if f.startswith("line_items.")]
    include_line_items = "line_items" in fields or bool(line_item_fields)

    # Top-level fields to include
    top_level_fields = [f for f in fields if "." not in f]

    result = {}

    # Always include so_no for identification
    if "so_no" in data:
        result["so_no"] = data["so_no"]

    # Include requested top-level fields
    for field in top_level_fields:
        if field in data and field != "line_items":
            result[field] = data[field]

    # Handle line_items specially
    if include_line_items and "line_items" in data and data["line_items"]:
        if line_item_fields:
            # Filter line item fields
            line_fields = [f.replace("line_items.", "") for f in line_item_fields]
            # Always include so_line_no for identification
            if "so_line_no" not in line_fields:
                line_fields.insert(0, "so_line_no")

            result["line_items"] = [
                {k: v for k, v in item.items() if k in line_fields}
                for item in data["line_items"]
            ]
        else:
            # Include all line item fields
            result["line_items"] = data["line_items"]

    return result


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
    fields: str | None = Query(
        None,
        description="Comma-separated list of fields to include (e.g., 'customer_name,customer_po_no,line_items'). "
                    "Supports line_items subfields: 'line_items.item_description,line_items.overall_thickness'",
    ),
) -> APIResponse[OrderResponse]:
    """
    Get detailed order information including line items

    - **so_no**: The sales order number (numeric)
    - **fields**: Optional comma-separated field list for sparse responses

    **Field Selection Examples:**
    - `?fields=customer_name,customer_po_no,job_name` - Header fields only
    - `?fields=customer_name,line_items` - Header + all line item fields
    - `?fields=customer_name,line_items.item_description,line_items.overall_thickness` - Specific line fields
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

        # Apply field selection if requested
        if fields:
            field_list = [f.strip() for f in fields.split(",")]
            # Convert to dict with JSON-serializable values (mode="json" converts dates to ISO strings)
            order_dict = order.model_dump(mode="json")
            # Also convert line_items to dicts if present
            if order_dict.get("line_items"):
                order_dict["line_items"] = [
                    item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                    for item in (order.line_items or [])
                ]
            filtered_data = filter_response_fields(order_dict, field_list)
            # Return JSONResponse to bypass response_model validation for sparse responses
            return JSONResponse(content={"success": True, "data": filtered_data})

        return APIResponse(success=True, data=order)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {e!s}",
        ) from e
