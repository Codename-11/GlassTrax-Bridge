# GlassTrax Bridge Portal

Web-based management portal for the GlassTrax Bridge API.

## Overview

The portal provides a user interface for:
- Managing API keys (create, revoke, activate/deactivate)
- Managing applications (organizations)
- Viewing access logs and API usage
- System diagnostics and health monitoring
- Server management (restart, reset)

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **UI Components:** shadcn/ui
- **Styling:** Tailwind CSS v4
- **State Management:** TanStack Query (React Query)
- **Routing:** React Router v6
- **HTTP Client:** Axios

## Getting Started

### Prerequisites

- Node.js 18+ (v24 recommended)
- npm 9+
- API server running on port 8000

### Installation

```bash
cd portal
npm install
```

### Development

```bash
npm run dev
```

Portal runs at `http://localhost:5173`

### Production Build

```bash
npm run build
```

Output is in `portal/dist/`

## Configuration

### Environment Variables

The portal uses **relative URLs** by default, which works in both development and production:

- **Development:** Vite proxies `/api`, `/docs`, `/health` to backend services
- **Production:** Same-origin requests (everything served from one port)

For non-standard setups, you can override with `.env`:

```env
# Only needed if API is on a different origin
VITE_API_URL=https://api.yourdomain.com
```

## Authentication

The portal uses JWT-based authentication.

### Login Methods

1. **Username/Password**: Enter `admin` and your configured password
2. **API Key**: Enter `admin` and an API key with admin permissions as password

On successful login, a JWT token is stored and used for subsequent requests.

### Default Credentials

- Username: `admin`
- Password: `admin` (default - should be changed!)

To change the admin password, add a bcrypt hash to `config.yaml`:

```yaml
admin:
  username: "admin"
  password_hash: "$2b$12$..."  # Generate with bcrypt
```

## Pages

### Login (`/login`)

Authentication page supporting:
- Username/password login
- API key login (enter key as password)
- Shows warning if using default password

### Dashboard (`/`)

Overview showing:
- Total applications count
- Active API keys count
- Total API keys count
- Recent API requests (last 10)

### API Keys (`/keys`)

Manage API keys:
- **Create:** Generate new keys for an application
- **View:** See key prefix, permissions, usage stats
- **Activate/Deactivate:** Toggle key status
- **Delete:** Permanently revoke keys

**System Keys Section:** Shows bootstrap keys and their status (active/disabled).

When creating a key, the full key is shown **only once**. Copy and store it securely.

### Applications (`/applications`)

Manage applications (organizations):
- Create new applications
- View application details
- See associated API key counts
- Edit or delete applications

### Access Logs (`/logs`)

Real-time view of API requests:
- Auto-refreshes every 5 seconds
- Shows method, path, status, response time
- Identifies which API key made each request
- Color-coded status indicators

### Diagnostics (`/diagnostics`)

System health and management:

**Diagnostic Checks:**
- Python environment
- ODBC driver detection
- GlassTrax database connectivity
- App database status
- Configuration validation
- API endpoint testing (with response time)

**System Information:**
- Platform, Python version, architecture
- Configured timezone
- Working directory
- **Restart Server** button

**Danger Zone:**
- Database reset with confirmation
- Type "RESET DATABASE" to confirm
- Clears all API keys, applications, and logs

## Project Structure

```
portal/
├── src/
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Layout.tsx      # Main app layout with sidebar
│   │   │   └── Sidebar.tsx     # Navigation sidebar
│   │   └── ui/                 # shadcn/ui components
│   ├── pages/
│   │   ├── Login.tsx           # JWT login
│   │   ├── Dashboard.tsx       # Stats overview
│   │   ├── ApiKeys.tsx         # API key management
│   │   ├── Applications.tsx    # Application management
│   │   ├── AccessLogs.tsx      # Access log viewer
│   │   └── Diagnostics.tsx     # System diagnostics
│   ├── lib/
│   │   ├── api.ts              # API client & types
│   │   ├── auth.tsx            # Auth context & hooks
│   │   └── utils.ts            # Utility functions
│   ├── App.tsx                 # Router setup
│   ├── main.tsx                # Entry point
│   └── index.css               # Tailwind + CSS variables
├── package.json
├── tsconfig.json
├── vite.config.ts
└── components.json             # shadcn/ui config
```

## Features

### Auto-refresh

Access logs automatically refresh every 5 seconds to show real-time activity.

### Toast Notifications

Success/error messages appear as toast notifications using Sonner.

### Responsive Design

Layout adapts to different screen sizes with collapsible sidebar.

### Dark Mode Ready

Theme variables are configured for dark mode support (toggle coming soon).

## API Integration

All API calls go through `src/lib/api.ts`:

```typescript
import { api, tenantsApi, apiKeysApi, accessLogsApi } from '@/lib/api';

// List applications
const apps = await tenantsApi.list();

// Create API key
const result = await apiKeysApi.create({
  tenant_id: 1,
  name: 'My Key',
  permissions: ['customers:read'],
});

// Run diagnostics
const diagnostics = await diagnosticsApi.get();
```

## Adding shadcn/ui Components

```bash
npx shadcn@latest add [component-name]
```

Example:
```bash
npx shadcn@latest add select
npx shadcn@latest add tabs
```

## Troubleshooting

### "Network Error" on login
- Ensure API server is running (`npm run dev` or `run_dev.bat`)
- In dev mode, access via `http://localhost:5173` (Vite proxies to API)
- Check browser console for errors

### "Failed to fetch data" after login
- Check that the API server has restarted after code changes
- Verify your API key/JWT token is valid

### Components not rendering
- Run `npm install` to ensure dependencies
- Check for TypeScript errors in terminal

### Server restart from UI not working
- On Windows, the restart spawns a new console window
- Check for any processes blocking port 8000
