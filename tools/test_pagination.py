#!/usr/bin/env python
"""
Test pagination for /orders/fabs endpoint.

Usage:
    python tools/test_pagination.py [--url URL] [--key KEY] [--date DATE]

Examples:
    python tools/test_pagination.py
    python tools/test_pagination.py --date 2026-01-13
    python tools/test_pagination.py --url http://localhost:8000 --key gtb_xxx
"""

import argparse
import sys
from datetime import date

import httpx


def test_pagination(base_url: str, api_key: str, order_date: str, page_size: int = 100):
    """Test pagination by fetching all pages and comparing counts."""
    headers = {"X-API-Key": api_key} if api_key else {}

    print(f"\n{'='*60}")
    print(f"Testing pagination for /orders/fabs")
    print(f"URL: {base_url}")
    print(f"Date: {order_date}")
    print(f"Page size: {page_size}")
    print(f"{'='*60}\n")

    all_orders = []
    page = 1

    with httpx.Client(base_url=base_url, headers=headers, timeout=60.0) as client:
        while True:
            print(f"Fetching page {page}...", end=" ")

            response = client.get(
                "/api/v1/orders/fabs",
                params={"date": order_date, "page": page, "page_size": page_size},
            )

            if response.status_code != 200:
                print(f"ERROR: {response.status_code}")
                print(response.text)
                return False

            data = response.json()
            orders = data.get("data", [])
            pagination = data.get("pagination", {})

            print(f"{len(orders)} orders (total_items={pagination.get('total_items')}, has_next={pagination.get('has_next')})")

            all_orders.extend(orders)

            if not pagination.get("has_next", False):
                break

            page += 1

            if page > 20:  # Safety limit
                print("WARNING: Exceeded 20 pages, stopping")
                break

    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Total pages fetched: {page}")
    print(f"Total orders fetched: {len(all_orders)}")

    # Check for duplicates
    so_lines = [(o.get("so_no"), o.get("line_no")) for o in all_orders]
    unique_so_lines = set(so_lines)

    if len(so_lines) != len(unique_so_lines):
        print(f"WARNING: Found {len(so_lines) - len(unique_so_lines)} duplicate SO/line combinations!")
    else:
        print(f"No duplicates found (all SO/line combinations unique)")

    # Show sample
    if all_orders:
        print(f"\nFirst 3 orders:")
        for o in all_orders[:3]:
            print(f"  FAB# {o.get('fab_number')}: SO {o.get('so_no')}-{o.get('line_no')} - {o.get('customer_name', 'Unknown')[:30]}")

        if len(all_orders) > 3:
            print(f"\nLast 3 orders:")
            for o in all_orders[-3:]:
                print(f"  FAB# {o.get('fab_number')}: SO {o.get('so_no')}-{o.get('line_no')} - {o.get('customer_name', 'Unknown')[:30]}")

    print(f"\n{'='*60}")
    print("PASS" if len(all_orders) > 0 else "NO DATA")
    print(f"{'='*60}\n")

    return True


def main():
    parser = argparse.ArgumentParser(description="Test pagination for /orders/fabs endpoint")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--key", default="", help="API key (optional for local testing)")
    parser.add_argument("--date", default=date.today().isoformat(), help="Order date (YYYY-MM-DD)")
    parser.add_argument("--page-size", type=int, default=100, help="Page size to test")

    args = parser.parse_args()

    try:
        success = test_pagination(args.url, args.key, args.date, args.page_size)
        sys.exit(0 if success else 1)
    except httpx.ConnectError:
        print(f"ERROR: Could not connect to {args.url}")
        print("Is the API server running?")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
