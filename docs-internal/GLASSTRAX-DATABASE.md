# GlassTrax Database Reference

Technical reference for the GlassTrax ERP database (Pervasive SQL).

## Database Overview

- **Engine**: Pervasive SQL (PSQL) / Actian PSQL
- **Access**: 32-bit ODBC driver required
- **Mode**: Read-only (critical - never modify ERP data)
- **Tables**: 267 tables (excluding system tables)
- **DSN**: Configured in Windows ODBC Data Source Administrator (32-bit)

## Pervasive SQL Quirks

### Data Types

| Pervasive Type | Notes |
|----------------|-------|
| `CHAR(n)` | Fixed-length, **space-padded** - always `.strip()` on retrieval |
| `NUMERIC(n)` | Decimal numbers, may return as string in some drivers |
| `DATE` | Stored as `CHAR(8)` in format `YYYYMMDD` (e.g., `"20251230"`) |

### Common Gotchas

1. **Space padding**: All `CHAR` fields are right-padded with spaces
   ```python
   # Wrong
   customer_id = row[0]  # "1001  "

   # Right
   customer_id = row[0].strip()  # "1001"
   ```

2. **Date handling**: Dates are stored as 8-character strings
   ```python
   # Parse GlassTrax date
   from datetime import datetime
   date_str = "20251230"
   date_obj = datetime.strptime(date_str, "%Y%m%d").date()
   ```

3. **Null dates**: Empty/null dates appear as `"18991230"` (1899-12-30)
   ```python
   if date_str == "18991230" or date_str.strip() == "":
       return None
   ```

4. **Boolean fields**: Stored as `CHAR(1)` with values `"Y"`/`"N"` or `" "`
   ```python
   is_taxable = row["taxable"].strip() == "Y"
   ```

5. **pyodbc row access**: Use positional indexing for compatibility
   ```python
   # Pervasive ODBC may not support attribute access
   # Use: row[0], row[1], etc.
   # Not: row.column_name
   ```

### Query Syntax

Pervasive SQL is mostly ANSI-compatible but has some differences:

```sql
-- Pagination (no OFFSET, use TOP)
SELECT TOP 10 * FROM customer

-- String concatenation
SELECT first_name || ' ' || last_name FROM customer

-- Case-insensitive LIKE (default behavior)
SELECT * FROM customer WHERE customer_name LIKE '%GLASS%'

-- Quote identifiers with double quotes
SELECT "order" FROM sales_orders_headers  -- "order" is reserved
```

## Key Tables

### Customer Master

**Table**: `customer` (463 rows, 136 columns)

| Column | Type | Description |
|--------|------|-------------|
| `customer_id` | CHAR(6) | Primary key |
| `customer_name` | CHAR(30) | Company name |
| `route_id` | CHAR(2) | Delivery route code |
| `customer_type` | CHAR(10) | Customer classification |
| `main_address_1` | CHAR(30) | Street address |
| `main_city` | CHAR(25) | City |
| `main_state` | CHAR(5) | State code |
| `main_zip_code` | CHAR(10) | Postal code |
| `main_phone` | CHAR(25) | Phone number |
| `customer_credit_hold` | CHAR(1) | Credit hold flag (Y/N/A/R) |
| `hidden` | CHAR(1) | Soft delete flag |

**Related tables**:
- `customer_contacts` - Contact persons
- `customer_notes` - Customer notes
- `customer_types` - Type definitions
- `delivery_routes` - Route definitions

### Sales Orders

**Table**: `sales_orders_headers` (211,699 rows, 92 columns)

| Column | Type | Description |
|--------|------|-------------|
| `so_no` | NUMERIC(8) | Sales order number (primary key) |
| `customer_id` | CHAR(6) | FK to customer |
| `order_date` | CHAR(8) | Order date (YYYYMMDD) |
| `ship_date` | CHAR(8) | Ship date (YYYYMMDD) |
| `delivery_date` | CHAR(8) | Delivery date (YYYYMMDD) |
| `customer_po_no` | CHAR(20) | Customer PO number |
| `route_id` | CHAR(2) | Delivery route |
| `open_closed_flag` | CHAR(1) | O=Open, C=Closed |
| `inside_salesperson` | CHAR(3) | Sales rep code |
| `job_name` | CHAR(30) | Job/project name |
| `pay_type` | CHAR(1) | Payment type code |
| `attached_file` | CHAR(256) | **Order-level** attachment path (typically PDF, e.g., `F:\drawings\2026\1 2026\12\order.pdf`) |

> **Note**: GlassTrax supports attachments at both order and line levels:
> - **Order-level** (`sales_orders_headers.attached_file`): Typically PDF drawings for the entire order
> - **Line-level** (`sales_order_detail.attached_file`): Typically DXF files for specific line items (shapes)
>
> The Bridge API exposes both as `order_attachment` and `line_attachment` in the fab orders endpoint.

**Table**: `sales_order_detail` (542,314 rows, 190 columns)

| Column | Type | Description |
|--------|------|-------------|
| `so_no` | NUMERIC(8) | FK to header |
| `so_line_no` | NUMERIC(3) | Line number (1, 2, 3...) |
| `item_id` | CHAR(25) | Product/item code (FK to inventory_items) |
| `item_description` | CHAR(50) | Line description (glass type info) |
| `order_qty` | NUMERIC(11) | Quantity ordered |
| `shipped_qty` | NUMERIC(11) | Quantity shipped |
| `size_1` | NUMERIC(10) | Width dimension |
| `size_2` | NUMERIC(10) | Height dimension |
| `unit_price` | NUMERIC(10) | Price per unit |
| `open_closed_flag` | CHAR(1) | Line status |
| `overall_thickness` | NUMERIC(10) | Glass thickness |
| `pattern` | CHAR(30) | Pattern type name |
| `processing_id` | CHAR(5) | FK to processing_charges |
| `shape_no` | NUMERIC(3) | Shape number reference |
| `coating_id_01` - `_10` | CHAR(10) | Coating IDs (up to 10) |
| `internal_comment_1` | CHAR(50) | Internal comment - fab orders start with `F# ` (e.g., `F# 4173`) |
| `attached_file` | CHAR(254) | **Line-level** attachment path (typically DXF for shapes, e.g., `F:\drawings\2026\1 2026\17\shape.dxf`) |

### Processing Tables

**Table**: `so_processing` (928,157 rows, 34 columns)

Links order lines to their processing operations (fab, edge, temper, etc.).

| Column | Type | Description |
|--------|------|-------------|
| `so_no` | NUMERIC(8) | FK to sales_orders_headers |
| `so_line_no` | NUMERIC(3) | FK to sales_order_detail |
| `process_index` | NUMERIC(3) | Processing sequence |
| `process_id` | CHAR(5) | FK to processing_charges |
| `number_of_cuts` | NUMERIC(10) | **Quantity** of this operation (e.g., 2 holes, 4 notches) |
| `processing_charge` | NUMERIC(8) | Charge amount |
| `size_1` - `size_4` | NUMERIC(10) | Dimension parameters for the operation |
| `notes_1` - `notes_10` | CHAR(80) | Processing notes |

**Table**: `processing_charges` (345 rows, 48 columns)

Reference table defining processing types.

| Column | Type | Description |
|--------|------|-------------|
| `processing_id` | CHAR(5) | Primary key (e.g., "AHNCA") |
| `process_type` | CHAR(1) | Type code (C, L, P, S, T, U, W) |
| `process_group` | CHAR(50) | Group: CUT, EDGE, FAB, SHAPE, TEMP |
| `description` | CHAR(50) | Human-readable (e.g., "1 1/2\" Bevel") |
| `tempered` | CHAR(1) | Requires tempering (Y/N) |

**Process Groups**:
- `CUT` - Cutting operations
- `EDGE` - Edgework (seaming, polishing, bevels)
- `FAB` - Fabrication (holes, notches, cutouts)
- `SHAPE` - Shape modifications
- `TEMP` - Tempering

### Inventory Items

**Table**: `inventory_items` (4,386 rows, 80 columns)

Master product/item definitions.

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | CHAR(25) | Primary key |
| `item_name` | CHAR(50) | Product description |
| `category_id` | CHAR(5) | Product category |
| `default_thickness` | NUMERIC(10) | Default thickness |
| `tempered_flag` | CHAR(1) | Tempered product (Y/N) |
| `annealed` | CHAR(1) | Annealed glass flag |
| `heat_strengthened` | CHAR(1) | Heat-strengthened flag |
| `laminated` | CHAR(1) | Laminated glass flag |
| `short_name` | CHAR(30) | Short display name |
| `color` | CHAR(15) | Glass color |

### Other Relevant Tables

| Table | Purpose |
|-------|---------|
| `delivery_routes` | Route definitions and descriptions |
| `salespeople` | Sales representative master |
| `invoice_headers` | Invoices |
| `invoice_detail` | Invoice line items |
| `customer_contacts` | Contact persons per customer |
| `ship_to_addresses` | Alternate shipping addresses |

## Exploration Tool

Use `tools/inspect_dsn.py` to explore the database:

```powershell
# List all tables
tools\inspect.bat tables

# Filter tables
tools\inspect.bat tables --filter sales

# View table schema
tools\inspect.bat schema customer

# Schema with sample values
tools\inspect.bat schema customer -s

# Sample data
tools\inspect.bat sample customer -l 5

# Sample with filter
tools\inspect.bat sample sales_orders_headers -f open_closed_flag=O -l 10

# Search tables/columns
tools\inspect.bat search invoice
```

## Common Queries

### Get active customers
```sql
SELECT customer_id, customer_name, route_id, customer_type
FROM customer
WHERE hidden = 'N'
ORDER BY customer_name
```

### Get open orders for a customer
```sql
SELECT h.so_no, h.order_date, h.ship_date, h.customer_po_no
FROM sales_orders_headers h
WHERE h.customer_id = '1001'
  AND h.open_closed_flag = 'O'
ORDER BY h.order_date DESC
```

### Get order with line items
```sql
SELECT h.so_no, h.customer_id, h.customer_po_no,
       d.so_line_no, d.item_description, d.order_qty, d.size_1, d.size_2
FROM sales_orders_headers h
JOIN sales_order_detail d ON h.so_no = d.so_no
WHERE h.so_no = 123456
ORDER BY d.so_line_no
```

### Get orders by route
```sql
SELECT h.so_no, h.customer_id, c.customer_name, h.ship_date
FROM sales_orders_headers h
JOIN customer c ON h.customer_id = c.customer_id
WHERE h.route_id = 'N'
  AND h.open_closed_flag = 'O'
ORDER BY h.ship_date
```

### Get order line with glass details
```sql
SELECT d.so_no, d.so_line_no, d.item_description,
       d.overall_thickness, d.pattern, d.size_1, d.size_2
FROM sales_order_detail d
WHERE d.so_no = 123456
ORDER BY d.so_line_no
```

### Check if order line has fabrication
```sql
SELECT d.so_no, d.so_line_no,
       CASE WHEN EXISTS (
           SELECT 1 FROM so_processing p
           JOIN processing_charges pc ON p.process_id = pc.processing_id
           WHERE p.so_no = d.so_no AND p.so_line_no = d.so_line_no
             AND pc.process_group = 'FAB'
       ) THEN 'Y' ELSE 'N' END AS has_fab
FROM sales_order_detail d
WHERE d.so_no = 123456
```

### Get processing operations for an order line
```sql
SELECT p.so_no, p.so_line_no, p.process_id,
       pc.process_group, pc.description,
       COALESCE(p.number_of_cuts, 1) as qty
FROM so_processing p
JOIN processing_charges pc ON p.process_id = pc.processing_id
WHERE p.so_no = 123456 AND p.so_line_no = 1
ORDER BY p.process_index
```

> **Note**: The `number_of_cuts` column stores the quantity for each operation (e.g., 2 holes, 4 notches). Always use `COALESCE(p.number_of_cuts, 1)` to default to 1 if null.

### Get edgework for an order line
```sql
SELECT pc.description AS edgework
FROM so_processing p
JOIN processing_charges pc ON p.process_id = pc.processing_id
WHERE p.so_no = 123456 AND p.so_line_no = 1
  AND pc.process_group = 'EDGE'
```

## Agent Allowed Tables

The GlassTrax API Agent restricts queries to these tables (configurable in `agent_config.yaml`):

```yaml
allowed_tables:
  - customer
  - customer_contacts
  - delivery_routes
  - sales_orders_headers
  - sales_order_detail
  - so_processing         # For fab/edge/temper operations
  - processing_charges    # Processing type definitions
  - inventory_items       # Product master for glass types
```

To query additional tables, add them to the allowlist and restart the agent.

## Performance Notes

1. **Large tables**: `sales_order_detail` has 500K+ rows - always use filters
2. **No indexes exposed**: Pervasive indexes exist but aren't visible via ODBC metadata
3. **Connection pooling**: The agent maintains a single connection; avoid long-running queries
4. **Timeout**: Default 30 seconds; adjust in config for complex queries
