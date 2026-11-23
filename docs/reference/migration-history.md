# Migration history

What each shipped migration actually did, in full. This is the archaeology page: read it when you are upgrading an install that sat out several releases, or hunting for when a particular file or key changed shape. How the migration *system* behaves lives in the [Migrations reference](migrations.md).

## The migrations, version by version {#inventory}

Three versions have shipped a migration so far. On an upgrade that spans more than one, they run in this order.

### v0.19.0

**Global services & configuration**

- `nginx-proxy` image bumped to `jwilder/nginx-proxy:1.11`

**Per bench**

- the `[ssl]` table becomes a top-level `[[ssl_certificates]]` array, and `preferred_challenge` becomes `challenge_type` (nothing reads that array where it lands; see the warning below, and v1.0.0's section for the fix)
- nginx's `SITENAME` environment variable becomes `SITE_MAPPINGS`
- `alias_domains`, `upload_limit` and `restart_policy` keys added
- runtime moves from pyenv/nvm to uv/fnm, and from certbot to acme.sh
- supervisor config regenerated

This is the slow step in any upgrade that crosses it: the per-bench half rebuilds the Python virtualenv with `uv`, reinstalls apps, and rebuilds assets.

!!! warning "v0.19.0 left TLS configuration where nothing reads it"
    v0.19.0 writes `ssl_certificates` and `dns_providers` at the **top level** of `bench_config.toml`, and no release has ever read them there: the loader only looks under `[ssl]`. A bench that stopped at v0.19.0 loads with zero certificates, and the next time fmx saves the file those orphaned keys are dropped outright, taking the TLS configuration with them. v1.0.0 relocates both into `[ssl].certificates` and `[ssl].dns_providers`, so migrate before you go hunting for a certificate `fmx ssl list` says is not there.

### v0.20.0

No structural changes. Every bench's compose images are re-tagged to the v0.20.0 frappe image, which carries Chromium's shared libraries: without them, Frappe v16's PDF generator cannot start. A bench that was already running is recreated on the new image immediately rather than just re-tagged on disk.

### v1.0.0

**Global services & configuration**

- `mariadb` moves off the end-of-life `mariadb:10.6` to `mariadb:11.8`; `MARIADB_AUTO_UPGRADE` lets the image upgrade the system tables itself
- the global `[cloudflare]` table in `fm_config.toml` becomes the credential set labelled `cloudflare` under `[ssl.dns_providers]`, so both bench and global scope store the same labelled-set shape
- `[migration_state]` is renamed `[schema]`, folding `migrated_to` and `system_migrated_to` into `version`
- the shared services are renamed to their engine names, atomically with everything that carries the old names:
    - compose service `global-db` becomes `mariadb`, `global-nginx-proxy` becomes `nginx-proxy` (containers `fm_mariadb`, `fm_nginx-proxy`)
    - the shared networks become `fm-frontend-network` / `fm-backend-network`, with their subnets carried over unchanged
    - on macOS, the data volume is copied to `fm-mariadb-data`; the old volume is kept in place as the rollback path and reported for manual removal

**Per bench**

Admin tools:

- Adminer moves from 4 to 5, with the FM login plugin
- `admin_tools_username` / `admin_tools_password` move into the `[auth]` table

Bench nginx:

- gains the real-IP overlay
- re-renders `default.conf`, so it starts logging JSON

SSL configuration, reshaped into the one form the loader reads:

- v0.19.0's top-level `ssl_certificates` array and `dns_providers` table move under `[ssl]`
- `[ssl].dns_challenge_providers` is renamed `dns_providers`
- a credential left on a certificate moves into the set labelled `cloudflare`
- the dead certificate keys (`email`, `status`, `cert_path`, `key_path`, `issued_date`, `last_renewal_attempt`, `toml_exclude`) are deleted

Sites and deploys:

- every bench gains a `[sites."<site>"]` entry; `[database."<site>"]` and a top-level `alias_domains` list move under it
- each recorded deploy's `backup` path becomes a `backups` map keyed by site
- `[switch].migrate = "auto"` becomes `true`
- `default_site` is recorded in `common_site_config.json` for a bench that has none

Schema ledger:

- `[migration_state]` is renamed `[schema]`, its `migrated_to` key becoming `version`

Service rename, applied to every bench:

- every bench is taken down for the network swap, its compose files rewritten to the renamed external networks, and `db_host: global-db` becomes `mariadb` in every site config (external database endpoints are never touched)
- benches that were running are started again

Telemetry:

- NewRelic settings move into `[telemetry.newrelic]`, from either earlier shape: the `[monitoring]` table of the unreleased 0.20/0.21 development line, or v0.19.0's flat `newrelic_enabled` / `newrelic_license_key` keys
- neither earlier shape was ever read by the current loader, so a bench upgrading from v0.19.0 silently stopped reporting to NewRelic until this step runs
- the old keys are deleted rather than left beside the new table, because fmx's config writers merge and never strip

Global proxy:

- the access-log format is brought up to the one this fmx version ships; a container reads its environment once, at creation, so a template change alone would otherwise only reach newly created hosts

## Version-specific backup artifacts {#version-backups}

Beyond the standard set every migration takes (see [Backup and restore](../guides/backup-restore.md#before-a-migration)), individual versions add their own:

| Artifact | Version | Why |
|---|---|---|
| `supervisor.conf`, `*.fm.supervisor.conf` | v0.19.0 | it regenerates them |
| nginx `default.conf` | v0.19.0, v1.0.0 | both regenerate it |
| `docker-compose.admin-tools.yml` | v1.0.0 | it rewrites it (Adminer 5) |
| all three bench compose files | v1.0.0 | the network rename rewrites them |
| `global-db-all-databases-<timestamp>.sql.gz` | v1.0.0 | whole-server dump taken while the old engine still runs, because the datadir upgrade is one-way (the dump precedes the same migration's service rename, so the file carries the old `global-db` name) |
| `fm_config.toml` | v1.0.0 | its DNS-credential relocation backs the file up before rewriting; other versions rewind only the version field in place, without a copy |

**See also:** [Migrations reference](migrations.md), [Configuration reference](configuration.md)
