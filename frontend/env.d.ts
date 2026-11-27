/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

declare const __APP_VERSION__: string

// Written by public/config.js (dev placeholder) or docker/render-config.sh (prod container
// entrypoint) - lets a pre-built frontend image be pointed at any backend URL at runtime.
interface Window {
  __APP_CONFIG__?: { apiBaseUrl?: string }
}
