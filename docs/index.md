---
layout: home

hero:
  name: GlassTrax Bridge
  text: REST API for GlassTrax ERP
  tagline: Access your GlassTrax data through a modern, secure REST API
  image:
    src: /logo.svg
    alt: GlassTrax Bridge
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: API Reference
      link: /api/

features:
  - icon: 🔐
    title: Secure by Design
    details: API key authentication with bcrypt hashing, JWT tokens for portal access, and read-only database connections.
  - icon: 🏢
    title: Multi-Tenant Architecture
    details: Create isolated applications with their own API keys, permissions, and rate limits for different integrations.
  - icon: 📊
    title: Full Audit Trail
    details: Every API request is logged with attribution, timing, and status. Export logs and filter by date, key, or endpoint.
  - icon: 🖥️
    title: Admin Portal
    details: Modern web interface for managing API keys, applications, settings, and system diagnostics.
  - icon: 🐳
    title: Flexible Deployment
    details: Docker + Windows Agent (recommended), Windows standalone, or Docker-only for testing.
  - icon: ⚡
    title: Real-Time Monitoring
    details: Live access logs, connection status indicators, and one-click diagnostics from the portal.
---

<p align="center">
  <img src="/screenshots/glasstrax_bridge_main_dashboard.png" alt="GlassTrax Bridge Dashboard" style="max-width: 90%; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
</p>

## What is GlassTrax Bridge?

GlassTrax Bridge provides a modern REST API layer on top of your GlassTrax ERP system. It enables secure, read-only access to customer, order, and other business data through a well-documented API.

### Key Capabilities

| Feature | Description |
|---------|-------------|
| **REST API** | JSON-based endpoints for customers, orders, and more |
| **Admin Portal** | Web UI for managing keys, viewing logs, and configuration |
| **Multi-Tenant** | Separate API keys per application with granular permissions |
| **Audit Logging** | Complete request history with filtering and CSV export |
| **Rate Limiting** | Per-key request limits to protect your database |

### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Your Apps     │────▶│  GlassTrax      │────▶│   GlassTrax     │
│   (API Client)  │     │  Bridge API     │     │   Database      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────────┐
                        │  Admin Portal   │
                        │  (Web UI)       │
                        └─────────────────┘
```

For Docker deployments, the API connects to a Windows agent for ODBC access:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Docker        │────▶│   Windows       │────▶│   GlassTrax     │
│   (API+Portal)  │     │   Agent         │     │   Database      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Quick Links

<div class="quick-links">

- 📖 **[Getting Started](/guide/getting-started)** - Installation and first-time setup
- 🔑 **[Authentication](/guide/authentication)** - API keys and admin login
- 📚 **[API Reference](/api/)** - Endpoint documentation
- 🐳 **[Deployment Guide](/guide/deployment)** - Docker and Windows options
- ⚙️ **[Configuration](/guide/configuration)** - Settings and customization

</div>

## Requirements

| Component | Requirement |
|-----------|-------------|
| **Docker Host** | Docker with docker-compose |
| **Windows Agent** | Windows with Pervasive ODBC driver |
| **Browser** | Modern browser for admin portal |

::: tip Ready to get started?
Follow the [Getting Started guide](/guide/getting-started) for step-by-step installation instructions.
:::

---

<div style="text-align: center; margin-top: 2rem; color: #666;">
  <p>Copyright © 2025-2026 Axiom-Labs. All Rights Reserved.</p>
</div>
