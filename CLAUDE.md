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
- Run integration tests (requires `DATABASE_URL` pointing at a reachable MySQL instance): `uv run pytest tests/integration`

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
