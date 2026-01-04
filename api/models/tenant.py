### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Tenant Model -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Tenant Model

Represents an organization/application that accesses the API.
Each tenant can have multiple API keys with different permissions.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from api.database import Base


class Tenant(Base):
    """
    Tenant model - represents an organization or application.

    Examples:
        - "Warehouse App" - internal warehouse management
        - "Sales Dashboard" - internal sales reporting
        - "Partner Integration" - external partner access
    """

    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant(id={self.id}, name='{self.name}')>"
