#!/bin/sh
# Runs via nginx's /docker-entrypoint.d/ hook, before nginx starts. Overwrites the build-time
# placeholder (public/config.js) with the real backend URL, read from a runtime env var - so the
# same pre-built image works for any self-hoster without rebuilding.
set -eu

cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = { apiBaseUrl: "${VITE_API_BASE_URL:-}" }
EOF
