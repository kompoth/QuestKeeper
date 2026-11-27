# Roadmap (questkeeper)

Value/Effort are rough High/Med/Low estimates to guide bucketing, not fixed commitments. Re-bucket on review as estimates shift.

| Item | Stage | Value | Effort | Notes |
|---|---|---|---|---|
| Sidebar tree reordering | 🚀 Now | 🟢 High | 🟢 Low | Simple frontend sorting: alphabetically, created, or updated. |
| Entity reparenting (move entity+subtree to new parent) | ⏭️ Next | 🟢 High | 🟡 Med | On backend just overwrite parent_id; on frontend show search/dropdown with existing entities as candidates. |
| App-wide typography setup | ⏭️ Next | 🟢 High | 🟡 Med | Vuetify currently default Roboto, no font/scale decided. |
| Frontend registration UI | 🕒 Later | 🔴 Low (no external users expected yet) | 🟢 Low | Backend exists since phase 5, only frontend view/route missing. Also fix: `registration_enabled` no-row-yet default must be `False`. |
| Map view zoom/pan perf with large (15MB+) images | 🕒 Later | 🟡 Med | 🔴 High | RESEARCH done. No resolution cap on upload. Recommended fix: rAF-throttle handlers + client-side downscale-on-upload (~4096px cap). Tiling (OpenSeadragon/Leaflet) reserved for later. |
| Per-world media storage usage shown to owner | 🕒 Later | 🔴 Low | 🟡 Med | Sum S3 object sizes under `worlds/{world_id}/`. |
| Real landing page | 🕒 Later | 🔴 Low | 🔴 High | `Landing.vue` is a placeholder stub; design direction undecided. Low value + high effort — candidate to cut rather than keep deferring. |
| Paginated admin "Worlds" view with used-storage column | 🕒 Later | 🔴 Low | 🟡 Med | Needs storage-usage calc above, new `GET /admin/worlds`. |
| Clean up scattered `# noqa: PLR0913, PLR0917` | 🕒 Later | 🔴 Low | 🟡 Med | Find structural fix (context object / raise ruff max-args) instead of per-function suppression. |
