### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Routers Package -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Routers Package

Contains endpoint routers for different resources:
- customers: Customer data endpoints
- orders: Order data endpoints
- keys: API key management endpoints
- auth: Portal authentication endpoints
"""

from .customers import router as customers_router
from .orders import router as orders_router
from .keys import router as keys_router

__all__ = ["customers_router", "orders_router", "keys_router"]
