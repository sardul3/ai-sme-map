# Sync progress across machines (E12)

There are no accounts. Copy `data/progress.json`.

**Recommended:** Syncthing or iCloud on that one file (not the whole `data/` tree, so compile output does not fight).

1. `make backup-progress` on machine A.
2. Copy `data/progress.json` to machine B (same schema_version).
3. Do not merge two live files by hand if both changed; pick the newer `sittings` and re-tick.

`localStorage.atlas_progress` is a browser fallback when PUT is unavailable. The git file wins when the server is up.
