# Orders API

Endpoints for accessing sales order data from GlassTrax.

## Permissions

All order endpoints require the `orders:read` permission.

## List Orders

```http
GET /api/v1/orders
```

Returns a paginated list of orders with optional filtering.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `customer_id` | string | Filter by customer ID |
| `status` | string | Filter by status: `O` (Open) or `C` (Closed) |
| `date_from` | date | Orders from this date (YYYY-MM-DD) |
| `date_to` | date | Orders to this date (YYYY-MM-DD) |
| `search` | string | Search in SO#, job name, or customer PO |
| `route_id` | string | Filter by delivery route |
| `salesperson` | string | Filter by salesperson |
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20, max: 100) |

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/orders?status=O&page_size=10" \
  -H "X-API-Key: gtb_your_api_key"
```

### Example Response

```json
{
  "success": true,
  "data": [
    {
      "so_no": 123456,
      "customer_id": "1001",
      "customer_name": "ABC Glass Co",
      "order_date": "2024-01-15",
      "job_name": "Downtown Project",
      "open_closed_flag": "O",
      "status": "Open",
      "customer_po_no": "PO-2024-001",
      "route_id": "N"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 50,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

## Get Order Details

```http
GET /api/v1/orders/{so_no}
```

Returns detailed order information including line items with glass details.

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `so_no` | integer | Sales order number |

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated list of fields to include (optional) |

### Field Selection

Use the `fields` parameter to request only specific fields (sparse fieldsets):

```bash
# Header fields only
?fields=customer_name,customer_po_no,job_name

# Header + all line items
?fields=customer_name,line_items

# Specific line item fields
?fields=customer_name,line_items.item_description,line_items.overall_thickness
```

::: tip
Field selection reduces response size and is useful for form autofill scenarios where you only need specific data.
:::

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/orders/123456" \
  -H "X-API-Key: gtb_your_api_key"
```

### Example Response

```json
{
  "success": true,
  "data": {
    "so_no": 123456,
    "customer_id": "1001",
    "customer_name": "ABC Glass Co",
    "customer_po_no": "PO-2024-001",
    "job_name": "Downtown Project",
    "order_date": "2024-01-15",
    "ship_date": "2024-01-20",
    "status": "Open",
    "route_id": "N",
    "line_items": [
      {
        "so_line_no": 1,
        "item_description": "1/4 CLEAR TEMPERED",
        "size_1": 24.5,
        "size_2": 36.0,
        "block_size": "24.5 x 36.0",
        "overall_thickness": 0.25,
        "pattern": "CLEAR",
        "has_fab": true,
        "edgework": "1\" Flat Polish",
        "order_qty": 10
      }
    ],
    "total_lines": 1,
    "total_qty": 10
  }
}
```

### Line Item Fields

| Field | Type | Description |
|-------|------|-------------|
| `so_line_no` | integer | Line number |
| `item_id` | string | Product item ID |
| `item_description` | string | Glass type description |
| `size_1` | float | Width dimension |
| `size_2` | float | Height dimension |
| `block_size` | string | Formatted size (e.g., "24.5 x 36.0") |
| `overall_thickness` | float | Glass thickness |
| `pattern` | string | Pattern type |
| `has_fab` | boolean | Has fabrication processing |
| `edgework` | string | Edgework description |
| `order_qty` | float | Quantity ordered |
| `shipped_qty` | float | Quantity shipped |
| `unit_price` | float | Price per unit |

## Check Order Exists

```http
GET /api/v1/orders/{so_no}/exists
```

Lightweight validation endpoint to check if an order exists. Returns basic identifying information without fetching full order details.

::: tip Use Case
This endpoint is ideal for form validation - quickly check if an SO number is valid and get customer/PO info for autofill without the overhead of fetching full order details.
:::

### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `so_no` | integer | Sales order number |

### Example Request

```bash
curl -X GET "http://localhost:8000/api/v1/orders/123456/exists" \
  -H "X-API-Key: gtb_your_api_key"
```

### Example Response (Order Found)

```json
{
  "success": true,
  "data": {
    "exists": true,
    "so_no": 123456,
    "customer_id": "1001",
    "customer_name": "ABC Glass Co",
    "customer_po_no": "PO-2024-001",
    "job_name": "Downtown Project",
    "status": "Open"
  }
}
```

### Example Response (Order Not Found)

```json
{
  "success": true,
  "data": {
    "exists": false
  }
}
```

## Error Responses

### Order Not Found

```json
{
  "detail": "Order '999999' not found"
}
```
Status: `404 Not Found`

### Unauthorized

```json
{
  "detail": "API key required"
}
```
Status: `401 Unauthorized`

### Permission Denied

```json
{
  "detail": "Permission denied: orders:read required"
}
```
Status: `403 Forbidden`
