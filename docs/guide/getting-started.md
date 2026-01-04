# Getting Started

This guide will help you set up and start using GlassTrax Bridge.

## Prerequisites

- **Windows Server** with GlassTrax installed
- **Pervasive ODBC Driver** (32-bit)
- **Python 3.11 32-bit** (bundled in `python32/` or install separately)
- **Node.js 18+** (for portal development)

## Installation

### 1. Clone or Extract the Project

```bash
git clone https://github.com/Codename-11/GlassTrax-Bridge.git
cd GlassTrax-Bridge
```

### 2. Install Dependencies

```bash
# Python dependencies
.\python32\python.exe -m pip install -r requirements.txt

# Node dependencies (for portal)
npm install
```

### 3. Configure Application

First, set up your ODBC DSN in Windows ODBC Data Source Administrator (32-bit).

Then copy and edit the configuration:

```bash
copy config.example.yaml config.yaml
notepad config.yaml
```

Key settings in `config.yaml`:

```yaml
database:
  friendly_name: "TGI Database"
  dsn: "LIVE"         # ODBC Data Source Name
  readonly: true
  timeout: 30
```

### 4. Initialize Database

```bash
.\python32\python.exe -m alembic upgrade head
```

### 5. Start the API Server

```bash
.\python32\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

::: tip First Run
On first run, an admin API key is auto-generated and displayed. **Save this key!** It won't be shown again.
:::

```
======================================================================
  INITIAL ADMIN API KEY GENERATED
======================================================================

  Key: gtb_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

  IMPORTANT: Save this key now! It will NOT be shown again.

======================================================================
```

### 4. Verify the API is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "glasstrax_connected": true,
  "app_db_connected": true
}
```

### 5. Start the Portal (Optional)

```bash
cd portal
npm install
npm run dev
```

Access the portal at `http://localhost:5173`

## Next Steps

- [Configure authentication](/guide/authentication)
- [Create your first application](/guide/applications)
- [Generate API keys](/guide/api-keys)
- [Explore the API](/api/)
