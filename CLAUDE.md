# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Instruction conventions

- Write each entry as a short, atomic list item, one fact or rule per entry.
- Atomic entries keep future diffs to this file atomic (one entry added/changed per change).
- Avoid merging multiple rules into one entry or one prose paragraph.

## Comments

- Don't comment every change, most code should read clearly from naming alone.
- Add a comment only for a non-obvious invariant or constraint.
- Write comments as facts about the current code, not relative to what it used to do (no "unlike before", "can't do X like the old approach").
- Keep comments non-verbose and straight to the point: 1-2 lines, 3 lines max.

## Commit conventions

- Follow the Conventional Commits spec (`type(scope): subject`, e.g. `feat(backend): add entity persistence`).
- Keep each commit message clear and short.

## Project

- Questkeeper is a tabletop campaign knowledge base: wiki-style entities with articles and maps, organized per "world".
- Monorepo with independent `backend/` and `frontend/` projects.
- One `.env` at the repo root (gitignored; `.env.example` documents it) is shared by both — backend resolves it by absolute path (`app/config.py`), frontend via Vite's `envDir` (`vite.config.mts`), so it's found regardless of which directory a command is run from.
- Only `VITE_`-prefixed vars in that file are exposed to frontend client code; backend vars stay server-side. Backend's `Settings` uses `extra="ignore"` since the shared file carries frontend-only vars it doesn't declare as fields.
- A single root `VERSION` file (semver) is the project's shared version — `backend/pyproject.toml`'s `version` and `frontend/package.json`'s `version` must always match it.
- Bump the version with `python3 scripts/bump_version.py {major|minor|patch|<explicit semver>}`, run from the repo root — it updates `VERSION`, `backend/pyproject.toml`, and `frontend/package.json` together. Don't hand-edit any of the three in isolation.

## Backend (`backend/`)

- Python 3.14, FastAPI/Pydantic, managed with `uv`.
- Currently only data models exist (`backend/app/core/models.py`) — no API routes, persistence, or tests yet.
- Ruff lint selects `ALL` rules (see `pyproject.toml` for the ignore list); keep new code compliant rather than adding ignores.
- Docstring convention is Google style, but `D` is ignored project-wide, so docstrings are optional.
- Line length: 120.

Commands (run from `backend/`):
- Install deps: `uv sync`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run ty check .`
- Run unit tests: `uv run pytest tests/unit`
- Run integration tests (requires `DATABASE_URL` pointing at a reachable MariaDB instance): `uv run pytest tests/integration`
- The integration suite calls `Base.metadata.create_all`/`drop_all` on whatever `DATABASE_URL` resolves to (from `.env` if not overridden) — never point it at a DB used for manual/dev testing, or the suite's teardown wipes it.
- Local convenience: a disposable `questkeeper-mariadb-test` container (mariadb:11, db `questkeeper_test`, port 3308) mirrors CI's isolated service container; run tests against it with `DATABASE_URL=mysql+aiomysql://root:root@127.0.0.1:3308/questkeeper_test uv run pytest tests/integration`.
- Media storage is an S3-compatible object store, run locally via [Garage](https://garagehq.deuxfleurs.fr/) (not MinIO — MinIO's Docker image is no longer freely pullable). Dev: `questkeeper-garage-dev` (port 9100, bucket `questkeeper-media`, matches `.env`). Test: a disposable `questkeeper-garage-test` (port 9200, bucket `questkeeper-test`) mirrors the mariadb-test convention above — a real S3-compatible store is required for integration tests, since the test suite verifies the store itself enforces upload size/content-type (via presigned POST conditions), not just the application wiring; `adobe/s3mock` was tried and rejected for this because it never validates presigned URLs or POST policy conditions at all (accepts any upload regardless of signed constraints). Both containers: `docker run -d --name <name> -p <port>:3900 -p <port+1>:3901 -p <port+3>:3903 -v <garage.toml>:/etc/garage.toml -e GARAGE_DEFAULT_ACCESS_KEY=... -e GARAGE_DEFAULT_SECRET_KEY=... -e GARAGE_DEFAULT_BUCKET=... dxflrs/garage:v2.5.0 /garage server --single-node --default-bucket` (minimal `garage.toml`: `replication_factor = 1`, `db_engine = "sqlite"`, ephemeral `/tmp` dirs, a random `rpc_secret`, `[s3_api]` with `s3_region = "garage"`). Run tests against it with `S3_ENDPOINT_URL=http://localhost:9200 S3_ACCESS_KEY=questkeeper S3_SECRET_KEY=questkeeper-test-secret S3_BUCKET=questkeeper-test S3_REGION=garage uv run pytest tests/integration` (combine with the `DATABASE_URL` override above).

### Domain model (`app/core/models.py`)

- `Entity`: the core object — has `id`, `world_id`, `parent`/`children` for tree nesting.
- `Entity` has optional `article: Article | None` and `map: Map | None`.
- An entity is a composition of these two optional facets, not a subtype hierarchy — it can have neither, either, or (in principle) both.
- `World`: top-level container entities belong to.
- `Map.pins`: keyed by `tuple[float, float]` coordinates, each pointing to a `MapPin` referencing an `EntityId`.
- `User`/`UserRole`: admin / warden / member roles, not yet wired to any auth flow.

## Frontend (`frontend/`)

- Vue 3 + TypeScript + Vuetify 4, built with Vite.
- No backend integration yet — `src/data/*.ts` holds temporary in-memory mocks standing in for a future API client; don't treat their current shape as settled design.
- No test runner is configured yet.

Commands (run from `frontend/`):
- Dev server: `npm run dev`
- Build (type-checks then builds): `npm run build`
- Type check only: `npm run type-check`
- Lint: `npm run lint`
- Preview production build: `npm run preview`

### Structure

- `src/router/index.ts`: manual (not file-based) routes.
- Route nesting mirrors the domain: `/w` (worlds list) → `/w/:worldId` (`World` layout) → `/w/:worldId/e/:entityId` (`EntityView`).
- `src/layouts/*.vue`: route-level shells (`Landing`, `Login`, `World`, `Worlds`).
- `src/views/`: route-level pages nested inside layouts (e.g. `views/world/EntityView.vue` renders inside `layouts/World.vue`).
- `src/components/EntityArticle.vue` / `EntityMap.vue`: render an entity's `article` or `map` facet.
- `EntityView.vue` picks one of `EntityArticle`/`EntityMap` based on which facet is present (map takes precedence), matching the backend's optional-facet composition.
- `src/utils/nav.ts`: builds the recursive sidebar nav tree (`NavItem`) from entity parent/child relationships, used by `NavBar`.
- Import alias `@/` maps to `src/`.

### Conventions

- ESLint config extends `eslint-config-vuetify` (`eslint.config.js`); flat config format.
- Use `<script lang="ts" setup>` composition API throughout; prefer the same for new components.
- Don't run a Playwright browser verification pass on a change unless explicitly asked — it's slow; lint/type-check/build is the default bar for "done".
