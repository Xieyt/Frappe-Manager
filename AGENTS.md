# AGENTS.md — Frappe Manager

## Project

- **What**: `fm` — CLI tool that manages Frappe benches via Docker Compose
- **Entry point**: `frappe_manager.main:cli_entrypoint` → Typer app in `frappe_manager/commands/__init__.py`
- **Install**: `fm = "frappe_manager.main:cli_entrypoint"` (pyproject.toml `[project.scripts]`)
- **Python**: strictly **3.13 only** (`>=3.13,<3.14`)

## Developer Commands

```bash
# Activate env (uses direnv + uv)
direnv allow          # first time only; then auto-activates on cd

# Run CLI during development
uv run fm --help

# Lint + format
uv run ruff check .
uv run ruff format .

# Run tests
just test             # SSL manager unit tests (default)
just test-all         # all tests
just test-file <path> # single test file
just test-debug <path># single test with verbose logs

# Generate CLI docs from live Typer app
just docs-gen         # runs scripts/update_cli_docs.py

# Docs
just docs             # serve versioned docs (mike)
just css              # compile SCSS → CSS
```

**Note**: `development.md` references `poetry` — it is **stale**. This project uses `uv` exclusively.

## Architecture

```
frappe_manager/
  main.py              # CLI entrypoint, signal handling, exception handling
  __init__.py          # Constants (CLI_DIR, paths), enums, defaults
  commands/            # Typer subcommands (create, start, stop, delete, etc.)
    __init__.py        # Main Typer app, app_callback (runs before every command)
    self/              # fm self subcommands
    services/          # fm services subcommands
    ssl/               # fm ssl subcommands
  docker/              # Docker client, ComposeFile abstraction
  site_manager/        # Bench/site lifecycle (Bench, BenchService, BenchConfig)
  services_manager/    # Global services (nginx-proxy, global-db)
  migration_manager/   # Versioned bench + infrastructure migrations
  ssl_manager/         # SSL certificate management (acme.sh, Cloudflare DNS)
  output_manager/      # Rich-based output, spinners, global singleton
  logger/              # Logging with contextual correlation IDs
  metadata_manager/    # FMConfigManager — reads/writes fm_config.toml
  templates/           # Docker compose templates, nginx configs
```

### Key patterns

- **Global output handler**: singleton via `get_global_output_handler()` / `set_global_output_handler()`. Initialized early in `main.py`, upgraded to `LoggingOutputHandler` in `app_callback`. All CLI output goes through this.
- **app_callback**: runs before every command. Handles: CLI_DIR creation, Docker daemon check, image pulling, migration checks, services initialization. Stored in `ctx.obj`.
- **Migration system**: two-tier — infrastructure (global) and per-bench. Commands skip migration check if whitelisted (`stop`, `delete`, etc.). Run `fm migrate` explicitly.
- **Home directory**: `~/frappe` by default, override with `FRAPPE_MANAGER_HOME`. Benches live in `~/frappe/sites`, services in `~/frappe/services`.

## Testing

- **Framework**: pytest with `--strict-markers`
- **Markers**: `unit`, `integration`, `slow`
- **Coverage**: default targets `frappe_manager/ssl_manager` (see pyproject.toml)
- **Global output handler**: auto-initialized for all tests via `tests/unit/conftest.py` autouse fixture. Tests should NOT patch `get_global_output_handler` directly — patch the handler instance instead.
- **Test structure**: `tests/unit/` mirrors source layout, each module may have its own `conftest.py`
- **CI**: `uv run pytest tests/ -v --cov=frappe_manager --cov-report=xml`

## Linting (Ruff)

- Line length: **120**
- Quote style: **preserve** (don't normalize quotes)
- Many rules ignored intentionally (see pyproject.toml) — don't "fix" ignored rules
- `fixable = ["ALL"]` — `ruff check --fix` is safe

## Docs

- Config: `zensical.toml` (MkDocs-based, mike for versioning)
- CLI docs are **generated** from live Typer app — run `just docs-gen`, don't edit manually
- SCSS source: `docs/stylesheets/extra.scss` → compiled to `extra.css`

## CI Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `pytest.yml` | PR/push to main, develop | Unit tests + coverage |
| `e2e-site.yaml` | manual/PR | E2E site tests |
| `e2e-migration.yml` | manual/PR | Migration tests |
| `pages.yml` | push | Deploy docs to GitHub Pages |
| `publish-pypi.yml` | release | Publish to PyPI |
| `bake-images.yml` | — | Docker image builds |
| `build-linux-binary.yml` | — | Linux binary builds |
| `update-cli-docs.yml` | — | Auto-update CLI docs |

## Gotchas

- **Poetry is dead here** — `development.md` is outdated. Use `uv sync --frozen`
- **Docker must be running** — `app_callback` checks and exits if daemon is down
- **Quote preservation** — ruff configured with `quote-style = "preserve"`, don't run formatters that normalize quotes
- **Migration-aware** — most commands check bench/infra version before proceeding. New commands should respect migration whitelists.
- **`fm shell`** allows extra args (`context_settings={"allow_extra_args": True}`) — it passes through to container shell

## Orchestration Rules

### Exploration First — No Exceptions

- Before ANY code change, invoke `@explorer` to locate relevant files
- Never assume file paths, module names, or project structure
- `@fixer` and `@designer` only receive tasks AFTER `@explorer` confirms exact paths

### Agent Routing

| Situation | Agent |
|---|---|
| Don't know where files are | `@explorer` first |
| Need current library/API docs | `@librarian` |
| Architectural decision, bug after 2+ failed attempts, code review | `@oracle` |
| UI/UX implementation or polish | `@designer` (after `@explorer`) |
| Well-scoped implementation, test changes, multi-file edits | `@fixer` (after `@explorer`) |
| Images, screenshots, PDFs to interpret | `@observer` (include full file path) |
| High-stakes decision needing multi-model consensus | `@council` |

### Parallelization

- Run `@explorer` + `@librarian` in parallel when both are needed
- Spawn multiple `@fixer` instances for independent folders simultaneously
- Never parallelize writes to the same file

### Orchestrator Must Not

- Write or suggest code directly — delegate to `@fixer` or `@designer`
- Paste full file contents into delegation prompts — use path references (`src/foo.ts:42`)
- Re-summarize `@council` output — present it verbatim
- Invoke `@oracle` on the first attempt at a problem
- Invoke `@council` for routine implementation questions

### Delegation Prompt Requirements

Every subagent call must include:
- Goal in one sentence
- Exact file paths from `@explorer` (never guessed)
- Constraints the subagent must respect
