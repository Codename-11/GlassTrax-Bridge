### Description ###
# GlassTrax-Bridge - Python Interface for GlassTrax ERP
# - Access Log Model -
# Author: Bailey Dixon
# Date: 01/03/2026
# Python: 3.11
####################

"""
Access Log Model

Records all API requests for audit and analytics:
- Who: API key/tenant that made the request
- What: HTTP method, path, response status
- When: Timestamp
- How long: Response time
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String

from api.database import Base


class AccessLog(Base):
    """
    Access log model - records API request/response details.

    Used for:
    - Security auditing
    - Usage analytics
    - Rate limit tracking
    - Debugging/troubleshooting
    """

    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Request identification
    request_id = Column(String(36), nullable=False)  # UUID for correlation

    # Who made the request
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True)
    key_prefix = Column(String(12), nullable=True)  # For display when key is deleted

    # Request details
    method = Column(String(10), nullable=False)  # GET, POST, etc.
    path = Column(String(500), nullable=False)  # /api/v1/customers
    query_string = Column(String(1000), nullable=True)  # ?page=1&limit=10
    client_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)

    # Response details
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=True)  # Response time in milliseconds

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index("ix_access_logs_api_key_created", "api_key_id", "created_at"),
        Index("ix_access_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_access_logs_path_created", "path", "created_at"),
    )

    def __repr__(self):
        return f"<AccessLog(id={self.id}, method='{self.method}', path='{self.path}', status={self.status_code})>"

    @classmethod
    def create_from_request(
        cls,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: float,
        api_key_id: int | None = None,
        tenant_id: int | None = None,
        key_prefix: str | None = None,
        query_string: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
    ) -> "AccessLog":
        """
        Create an access log entry from request details.

        Args:
            request_id: UUID for request correlation
            method: HTTP method
            path: Request path
            status_code: HTTP response status
            response_time_ms: Response time in milliseconds
            api_key_id: ID of the API key used (if authenticated)
            tenant_id: ID of the tenant (if authenticated)
            key_prefix: First chars of API key for display
            query_string: Query parameters
            client_ip: Client IP address
            user_agent: Client user agent

        Returns:
            AccessLog instance (not yet committed to database)
        """
        return cls(
            request_id=request_id,
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            api_key_id=api_key_id,
            tenant_id=tenant_id,
            key_prefix=key_prefix,
            query_string=query_string,
            client_ip=client_ip,
            user_agent=user_agent,
        )
