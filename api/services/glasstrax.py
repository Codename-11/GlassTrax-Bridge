### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - GlassTrax Data Service -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
GlassTrax Data Service

Provides a service layer for accessing GlassTrax ERP data.
Supports two modes:
1. Direct ODBC - connects directly to Pervasive SQL (Windows only)
2. Agent Mode - communicates with GlassTrax Agent via HTTP

Tables:
- customer (463 records) - Customer master data
- customer_contacts - Customer contact information
- delivery_routes - Route definitions
- sales_orders_headers (211,699 records) - Order headers
- sales_order_detail (542,314 records) - Order line items

Date format: YYYYMMDD stored as CHAR(8)
Status: open_closed_flag - 'O' = Open, 'C' = Closed
"""

from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from api.services.agent_client import AgentClient

# Import pyodbc only when needed (not available in Docker)
try:
    import pyodbc

    PYODBC_AVAILABLE = True
except ImportError:
    pyodbc = None  # type: ignore
    PYODBC_AVAILABLE = False


def parse_glasstrax_date(date_str: str | None) -> date | None:
    """Convert GlassTrax YYYYMMDD string to date object"""
    if not date_str or len(date_str) != 8 or date_str == "18991230":
        return None
    try:
        return date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    except (ValueError, TypeError):
        return None


def format_date_for_query(d: date | None) -> str | None:
    """Convert date object to GlassTrax YYYYMMDD format"""
    if not d:
        return None
    return d.strftime("%Y%m%d")


class GlassTraxService:
    """
    Service layer for GlassTrax database operations.

    Supports two modes:
    1. Direct ODBC (agent_client=None): Uses pyodbc for direct database access.
       Requires Windows with 32-bit Python and Pervasive ODBC driver.
    2. Agent Mode (agent_client provided): Uses HTTP client to communicate with
       GlassTrax Agent running on Windows.
    """

    def __init__(
        self,
        dsn: str = "LIVE",
        readonly: bool = True,
        agent_client: "AgentClient | None" = None,
    ):
        """
        Initialize the service.

        Args:
            dsn: ODBC Data Source Name (used in direct mode only)
            readonly: Connect in read-only mode (default: True)
            agent_client: Optional AgentClient for agent mode
        """
        self.dsn = dsn
        self.readonly = readonly
        self.agent_client = agent_client
        self._conn: Any = None  # pyodbc.Connection when in direct mode
        self._cursor: Any = None  # pyodbc.Cursor when in direct mode

    @property
    def is_agent_mode(self) -> bool:
        """Check if running in agent mode"""
        return self.agent_client is not None

    # ========================================
    # Direct ODBC Methods (Windows only)
    # ========================================

    def _get_connection(self) -> Any:
        """Get or create database connection (direct mode only)"""
        if self.is_agent_mode:
            raise RuntimeError("Cannot get direct connection in agent mode")

        if not PYODBC_AVAILABLE:
            raise RuntimeError("pyodbc not available - use agent mode")

        if self._conn is None:
            readonly_str = "Yes" if self.readonly else "No"
            conn_str = f"DSN={self.dsn};ReadOnly={readonly_str}"
            self._conn = pyodbc.connect(conn_str)
            self._cursor = self._conn.cursor()
        return self._conn

    def _get_cursor(self) -> Any:
        """Get the cursor, creating connection if needed (direct mode only)"""
        self._get_connection()
        return self._cursor

    def close(self) -> None:
        """Close the database connection"""
        if self._cursor:
            self._cursor.close()
            self._cursor = None
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "GlassTraxService":
        """Context manager entry"""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        """Context manager exit"""
        self.close()
        return False

    # ========================================
    # Customer Methods
    # ========================================

    async def get_customers(
        self,
        search: str | None = None,
        route_id: str | None = None,
        customer_type: str | None = None,
        city: str | None = None,
        state: str | None = None,
        salesperson: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get list of customers with optional filtering and pagination.

        Args:
            search: Search term for customer name or ID
            route_id: Filter by route ID
            customer_type: Filter by customer type
            city: Filter by city
            state: Filter by state
            salesperson: Filter by inside salesperson
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of customer dicts, total count)
        """
        if self.is_agent_mode:
            return await self._get_customers_via_agent(
                search, route_id, customer_type, city, state, salesperson, page, page_size
            )
        else:
            return self._get_customers_direct(
                search, route_id, customer_type, city, state, salesperson, page, page_size
            )

    async def _get_customers_via_agent(
        self,
        search: str | None,
        route_id: str | None,
        customer_type: str | None,
        city: str | None,
        state: str | None,
        salesperson: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get customers via agent (agent mode)"""
        from api.services.agent_schemas import FilterCondition, JoinClause, OrderBy

        # Build filters
        filters: list[FilterCondition] = []

        if search:
            # Agent doesn't support OR, so we need two queries or use LIKE on customer_name
            # For simplicity, search on customer_name only in agent mode
            filters.append(FilterCondition(column="c.customer_name", operator="LIKE", value=f"%{search}%"))

        if route_id:
            filters.append(FilterCondition(column="c.route_id", operator="=", value=route_id))

        if customer_type:
            filters.append(FilterCondition(column="c.customer_type", operator="=", value=customer_type))

        if city:
            filters.append(FilterCondition(column="c.main_city", operator="LIKE", value=f"%{city}%"))

        if state:
            filters.append(FilterCondition(column="c.main_state", operator="=", value=state))

        if salesperson:
            filters.append(FilterCondition(column="c.inside_salesperson", operator="=", value=salesperson))

        # Get total count
        total = await self.agent_client.count_table("customer", filters)

        # Get paginated results
        offset = (page - 1) * page_size

        result = await self.agent_client.query_table(
            table="customer",
            alias="c",
            columns=[
                "c.customer_id",
                "c.customer_name",
                "c.route_id",
                "r.route_name",
                "c.main_city",
                "c.main_state",
                "c.customer_type",
                "c.inside_salesperson",
            ],
            filters=filters,
            joins=[
                JoinClause(
                    table="delivery_routes",
                    alias="r",
                    join_type="LEFT",
                    on_left="c.route_id",
                    on_right="r.route_id",
                )
            ],
            order_by=[OrderBy(column="c.customer_name", direction="ASC")],
            limit=page_size,
            offset=offset,
        )

        # Convert rows to dicts
        customers = []
        for row in result.rows:
            customer = dict(zip([c.lower() for c in result.columns], row))
            customers.append(customer)

        return customers, total

    def _get_customers_direct(
        self,
        search: str | None,
        route_id: str | None,
        customer_type: str | None,
        city: str | None,
        state: str | None,
        salesperson: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get customers via direct ODBC (direct mode)"""
        cursor = self._get_cursor()

        # Build WHERE clause
        conditions = []
        params = []

        if search:
            conditions.append("(c.customer_id LIKE ? OR c.customer_name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        if route_id:
            conditions.append("c.route_id = ?")
            params.append(route_id)

        if customer_type:
            conditions.append("c.customer_type = ?")
            params.append(customer_type)

        if city:
            conditions.append("c.main_city LIKE ?")
            params.append(f"%{city}%")

        if state:
            conditions.append("c.main_state = ?")
            params.append(state)

        if salesperson:
            conditions.append("c.inside_salesperson = ?")
            params.append(salesperson)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM customer c
            WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Get paginated results with route name join
        offset = (page - 1) * page_size
        fetch_count = offset + page_size
        query = f"""
            SELECT TOP {fetch_count}
                c.customer_id,
                c.customer_name,
                c.route_id,
                r.route_name,
                c.main_city,
                c.main_state,
                c.customer_type,
                c.inside_salesperson
            FROM customer c
            LEFT JOIN delivery_routes r ON c.route_id = r.route_id
            WHERE {where_clause}
            ORDER BY c.customer_name
        """

        cursor.execute(query, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()

        # Slice to get only the target page (Pervasive doesn't support SKIP)
        all_customers = [dict(zip(columns, row)) for row in rows]
        customers = all_customers[offset : offset + page_size]
        return customers, total

    async def get_customer_by_id(self, customer_id: str) -> dict[str, Any] | None:
        """
        Get detailed customer information by ID.

        Args:
            customer_id: Customer identifier (6 char)

        Returns:
            Customer dict with addresses and contacts, or None if not found
        """
        if self.is_agent_mode:
            return await self._get_customer_by_id_via_agent(customer_id)
        else:
            return self._get_customer_by_id_direct(customer_id)

    async def _get_customer_by_id_via_agent(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer by ID via agent (agent mode)"""
        from api.services.agent_schemas import FilterCondition, JoinClause

        # Get customer with route
        result = await self.agent_client.query_table(
            table="customer",
            alias="c",
            columns=None,  # All columns
            filters=[FilterCondition(column="c.customer_id", operator="=", value=customer_id)],
            joins=[
                JoinClause(
                    table="delivery_routes",
                    alias="r",
                    join_type="LEFT",
                    on_left="c.route_id",
                    on_right="r.route_id",
                )
            ],
            limit=1,
        )

        if not result.rows:
            return None

        customer = dict(zip([c.lower() for c in result.columns], result.rows[0]))

        # Get contacts
        contacts_result = await self.agent_client.query_table(
            table="customer_contacts",
            columns=[
                "contact_no",
                "first_name",
                "last_name",
                "title",
                "email",
                "work_phone",
                "mobl_phone",
                "fax",
            ],
            filters=[FilterCondition(column="customer_id", operator="=", value=customer_id)],
        )

        contacts = []
        for row in contacts_result.rows:
            contact = dict(zip([c.lower() for c in contacts_result.columns], row))
            # Rename mobl_phone to mobile_phone
            if "mobl_phone" in contact:
                contact["mobile_phone"] = contact.pop("mobl_phone")
            contacts.append(contact)

        return self._build_customer_response(customer, contacts)

    def _get_customer_by_id_direct(self, customer_id: str) -> dict[str, Any] | None:
        """Get customer by ID via direct ODBC (direct mode)"""
        cursor = self._get_cursor()

        # Get customer with route name
        query = """
            SELECT TOP 1
                c.*,
                r.route_name
            FROM customer c
            LEFT JOIN delivery_routes r ON c.route_id = r.route_id
            WHERE c.customer_id = ?
        """

        cursor.execute(query, [customer_id])
        row = cursor.fetchone()

        if not row:
            return None

        columns = [col[0].lower() for col in cursor.description]
        customer = dict(zip(columns, row))

        # Get contacts
        contacts_query = """
            SELECT
                contact_no,
                first_name,
                last_name,
                title,
                email,
                work_phone,
                mobl_phone as mobile_phone,
                fax
            FROM customer_contacts
            WHERE customer_id = ?
            ORDER BY contact_no
        """
        cursor.execute(contacts_query, [customer_id])
        contact_cols = [col[0].lower() for col in cursor.description]
        contact_rows = cursor.fetchall()

        contacts = [
            {k: v.strip() if isinstance(v, str) else v for k, v in dict(zip(contact_cols, row)).items()}
            for row in contact_rows
        ]

        return self._build_customer_response(customer, contacts)

    def _build_customer_response(
        self, customer: dict[str, Any], contacts: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build structured customer response from raw data"""

        def strip_val(val: Any) -> Any:
            return val.strip() if isinstance(val, str) and val else val if val else None

        return {
            "customer_id": strip_val(customer.get("customer_id")),
            "customer_name": strip_val(customer.get("customer_name")),
            "route_id": strip_val(customer.get("route_id")),
            "route_name": strip_val(customer.get("route_name")),
            "lookup_description": strip_val(customer.get("lookup_description")),
            "customer_type": strip_val(customer.get("customer_type")),
            "inside_salesperson": strip_val(customer.get("inside_salesperson")),
            "territory": strip_val(customer.get("territory")),
            "branch_id": strip_val(customer.get("branch_id")),
            # Main address
            "main_address": {
                "name": strip_val(customer.get("main_name")),
                "address1": strip_val(customer.get("main_address_1")),
                "address2": strip_val(customer.get("main_address_2")),
                "city": strip_val(customer.get("main_city")),
                "state": strip_val(customer.get("main_state")),
                "country": strip_val(customer.get("main_country")),
                "zip_code": strip_val(customer.get("main_zip_code")),
                "phone": strip_val(customer.get("main_phone_no")),
                "fax": strip_val(customer.get("main_fax_no")),
            },
            # Billing address
            "bill_address": {
                "name": strip_val(customer.get("billing_name")),
                "address1": strip_val(customer.get("billing_address_1")),
                "address2": strip_val(customer.get("billing_address_2")),
                "city": strip_val(customer.get("billing_city")),
                "state": strip_val(customer.get("billing_state")),
                "country": strip_val(customer.get("billing_country")),
                "zip_code": strip_val(customer.get("billing_zip_code")),
            },
            # Shipping address
            "ship_address": {
                "name": strip_val(customer.get("shipping_name")),
                "address1": strip_val(customer.get("shipping_address_1")),
                "address2": strip_val(customer.get("shipping_address_2")),
                "city": strip_val(customer.get("shipping_city")),
                "state": strip_val(customer.get("shipping_state")),
                "country": strip_val(customer.get("shipping_country")),
                "zip_code": strip_val(customer.get("shipping_zip_code")),
            },
            # Financial
            "credit_limit": customer.get("credit_limit"),
            "credit_terms_code": strip_val(customer.get("credit_terms_code")),
            "credit_hold": customer.get("credit_hold_flag") == "Y" if customer.get("credit_hold_flag") else None,
            "taxable": customer.get("taxable_flag") == "Y" if customer.get("taxable_flag") else None,
            # Stats
            "ytd_sales": customer.get("ytd_sales"),
            "last_sale_date": customer.get("last_sale_date"),
            "customer_since_date": customer.get("customer_since_date"),
            # Contacts
            "contacts": contacts,
        }

    # ========================================
    # Order Methods
    # ========================================

    async def get_orders(
        self,
        customer_id: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
        route_id: str | None = None,
        salesperson: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get list of orders with optional filtering and pagination.

        Args:
            customer_id: Filter by customer
            status: Filter by status ('O' = Open, 'C' = Closed)
            date_from: Start date
            date_to: End date
            search: Search in SO#, job name, or customer PO#
            route_id: Filter by route
            salesperson: Filter by inside salesperson
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of order dicts, total count)
        """
        if self.is_agent_mode:
            return await self._get_orders_via_agent(
                customer_id, status, date_from, date_to, search, route_id, salesperson, page, page_size
            )
        else:
            return self._get_orders_direct(
                customer_id, status, date_from, date_to, search, route_id, salesperson, page, page_size
            )

    async def _get_orders_via_agent(
        self,
        customer_id: str | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        route_id: str | None,
        salesperson: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get orders via agent (agent mode)"""
        from api.services.agent_schemas import FilterCondition, JoinClause, OrderBy

        # Build filters
        filters: list[FilterCondition] = []

        if customer_id:
            filters.append(FilterCondition(column="h.customer_id", operator="=", value=customer_id))

        if status:
            filters.append(FilterCondition(column="h.open_closed_flag", operator="=", value=status))

        if date_from:
            filters.append(FilterCondition(column="h.order_date", operator=">=", value=format_date_for_query(date_from)))

        if date_to:
            filters.append(FilterCondition(column="h.order_date", operator="<=", value=format_date_for_query(date_to)))

        if search:
            # Search on job_name only in agent mode (agent doesn't support OR)
            filters.append(FilterCondition(column="h.job_name", operator="LIKE", value=f"%{search}%"))

        if route_id:
            filters.append(FilterCondition(column="h.route_id", operator="=", value=route_id))

        if salesperson:
            filters.append(FilterCondition(column="h.inside_salesperson", operator="=", value=salesperson))

        # Get total count
        total = await self.agent_client.count_table("sales_orders_headers", filters)

        # Get paginated results
        offset = (page - 1) * page_size

        result = await self.agent_client.query_table(
            table="sales_orders_headers",
            alias="h",
            columns=[
                "h.so_no",
                "h.customer_id",
                "c.customer_name",
                "h.order_date",
                "h.job_name",
                "h.open_closed_flag",
                "h.ship_method",
                "h.customer_po_no",
                "h.inside_salesperson",
                "h.route_id",
            ],
            filters=filters,
            joins=[
                JoinClause(
                    table="customer",
                    alias="c",
                    join_type="LEFT",
                    on_left="h.customer_id",
                    on_right="c.customer_id",
                )
            ],
            order_by=[
                OrderBy(column="h.order_date", direction="DESC"),
                OrderBy(column="h.so_no", direction="DESC"),
            ],
            limit=page_size,
            offset=offset,
        )

        # Convert rows to dicts and process
        orders = []
        for row in result.rows:
            order = dict(zip([c.lower() for c in result.columns], row))
            order["order_date"] = parse_glasstrax_date(order.get("order_date"))
            flag = order.get("open_closed_flag")
            order["status"] = "Open" if flag == "O" else "Closed" if flag == "C" else None
            # Strip strings
            for key in ["customer_id", "customer_name", "job_name", "ship_method", "customer_po_no", "inside_salesperson", "route_id"]:
                if order.get(key) and isinstance(order[key], str):
                    order[key] = order[key].strip() or None
            orders.append(order)

        return orders, total

    def _get_orders_direct(
        self,
        customer_id: str | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
        search: str | None,
        route_id: str | None,
        salesperson: str | None,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get orders via direct ODBC (direct mode)"""
        cursor = self._get_cursor()

        # Build WHERE clause
        conditions = []
        params = []

        if customer_id:
            conditions.append("h.customer_id = ?")
            params.append(customer_id)

        if status:
            conditions.append("h.open_closed_flag = ?")
            params.append(status)

        if date_from:
            conditions.append("h.order_date >= ?")
            params.append(format_date_for_query(date_from))

        if date_to:
            conditions.append("h.order_date <= ?")
            params.append(format_date_for_query(date_to))

        if search:
            conditions.append(
                "(CAST(h.so_no AS VARCHAR(20)) LIKE ? OR h.job_name LIKE ? OR h.customer_po_no LIKE ?)"
            )
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

        if route_id:
            conditions.append("h.route_id = ?")
            params.append(route_id)

        if salesperson:
            conditions.append("h.inside_salesperson = ?")
            params.append(salesperson)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM sales_orders_headers h
            WHERE {where_clause}
        """
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]

        # Get paginated results with customer name
        offset = (page - 1) * page_size
        fetch_count = offset + page_size
        query = f"""
            SELECT TOP {fetch_count}
                h.so_no,
                h.customer_id,
                c.customer_name,
                h.order_date,
                h.job_name,
                h.open_closed_flag,
                h.ship_method,
                h.customer_po_no,
                h.inside_salesperson,
                h.route_id
            FROM sales_orders_headers h
            LEFT JOIN customer c ON h.customer_id = c.customer_id
            WHERE {where_clause}
            ORDER BY h.order_date DESC, h.so_no DESC
        """

        cursor.execute(query, params)
        columns = [col[0].lower() for col in cursor.description]
        rows = cursor.fetchall()

        all_orders = []
        for row in rows:
            order = dict(zip(columns, row))
            order["order_date"] = parse_glasstrax_date(order.get("order_date"))
            flag = order.get("open_closed_flag")
            order["status"] = "Open" if flag == "O" else "Closed" if flag == "C" else None
            for key in ["customer_id", "customer_name", "job_name", "ship_method", "customer_po_no", "inside_salesperson", "route_id"]:
                if order.get(key) and isinstance(order[key], str):
                    order[key] = order[key].strip() or None
            all_orders.append(order)

        orders = all_orders[offset : offset + page_size]
        return orders, total

    async def get_order_by_number(self, so_no: int) -> dict[str, Any] | None:
        """
        Get detailed order information including line items.

        Args:
            so_no: Sales order number (numeric)

        Returns:
            Order dict with line_items or None if not found
        """
        if self.is_agent_mode:
            return await self._get_order_by_number_via_agent(so_no)
        else:
            return self._get_order_by_number_direct(so_no)

    async def _get_order_by_number_via_agent(self, so_no: int) -> dict[str, Any] | None:
        """Get order by number via agent (agent mode)"""
        from api.services.agent_schemas import FilterCondition, JoinClause

        # Get order header
        result = await self.agent_client.query_table(
            table="sales_orders_headers",
            alias="h",
            columns=None,  # All columns
            filters=[FilterCondition(column="h.so_no", operator="=", value=so_no)],
            joins=[
                JoinClause(
                    table="customer",
                    alias="c",
                    join_type="LEFT",
                    on_left="h.customer_id",
                    on_right="c.customer_id",
                )
            ],
            limit=1,
        )

        if not result.rows:
            return None

        header = dict(zip([c.lower() for c in result.columns], result.rows[0]))

        # Get line items
        lines_result = await self.agent_client.query_table(
            table="sales_order_detail",
            columns=[
                "so_line_no",
                "item_id",
                "item_description",
                "cust_part_no",
                "order_qty",
                "shipped_qty",
                "bill_qty",
                "unit_price",
                "total_extended_price",
                "size_1",
                "size_2",
                "open_closed_flag",
            ],
            filters=[FilterCondition(column="so_no", operator="=", value=so_no)],
        )

        line_items = []
        for row in lines_result.rows:
            item = dict(zip([c.lower() for c in lines_result.columns], row))
            for key in ["item_id", "item_description", "cust_part_no", "open_closed_flag"]:
                if item.get(key) and isinstance(item[key], str):
                    item[key] = item[key].strip() or None
            line_items.append(item)

        return self._build_order_response(header, line_items)

    def _get_order_by_number_direct(self, so_no: int) -> dict[str, Any] | None:
        """Get order by number via direct ODBC (direct mode)"""
        cursor = self._get_cursor()

        # Get order header with customer name
        header_query = """
            SELECT TOP 1
                h.*,
                c.customer_name
            FROM sales_orders_headers h
            LEFT JOIN customer c ON h.customer_id = c.customer_id
            WHERE h.so_no = ?
        """

        cursor.execute(header_query, [so_no])
        header_row = cursor.fetchone()

        if not header_row:
            return None

        columns = [col[0].lower() for col in cursor.description]
        header = dict(zip(columns, header_row))

        # Get line items
        lines_query = """
            SELECT
                so_line_no,
                item_id,
                item_description,
                cust_part_no,
                order_qty,
                shipped_qty,
                bill_qty,
                unit_price,
                total_extended_price,
                size_1,
                size_2,
                open_closed_flag
            FROM sales_order_detail
            WHERE so_no = ?
            ORDER BY so_line_no
        """

        cursor.execute(lines_query, [so_no])
        line_columns = [col[0].lower() for col in cursor.description]
        line_rows = cursor.fetchall()

        line_items = []
        for row in line_rows:
            item = dict(zip(line_columns, row))
            for key in ["item_id", "item_description", "cust_part_no", "open_closed_flag"]:
                if item.get(key) and isinstance(item[key], str):
                    item[key] = item[key].strip() or None
            line_items.append(item)

        return self._build_order_response(header, line_items)

    def _build_order_response(
        self, header: dict[str, Any], line_items: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build structured order response from raw data"""

        def strip_val(val: Any) -> Any:
            return val.strip() if isinstance(val, str) and val else val if val else None

        total_qty = 0
        total_amount = 0
        for item in line_items:
            if item.get("order_qty"):
                total_qty += item["order_qty"]
            if item.get("total_extended_price"):
                total_amount += item["total_extended_price"]

        return {
            "so_no": header.get("so_no"),
            "customer_id": strip_val(header.get("customer_id")),
            "customer_name": strip_val(header.get("customer_name")),
            "branch_id": strip_val(header.get("branch_id")),
            "job_name": strip_val(header.get("job_name")),
            "quotation_no": header.get("quotation_no"),
            "type": strip_val(header.get("type")),
            # Status
            "open_closed_flag": strip_val(header.get("open_closed_flag")),
            "status": "Open" if header.get("open_closed_flag") == "O" else "Closed" if header.get("open_closed_flag") == "C" else None,
            "credit_hold_flag": strip_val(header.get("credit_hold_flag")),
            "verification_hold": strip_val(header.get("verification_hold")),
            # Dates
            "order_date": parse_glasstrax_date(header.get("order_date")),
            "ship_date": parse_glasstrax_date(header.get("ship_date")),
            "delivery_date": parse_glasstrax_date(header.get("delivery_date")),
            "quotation_date": parse_glasstrax_date(header.get("quotation_date")),
            "expiration_date": parse_glasstrax_date(header.get("expiration_date")),
            # References
            "customer_po_no": strip_val(header.get("customer_po_no")),
            "inside_salesperson": strip_val(header.get("inside_salesperson")),
            "route_id": strip_val(header.get("route_id")),
            # Contact
            "buyer_first_name": strip_val(header.get("buyer_first_name")),
            "buyer_last_name": strip_val(header.get("buyer_last_name")),
            "phone": strip_val(header.get("phone")),
            "email": strip_val(header.get("email")),
            # Billing address
            "bill_address": {
                "name": strip_val(header.get("billing_name")),
                "address1": strip_val(header.get("billing_address_1")),
                "address2": strip_val(header.get("billing_address_2")),
                "city": strip_val(header.get("billing_city")),
                "state": strip_val(header.get("billing_state")),
                "country": strip_val(header.get("billing_country")),
                "zip_code": strip_val(header.get("billing_zip_code")),
            },
            # Shipping address
            "ship_address": {
                "name": strip_val(header.get("shipping_name")),
                "address1": strip_val(header.get("shipping_address_1")),
                "address2": strip_val(header.get("shipping_address_2")),
                "city": strip_val(header.get("shipping_city")),
                "state": strip_val(header.get("shipping_state")),
                "country": strip_val(header.get("shipping_country")),
                "zip_code": strip_val(header.get("shipping_zip_code")),
            },
            # Shipping
            "ship_method": strip_val(header.get("ship_method")),
            "warehouse_id": strip_val(header.get("warehouse_id")),
            # Financial
            "pay_type": strip_val(header.get("pay_type")),
            "taxable": header.get("taxable_flag") == "Y" if header.get("taxable_flag") else None,
            "currency_id": strip_val(header.get("currency_id")),
            "amount_paid": header.get("amount_paid"),
            "surcharge": header.get("surcharge"),
            # Line items
            "line_items": line_items,
            "total_lines": len(line_items),
            "total_qty": total_qty,
            "total_amount": total_amount,
        }

    # ========================================
    # Utility Methods
    # ========================================

    async def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if connection successful, False otherwise
        """
        if self.is_agent_mode:
            return await self.agent_client.is_healthy()
        else:
            try:
                cursor = self._get_cursor()
                cursor.execute("SELECT 1")
                return True
            except Exception:
                return False

    def get_table_list(self) -> list[str]:
        """
        Get list of available tables (direct mode only).

        Returns:
            List of table names
        """
        if self.is_agent_mode:
            # Not supported in agent mode - tables are restricted by allowlist
            return []

        cursor = self._get_cursor()

        try:
            conn = self._get_connection()
            db_info = conn.getinfo(17)  # SQL_DATABASE_NAME
            cursor.tables(catalog=db_info, tableType="TABLE")

            tables = []
            for row in cursor.fetchall():
                if not row[2].startswith("SYSTEM") and not row[2].startswith("_"):
                    tables.append(row[2])

            return sorted(tables)
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
