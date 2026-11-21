// Placeholder for local/dev builds. The prod nginx image overwrites this file at container start
// (see docker/render-config.sh) so a pre-built image can be pointed at any backend URL at runtime,
// without rebuilding - Vite's import.meta.env.VITE_API_BASE_URL only applies to source builds.
window.__APP_CONFIG__ = {}
