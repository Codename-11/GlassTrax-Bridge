### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - API Services Package -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
API Services Package

Contains business logic and data access services:
- glasstrax: GlassTrax database access layer
- auth: Authentication and authorization logic
"""

from .glasstrax import GlassTraxService

__all__ = ["GlassTraxService"]
