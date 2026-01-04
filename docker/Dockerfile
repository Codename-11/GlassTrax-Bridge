# GlassTrax-Bridge - Multi-stage Dockerfile
# Builds portal and docs, with optional API proxy to Windows host
#
# MODES:
#   1. Standalone: API runs in container (no GlassTrax access)
#   2. Proxy: API_HOST points to Windows machine running the API
#
# Usage:
#   docker-compose up -d                    # Standalone mode
#   API_HOST=192.168.1.100 docker-compose up -d  # Proxy to Windows

# ============================================
# Stage 1: Build Portal (Vite + React)
# ============================================
FROM node:20-alpine AS portal-builder

WORKDIR /build/portal

# Copy package files first for better caching
COPY portal/package*.json ./
RUN npm ci

# Copy source and build
COPY portal/ ./
RUN npm run build

# ============================================
# Stage 2: Build VitePress Documentation
# ============================================
FROM node:20-alpine AS docs-builder

WORKDIR /build/docs

# Copy package files
COPY docs/package*.json ./
RUN npm ci

# Copy source and build
COPY docs/ ./
RUN npm run build

# ============================================
# Stage 3: Production Runtime
# ============================================
FROM python:3.11-slim

# Install nginx, supervisor, and utilities
RUN apt-get update && apt-get install -y \
    nginx \
    supervisor \
    gettext-base \
    curl \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor

WORKDIR /app

# Copy Python requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source code and utilities
COPY api/ ./api/
COPY utils/ ./utils/
COPY config.yaml ./
COPY VERSION ./

# Copy built portal from stage 1
COPY --from=portal-builder /build/portal/dist ./portal/dist

# Copy built docs from stage 2
COPY --from=docs-builder /build/docs/.vitepress/dist ./docs/.vitepress/dist

# Copy nginx template (will be processed by entrypoint)
COPY docker/nginx.conf.template /etc/nginx/nginx.conf.template

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Copy and setup entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Create data directory for SQLite
RUN mkdir -p /app/data && chmod 777 /app/data

# Environment variables for API proxy
ENV API_HOST=localhost
ENV API_PORT=8000

# Expose ports
# 80 - Portal + Documentation (nginx)
# 8000 - API (uvicorn) - only used in standalone mode
EXPOSE 80 8000

# Health check (nginx only - API may be external)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/nginx-health || exit 1

# Use entrypoint to configure nginx and start services
ENTRYPOINT ["/entrypoint.sh"]
