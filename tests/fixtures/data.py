"""
Sample test data for GlassTrax-Bridge tests.

Contains realistic mock data that matches the GlassTrax database schema.
"""

# Sample customer data (matches GlassTrax customer table structure)
SAMPLE_CUSTOMERS = [
    {
        "customer_id": "CUST001",
        "customer_name": "Acme Glass Corporation",
        "route_id": "R01",
        "route_name": "Route 1 - Downtown",
        "main_address": "123 Main Street",
        "main_city": "Boston",
        "main_state": "MA",
        "main_zip": "02101",
        "customer_type": "A",
        "inside_salesperson": "JD",
        "outside_salesperson": "SM",
        "phone": "617-555-0100",
        "fax": "617-555-0101",
        "email": "orders@acmeglass.com",
    },
    {
        "customer_id": "CUST002",
        "customer_name": "Crystal Clear Windows",
        "route_id": "R02",
        "route_name": "Route 2 - Suburbs",
        "main_address": "456 Oak Avenue",
        "main_city": "Cambridge",
        "main_state": "MA",
        "main_zip": "02139",
        "customer_type": "B",
        "inside_salesperson": "AW",
        "outside_salesperson": "SM",
        "phone": "617-555-0200",
        "fax": None,
        "email": "info@crystalclear.com",
    },
    {
        "customer_id": "CUST003",
        "customer_name": "Metro Glass & Mirror",
        "route_id": "R01",
        "route_name": "Route 1 - Downtown",
        "main_address": "789 Industrial Blvd",
        "main_city": "Somerville",
        "main_state": "MA",
        "main_zip": "02143",
        "customer_type": "A",
        "inside_salesperson": "JD",
        "outside_salesperson": "RB",
        "phone": "617-555-0300",
        "fax": "617-555-0301",
        "email": None,
    },
]

# Sample order data (matches GlassTrax order table structure)
SAMPLE_ORDERS = [
    {
        "order_number": "ORD-2024-001",
        "customer_id": "CUST001",
        "customer_name": "Acme Glass Corporation",
        "order_date": "20240115",
        "ship_date": "20240120",
        "status": "SHIPPED",
        "total_amount": 1250.00,
        "salesperson": "JD",
        "po_number": "PO-12345",
        "ship_via": "UPS Ground",
    },
    {
        "order_number": "ORD-2024-002",
        "customer_id": "CUST002",
        "customer_name": "Crystal Clear Windows",
        "order_date": "20240116",
        "ship_date": None,
        "status": "PENDING",
        "total_amount": 875.50,
        "salesperson": "AW",
        "po_number": "CC-2024-100",
        "ship_via": "Will Call",
    },
    {
        "order_number": "ORD-2024-003",
        "customer_id": "CUST001",
        "customer_name": "Acme Glass Corporation",
        "order_date": "20240117",
        "ship_date": "20240118",
        "status": "DELIVERED",
        "total_amount": 3420.00,
        "salesperson": "JD",
        "po_number": "PO-12346",
        "ship_via": "Delivery",
    },
]

# Sample GlassTrax database columns (for mock cursor.description)
CUSTOMER_COLUMNS = [
    "customer_id",
    "customer_name",
    "route_id",
    "route_name",
    "main_address",
    "main_city",
    "main_state",
    "main_zip",
    "customer_type",
    "inside_salesperson",
    "outside_salesperson",
    "phone",
    "fax",
    "email",
]

ORDER_COLUMNS = [
    "order_number",
    "customer_id",
    "customer_name",
    "order_date",
    "ship_date",
    "status",
    "total_amount",
    "salesperson",
    "po_number",
    "ship_via",
]
