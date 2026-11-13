# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Comments

Don't comment every change — most code should read clearly from naming alone. When a comment is warranted (a non-obvious invariant or constraint), write it as a fact about the current code, not relative to what the code used to do. A reader with no diff or change history must be able to understand it on its own; "can't do X like before" or "unlike the old approach" fails that test.

## Project

Questkeeper: a tabletop campaign knowledge base (wiki-style entities with articles and maps, organized per "world"). Monorepo with independent `backend/` and `frontend/` projects.

## Backend (`backend/`)

Python 3.14, FastAPI/Pydantic, managed with `uv`. Currently only data models exist (`backend/app/core/models.py`) — no API routes, persistence, or tests yet.

Commands (run from `backend/`):
- Install deps: `uv sync`
- Lint: `uv run ruff check .`
- Format: `uv run ruff format .`
- Type check: `uv run ty check .`

Ruff lint selects `ALL` rules (see `pyproject.toml` for the ignore list); keep new code compliant rather than adding ignores. Docstring convention is Google style, but `D` is ignored project-wide so docstrings are optional. Line length 120.

### Domain model (`app/core/models.py`)

- `Entity`: the core object — has `id`, `world_id`, `parent`/`children` for tree nesting, and optional `article: Article | None` and `map: Map | None`. An entity is a composition of these two optional facets, not a subtype hierarchy — an entity can have neither, either, or (in principle) both.
- `World`: top-level container entities belong to.
- `Map.pins`: keyed by `tuple[float, float]` coordinates, each pointing to a `MapPin` referencing an `EntityId`.
- `User`/`UserRole`: admin / warden / member roles, not yet wired to any auth flow.

## Frontend (`frontend/`)

Vue 3 + TypeScript + Vuetify 4, built with Vite. No backend integration yet — `src/data/*.ts` holds temporary in-memory mocks standing in for a future API client; don't treat their current shape as settled design.

Commands (run from `frontend/`):
- Dev server: `npm run dev`
- Build (type-checks then builds): `npm run build`
- Type check only: `npm run type-check`
- Lint: `npm run lint`
- Preview production build: `npm run preview`

No test runner is configured yet.

### Structure

- `src/router/index.ts`: manual (not file-based) routes. Nesting mirrors the domain: `/w` (worlds list) → `/w/:worldId` (`World` layout) → `/w/:worldId/e/:entityId` (`EntityView`).
- `src/layouts/*.vue`: route-level shells (`Landing`, `Login`, `World`, `Worlds`).
- `src/views/`: route-level pages nested inside layouts (e.g. `views/world/EntityView.vue` renders inside `layouts/World.vue`).
- `src/components/EntityArticle.vue` / `EntityMap.vue`: render an entity's `article` or `map` facet; `EntityView.vue` picks one or the other based on which is present (map takes precedence), matching the backend's optional-facet composition.
- `src/utils/nav.ts`: builds the recursive sidebar nav tree (`NavItem`) from entity parent/child relationships, used by `NavBar`.
- Import alias `@/` maps to `src/`.

### Conventions

- ESLint config extends `eslint-config-vuetify` (`eslint.config.js`); flat config format.
- `<script lang="ts" setup>` composition API throughout; prefer the same for new components.
