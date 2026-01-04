---
layout: home

hero:
  name: GlassTrax Bridge
  text: REST API for GlassTrax ERP
  tagline: Access your GlassTrax data through a modern, secure REST API
  actions:
    - theme: brand
      text: Get Started
      link: /guide/getting-started
    - theme: alt
      text: API Reference
      link: /api/

features:
  - icon: 🔐
    title: Secure Authentication
    details: JWT tokens and API keys with bcrypt hashing. Auto-generated admin key on first run.
  - icon: 🏢
    title: Multi-tenant
    details: Create applications with isolated API keys and permissions for different integrations.
  - icon: 📊
    title: Full Audit Trail
    details: Every API request is logged with attribution, timing, and status information.
  - icon: 🖥️
    title: Admin Portal
    details: Web-based management interface for keys, applications, and system diagnostics.
  - icon: ⚡
    title: Real-time Monitoring
    details: View access logs in real-time, run diagnostics, and manage server from the portal.
  - icon: 📖
    title: OpenAPI Documentation
    details: Auto-generated API documentation with interactive testing at /docs.
---

## Quick Start

### 1. Start the API Server

```bash
.\python32\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

On first run, an admin API key will be generated. **Save it!**

### 2. Test the API

```bash
curl http://localhost:8000/health
```

### 3. Access the Portal

Start the portal at `http://localhost:5173`:

```bash
cd portal && npm run dev
```

Login with `admin` / `admin` (or your admin API key).

---

<div style="text-align: center; margin-top: 2rem; color: #666;">
  <p>GlassTrax Bridge • Internal Use Only</p>
</div>
