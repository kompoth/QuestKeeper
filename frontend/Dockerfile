# syntax=docker/dockerfile:1

# Dev: source is bind-mounted (see docker-compose.yml); deps are (re)installed at container start
# so a package.json change takes effect on the next restart without a rebuild.
FROM node:22-alpine AS dev
WORKDIR /app
EXPOSE 3000
CMD ["sh", "-c", "npm ci && npm run dev -- --host 0.0.0.0"]

FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Prod: static build served by nginx, with SPA fallback for vue-router's history mode. The backend
# URL is NOT baked in at build time - it's rendered into config.js at container start (see
# docker/render-config.sh) from a runtime env var, so one built image works for any self-hoster.
FROM nginx:1.29-alpine AS prod
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/render-config.sh /docker-entrypoint.d/30-render-config.sh
EXPOSE 80
