"""
Test that Pydantic schemas properly coerce int values to strings.

This is specifically for handling the agent's auto-conversion of numeric strings to ints.
"""

import pytest

from api.schemas.order import OrderResponse, OrderListResponse, OrderExistsResponse
from api.schemas.customer import CustomerResponse, CustomerListResponse


class TestOrderSchemaCoercion:
    """Test OrderResponse handles int values for string fields."""

    def test_order_response_coerces_int_customer_id(self):
        """customer_id should accept int and coerce to str."""
        data = {"so_no": 188591, "customer_id": 1610}
        order = OrderResponse(**data)
        assert order.customer_id == "1610"
        assert isinstance(order.customer_id, str)

    def test_order_response_coerces_int_customer_po_no(self):
        """customer_po_no should accept int and coerce to str."""
        data = {"so_no": 188591, "customer_id": "TEST", "customer_po_no": 23449}
        order = OrderResponse(**data)
        assert order.customer_po_no == "23449"
        assert isinstance(order.customer_po_no, str)

    def test_order_response_coerces_int_pay_type(self):
        """pay_type should accept int and coerce to str."""
        data = {"so_no": 188591, "customer_id": "TEST", "pay_type": 5}
        order = OrderResponse(**data)
        assert order.pay_type == "5"
        assert isinstance(order.pay_type, str)

    def test_order_response_coerces_int_route_id(self):
        """route_id should accept int and coerce to str."""
        data = {"so_no": 188591, "customer_id": "TEST", "route_id": 12}
        order = OrderResponse(**data)
        assert order.route_id == "12"
        assert isinstance(order.route_id, str)

    def test_order_list_response_coerces_ints(self):
        """OrderListResponse should coerce int values."""
        data = {"so_no": 188591, "customer_id": 1610, "customer_po_no": 23449}
        order = OrderListResponse(**data)
        assert order.customer_id == "1610"
        assert order.customer_po_no == "23449"

    def test_order_exists_response_coerces_ints(self):
        """OrderExistsResponse should coerce int values."""
        data = {"exists": True, "so_no": 188591, "customer_id": 1610, "customer_po_no": 23449}
        order = OrderExistsResponse(**data)
        assert order.customer_id == "1610"
        assert order.customer_po_no == "23449"


class TestCustomerSchemaCoercion:
    """Test CustomerResponse handles int values for string fields."""

    def test_customer_response_coerces_int_customer_id(self):
        """customer_id should accept int and coerce to str."""
        data = {"customer_id": 1610, "customer_name": "Test Customer"}
        customer = CustomerResponse(**data)
        assert customer.customer_id == "1610"
        assert isinstance(customer.customer_id, str)

    def test_customer_response_coerces_int_route_id(self):
        """route_id should accept int and coerce to str."""
        data = {"customer_id": "TEST", "customer_name": "Test Customer", "route_id": 5}
        customer = CustomerResponse(**data)
        assert customer.route_id == "5"
        assert isinstance(customer.route_id, str)

    def test_customer_list_response_coerces_ints(self):
        """CustomerListResponse should coerce int values."""
        data = {"customer_id": 1610, "customer_name": "Test Customer", "route_id": 5}
        customer = CustomerListResponse(**data)
        assert customer.customer_id == "1610"
        assert customer.route_id == "5"
