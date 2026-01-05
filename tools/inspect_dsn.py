#!/usr/bin/env python
"""
GlassTrax DSN Inspection Tool

CLI tool for exploring the GlassTrax Pervasive database schema and data.
Outputs JSON by default (for programmatic use) with optional human-readable preview.

Usage:
    python inspect_dsn.py tables [--filter <pattern>] [--pretty]
    python inspect_dsn.py schema <table> [--sample-values] [--pretty]
    python inspect_dsn.py sample <table> [--limit N] [--filter col=val] [--pretty]
    python inspect_dsn.py search <keyword> [--pretty]
    python inspect_dsn.py columns <table> [--filter <pattern>] [--pretty]

Requires 32-bit Python for Pervasive ODBC compatibility.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path for config access
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pyodbc
except ImportError:
    print(json.dumps({
        "error": "pyodbc not available",
        "message": "This tool requires pyodbc. Run with python32 on Windows.",
        "hint": "Use: python32\\python.exe tools\\inspect_dsn.py"
    }, indent=2))
    sys.exit(1)


def load_dsn_from_config() -> str:
    """Load DSN from config.yaml"""
    import yaml
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config.get("database", {}).get("dsn", "LIVE")
    return "LIVE"


def get_connection(dsn: str) -> pyodbc.Connection:
    """Create ODBC connection to DSN"""
    try:
        conn = pyodbc.connect(f"DSN={dsn}", readonly=True, timeout=30)
        return conn
    except pyodbc.Error as e:
        print(json.dumps({
            "error": "connection_failed",
            "dsn": dsn,
            "message": str(e)
        }, indent=2))
        sys.exit(1)


def cmd_tables(conn: pyodbc.Connection, filter_pattern: Optional[str] = None) -> dict:
    """List all tables in the database"""
    cursor = conn.cursor()
    tables = []

    for row in cursor.tables():
        # Use positional indexing for compatibility across ODBC drivers
        # Standard columns: (table_cat, table_schem, table_name, table_type, remarks)
        table_name = row[2] if len(row) > 2 else str(row)
        table_type = row[3] if len(row) > 3 else "TABLE"
        table_schema = row[1] if len(row) > 1 else ""

        # Skip system tables
        if table_name.startswith("SYSTEM") or table_name.startswith("_"):
            continue

        # Apply filter if specified
        if filter_pattern and filter_pattern.lower() not in table_name.lower():
            continue

        tables.append({
            "name": table_name,
            "type": table_type,
            "schema": table_schema or ""
        })

    # Sort alphabetically
    tables.sort(key=lambda x: x["name"].lower())

    return {
        "command": "tables",
        "filter": filter_pattern,
        "count": len(tables),
        "tables": tables
    }


def cmd_schema(conn: pyodbc.Connection, table_name: str, sample_values: bool = False) -> dict:
    """Get schema for a specific table"""
    cursor = conn.cursor()
    columns = []

    try:
        for row in cursor.columns(table=table_name):
            # Use positional indexing for compatibility across ODBC drivers
            # Standard: (table_cat, table_schem, table_name, column_name, data_type,
            #           type_name, column_size, buffer_length, decimal_digits,
            #           num_prec_radix, nullable, remarks, column_def, sql_data_type,
            #           sql_datetime_sub, char_octet_length, ordinal_position, is_nullable)
            col_info = {
                "name": row[3] if len(row) > 3 else str(row),
                "type": row[5] if len(row) > 5 else "UNKNOWN",
                "size": row[6] if len(row) > 6 else None,
                "nullable": (row[10] == 1) if len(row) > 10 else True,
                "ordinal": row[16] if len(row) > 16 else 0
            }

            # Sample distinct values for low-cardinality columns
            if sample_values:
                try:
                    sample_cursor = conn.cursor()
                    # Get distinct values (limit to avoid huge queries)
                    query = f'SELECT DISTINCT TOP 20 "{col_info["name"]}" FROM "{table_name}"'
                    sample_cursor.execute(query)
                    values = [r[0] for r in sample_cursor.fetchall() if r[0] is not None]

                    # Only include if reasonable cardinality
                    if len(values) <= 15:
                        col_info["sample_values"] = [str(v)[:100] for v in values]
                        col_info["distinct_count"] = len(values)
                    else:
                        col_info["sample_values"] = [str(v)[:100] for v in values[:10]]
                        col_info["distinct_count"] = "15+"
                    sample_cursor.close()
                except pyodbc.Error:
                    col_info["sample_values"] = None

            columns.append(col_info)

        # Sort by ordinal position
        columns.sort(key=lambda x: x["ordinal"])

        # Get row count
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = cursor.fetchone()[0]
        except pyodbc.Error:
            row_count = None

        return {
            "command": "schema",
            "table": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns
        }

    except pyodbc.Error as e:
        return {
            "command": "schema",
            "table": table_name,
            "error": str(e)
        }


def cmd_sample(conn: pyodbc.Connection, table_name: str, limit: int = 10,
               filters: Optional[list] = None) -> dict:
    """Sample rows from a table"""
    cursor = conn.cursor()

    try:
        # Build query
        query = f'SELECT TOP {limit} * FROM "{table_name}"'
        params = []

        if filters:
            where_clauses = []
            for f in filters:
                if "=" in f:
                    col, val = f.split("=", 1)
                    where_clauses.append(f'"{col}" = ?')
                    params.append(val)
                elif "~" in f:  # LIKE pattern
                    col, val = f.split("~", 1)
                    where_clauses.append(f'"{col}" LIKE ?')
                    params.append(f"%{val}%")

            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

        cursor.execute(query, params)

        # Get column names
        columns = [desc[0] for desc in cursor.description]

        # Fetch rows
        rows = []
        for row in cursor.fetchall():
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i]
                # Convert to JSON-serializable
                if val is None:
                    row_dict[col] = None
                elif isinstance(val, (bytes, bytearray)):
                    row_dict[col] = val.hex()
                else:
                    row_dict[col] = str(val) if not isinstance(val, (int, float, bool)) else val
            rows.append(row_dict)

        return {
            "command": "sample",
            "table": table_name,
            "limit": limit,
            "filters": filters,
            "columns": columns,
            "row_count": len(rows),
            "rows": rows
        }

    except pyodbc.Error as e:
        return {
            "command": "sample",
            "table": table_name,
            "error": str(e)
        }


def cmd_search(conn: pyodbc.Connection, keyword: str) -> dict:
    """Search for tables and columns matching a keyword"""
    cursor = conn.cursor()
    keyword_lower = keyword.lower()

    results = {
        "tables": [],
        "columns": []
    }

    # Search tables
    for row in cursor.tables():
        table_name = row[2] if len(row) > 2 else str(row)
        table_type = row[3] if len(row) > 3 else "TABLE"
        if table_name.startswith("SYSTEM") or table_name.startswith("_"):
            continue

        if keyword_lower in table_name.lower():
            results["tables"].append({
                "name": table_name,
                "type": table_type
            })

    # Search columns across all tables
    tables_checked = set()
    for row in cursor.tables():
        table_name = row[2] if len(row) > 2 else str(row)
        if table_name.startswith("SYSTEM") or table_name.startswith("_"):
            continue
        if table_name in tables_checked:
            continue
        tables_checked.add(table_name)

        try:
            for col in cursor.columns(table=table_name):
                col_name = col[3] if len(col) > 3 else str(col)
                col_type = col[5] if len(col) > 5 else "UNKNOWN"
                if keyword_lower in col_name.lower():
                    results["columns"].append({
                        "table": table_name,
                        "column": col_name,
                        "type": col_type
                    })
        except pyodbc.Error:
            continue

    # Sort results
    results["tables"].sort(key=lambda x: x["name"].lower())
    results["columns"].sort(key=lambda x: (x["table"].lower(), x["column"].lower()))

    return {
        "command": "search",
        "keyword": keyword,
        "table_matches": len(results["tables"]),
        "column_matches": len(results["columns"]),
        "results": results
    }


def cmd_columns(conn: pyodbc.Connection, table_name: str, filter_pattern: Optional[str] = None) -> dict:
    """List columns for a table (quick view without sampling)"""
    cursor = conn.cursor()
    columns = []

    try:
        for row in cursor.columns(table=table_name):
            col_name = row[3] if len(row) > 3 else str(row)
            col_type = row[5] if len(row) > 5 else "UNKNOWN"
            col_size = row[6] if len(row) > 6 else None
            col_nullable = (row[10] == 1) if len(row) > 10 else True

            if filter_pattern and filter_pattern.lower() not in col_name.lower():
                continue

            columns.append({
                "name": col_name,
                "type": col_type,
                "size": col_size,
                "nullable": col_nullable
            })

        return {
            "command": "columns",
            "table": table_name,
            "filter": filter_pattern,
            "count": len(columns),
            "columns": columns
        }

    except pyodbc.Error as e:
        return {
            "command": "columns",
            "table": table_name,
            "error": str(e)
        }


def format_pretty(data: dict) -> str:
    """Format data as human-readable preview + JSON"""
    lines = []
    cmd = data.get("command", "")

    lines.append("=" * 60)

    if cmd == "tables":
        lines.append(f"TABLES ({data['count']} found)")
        if data.get("filter"):
            lines.append(f"Filter: {data['filter']}")
        lines.append("-" * 60)
        for t in data["tables"][:30]:  # Preview first 30
            lines.append(f"  {t['name']:<40} [{t['type']}]")
        if data["count"] > 30:
            lines.append(f"  ... and {data['count'] - 30} more")

    elif cmd == "schema":
        lines.append(f"SCHEMA: {data['table']}")
        if data.get("row_count") is not None:
            lines.append(f"Rows: {data['row_count']:,}")
        lines.append("-" * 60)
        for col in data.get("columns", []):
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            line = f"  {col['name']:<30} {col['type']:<15} {nullable}"
            if col.get("sample_values"):
                vals = ", ".join(str(v)[:20] for v in col["sample_values"][:5])
                line += f"  [{vals}]"
            lines.append(line)

    elif cmd == "sample":
        lines.append(f"SAMPLE: {data['table']} ({data['row_count']} rows)")
        if data.get("filters"):
            lines.append(f"Filters: {data['filters']}")
        lines.append("-" * 60)
        if data.get("rows"):
            # Show first few columns of each row
            for row in data["rows"][:10]:
                preview = ", ".join(f"{k}={str(v)[:30]}" for k, v in list(row.items())[:5])
                lines.append(f"  {preview}")

    elif cmd == "search":
        lines.append(f"SEARCH: '{data['keyword']}'")
        lines.append("-" * 60)
        lines.append(f"Tables matched: {data['table_matches']}")
        for t in data["results"]["tables"][:10]:
            lines.append(f"  [TABLE] {t['name']}")
        lines.append(f"Columns matched: {data['column_matches']}")
        for c in data["results"]["columns"][:15]:
            lines.append(f"  [COLUMN] {c['table']}.{c['column']} ({c['type']})")

    elif cmd == "columns":
        lines.append(f"COLUMNS: {data['table']} ({data['count']} columns)")
        lines.append("-" * 60)
        for col in data.get("columns", []):
            nullable = "NULL" if col["nullable"] else "NOT NULL"
            lines.append(f"  {col['name']:<30} {col['type']:<15} {nullable}")

    lines.append("=" * 60)
    lines.append("")
    lines.append("JSON OUTPUT:")
    lines.append(json.dumps(data, indent=2, default=str))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="GlassTrax DSN Inspection Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  inspect_dsn.py tables                      # List all tables
  inspect_dsn.py tables --filter customer    # Filter tables by name
  inspect_dsn.py schema customer             # Show table schema
  inspect_dsn.py schema customer --sample-values  # Include sample values
  inspect_dsn.py sample customer --limit 5   # Sample 5 rows
  inspect_dsn.py sample orders --filter status=O  # Filter by column
  inspect_dsn.py search order                # Search tables/columns
  inspect_dsn.py columns customer            # Quick column list
        """
    )

    parser.add_argument("--dsn", help="ODBC DSN name (default: from config.yaml)")
    parser.add_argument("--pretty", "-p", action="store_true",
                        help="Human-readable preview with JSON")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # tables command
    tables_parser = subparsers.add_parser("tables", help="List all tables")
    tables_parser.add_argument("--filter", "-f", help="Filter tables by name pattern")

    # schema command
    schema_parser = subparsers.add_parser("schema", help="Show table schema")
    schema_parser.add_argument("table", help="Table name")
    schema_parser.add_argument("--sample-values", "-s", action="store_true",
                               help="Include sample values for columns")

    # sample command
    sample_parser = subparsers.add_parser("sample", help="Sample rows from table")
    sample_parser.add_argument("table", help="Table name")
    sample_parser.add_argument("--limit", "-l", type=int, default=10,
                               help="Number of rows to sample (default: 10)")
    sample_parser.add_argument("--filter", "-f", action="append", dest="filters",
                               help="Filter by column (col=value or col~pattern)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search tables/columns")
    search_parser.add_argument("keyword", help="Keyword to search for")

    # columns command
    columns_parser = subparsers.add_parser("columns", help="List table columns")
    columns_parser.add_argument("table", help="Table name")
    columns_parser.add_argument("--filter", "-f", help="Filter columns by name pattern")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Get DSN
    dsn = args.dsn or load_dsn_from_config()

    # Connect
    conn = get_connection(dsn)

    try:
        # Execute command
        if args.command == "tables":
            result = cmd_tables(conn, args.filter)
        elif args.command == "schema":
            result = cmd_schema(conn, args.table, args.sample_values)
        elif args.command == "sample":
            result = cmd_sample(conn, args.table, args.limit, args.filters)
        elif args.command == "search":
            result = cmd_search(conn, args.keyword)
        elif args.command == "columns":
            result = cmd_columns(conn, args.table, args.filter)
        else:
            print(json.dumps({"error": f"Unknown command: {args.command}"}))
            sys.exit(1)

        # Add metadata
        result["dsn"] = dsn

        # Output
        if args.pretty:
            print(format_pretty(result))
        else:
            print(json.dumps(result, indent=2, default=str))

    finally:
        conn.close()


if __name__ == "__main__":
    main()
