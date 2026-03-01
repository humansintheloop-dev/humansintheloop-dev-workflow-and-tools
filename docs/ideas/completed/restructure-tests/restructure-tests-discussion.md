# Discussion: Restructure Unit Tests by Module

## Key Decisions

- **One test file per module class** — the organizing principle
- **Descending benefit order** — threads ordered by how much duplication/scattering each module has
- **Leftovers rule** — when a thread cleans a kitchen-sink file, rename remainder to `_leftovers.py` so later threads pull from it
- **Split `test_git_repository.py`** — core ops vs setup/infra to keep file size under ~400 lines
- **Preserve test behavior** — move verbatim, don't rewrite during the move
