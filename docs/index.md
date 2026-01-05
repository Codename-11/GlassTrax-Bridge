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
  - icon: 🐳
    title: Docker + Agent (Recommended)
    details: Run API and portal in Docker, with a lightweight Windows agent for Pervasive ODBC access.
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
---

<p align="center">
  <img src="/screenshots/glasstrax_bridge_main_dashboard.png" alt="GlassTrax Bridge Dashboard" style="max-width: 90%; border-radius: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
</p>

## Installation Methods

### Docker + Windows Agent (Recommended)

The recommended deployment runs the API and admin portal in Docker, with a lightweight Windows agent installed on the machine with GlassTrax ODBC access.

**Step 1:** Install the GlassTrax API Agent on Windows
- Download `GlassTraxAPIAgent-X.X.X-Setup.exe` from [Releases](https://github.com/Codename-11/GlassTrax-Bridge/releases)
- Run installer and start agent from system tray
- Save the API key shown on first run

**Step 2:** Start Docker with agent connection
```bash
AGENT_ENABLED=true \
AGENT_URL=http://YOUR_WINDOWS_IP:8001 \
AGENT_KEY=gta_your_key_here \
docker-compose up -d
```

**Step 3:** Access the application
- Portal: `http://localhost:3000`
- Agent health: `http://WINDOWS_IP:8001/health`

::: tip Why Docker + Agent?
- **Separation of concerns**: Docker handles the web stack, Windows handles ODBC
- **Easy updates**: Update Docker container without touching the Windows agent
- **Security**: Only the agent has direct database access
- **Cross-platform**: Run the portal anywhere Docker runs
:::

---

### Other Installation Methods (Beta)

::: warning Beta Methods
The following methods are available but considered beta. Docker + Agent is the recommended approach for production deployments.
:::

#### Windows All-in-One

Run everything directly on Windows. Requires 32-bit Python for Pervasive ODBC.

```bash
# Clone and setup
git clone https://github.com/Codename-11/GlassTrax-Bridge.git
cd GlassTrax-Bridge

# Start production server
.\run_prod.bat
```

#### Docker Standalone

For testing without GlassTrax database access:

```bash
docker pull ghcr.io/codename-11/glasstrax-bridge:latest
docker-compose up -d
```

---

<div style="text-align: center; margin-top: 2rem; color: #666;">
  <p>GlassTrax Bridge • Copyright (c) 2025-2026 Axiom-Labs</p>
</div>
