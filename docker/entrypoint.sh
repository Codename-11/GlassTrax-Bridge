#!/bin/bash
# GlassTrax Bridge - Docker Entrypoint
# Starts nginx and API services

set -e

echo "========================================"
echo " GlassTrax Bridge - Docker Container"
echo "========================================"
echo ""

# Check if agent mode is configured
if [ "${GLASSTRAX_AGENT_ENABLED}" = "true" ]; then
    echo " Mode: Agent (connecting to Windows agent)"
    echo " Agent URL: ${GLASSTRAX_AGENT_URL:-not set}"
else
    echo " Mode: Standalone (no GlassTrax access)"
fi

echo ""
echo " Portal:     http://localhost:3000"
echo " User Docs:  http://localhost:3000/docs"
echo " API:        http://localhost:3000/api/v1"
echo " Swagger:    http://localhost:3000/api/docs"
echo ""
echo "========================================"
echo ""

# Copy nginx config (no longer needs template substitution)
cp /etc/nginx/nginx.conf.template /etc/nginx/sites-available/default

# Ensure nginx can read the config
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Start supervisord (manages nginx and API)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
