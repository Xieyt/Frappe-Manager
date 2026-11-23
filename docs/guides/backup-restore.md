# Backup and restore

Three tools, three surfaces. Knowing which one you are talking to is most of this page.

| Tool | Owns | Commands |
|---|---|---|
| `bench` (inside the container) | site data: the database and the uploaded files | `bench backup`, `bench restore` |
| `fmx` (on the host) | insurance around fmx's own destructive operations | `fmx migrate` backups, `fmx services migrate` backups, `[switch] backup_db`, `fmx switch --restore-db`, `fmx prune` |
| the host filesystem | getting either of the above off the machine | `cp`, `rsync`, your backup agent |

fmx has no site-data backup command and does not wrap `bench backup`. Everything in the first row is Frappe's, reached through `fmx shell`.

## Site data: `bench backup`

`fmx shell` runs the command in the bench's `frappe` container with the working directory already at `/workspace/frappe-bench`:

```bash
# database only: faster and much smaller
fmx shell mybench -c "bench --site mybench.localhost backup"

# database plus every uploaded file
fmx shell mybench -c "bench --site mybench.localhost backup --with-files"
```

`--with-files` is a `bench` flag, not an `fmx` flag. `--site` is optional (fmx runs `bench use <benchname>` at create time, so the bench name is the default site), but naming it is what keeps the command correct on a bench that grows a second site.

### Where backups land

Frappe writes them to the site's own private directory, `sites/<sitename>/private/backups/`. In the container that is an absolute path under `/workspace`, and `/workspace` is a bind mount of the bench's `workspace` directory, so the same files are on the host:

```
container: /workspace/frappe-bench/sites/mybench.localhost/private/backups/
host:      ~/frappe/sites/mybench/workspace/frappe-bench/sites/mybench.localhost/private/backups/
```

Copying a file into that host directory makes it appear inside the container at the same path, which is how you bring a dump in from somewhere else.

Frappe names each artefact `<YYYYMMDD_HHMMSS>-<site slug>-<kind>`, where the slug is the site name with dots replaced by underscores:

| File | Contents |
|---|---|
| `20260824_143000-mybench_localhost-database.sql.gz` | gzipped SQL dump of the whole schema |
| `20260824_143000-mybench_localhost-files.tar` | public file attachments (`--with-files` only) |
| `20260824_143000-mybench_localhost-private-files.tar` | private file attachments (`--with-files` only) |
| `20260824_143000-mybench_localhost-site_config_backup.json` | copy of `site_config.json`, written every time |

!!! warning "Every `bench backup` deletes the older ones"
    Frappe clears that directory before it writes: anything older than `keep_backups_for_hours` (23 hours when the key is absent from the site config) is removed. The backups directory is a staging area, not an archive. Copy the files off the host, or set `keep_backups_for_hours` higher, if you want history.

Automating this is Frappe's job, not fmx's. Frappe schedules nothing locally on its own; a recurring backup comes from one of its off-site integrations (S3, Dropbox, Google Drive backup settings), which is also the only sane target, since the staging directory above is inside the bench you are backing up.

## Site data: `bench restore`

`bench restore` is not a merge and not reversible: it drops the site's database **and its database user**, recreates both, then imports the dump. That needs a database login that can drop and create schemas and users, so `bench` asks for the MariaDB root credentials.

Open an interactive shell, because the prompt needs a terminal that `fmx shell -c` does not give it:

```bash
fmx shell mybench
```

Then, from `/workspace/frappe-bench` where the shell starts:

```bash
bench --site mybench.localhost restore \
  sites/mybench.localhost/private/backups/20260824_143000-mybench_localhost-database.sql.gz \
  --with-public-files  sites/mybench.localhost/private/backups/20260824_143000-mybench_localhost-files.tar \
  --with-private-files sites/mybench.localhost/private/backups/20260824_143000-mybench_localhost-private-files.tar
```

`--with-public-files` and `--with-private-files` are `bench restore` flags, and both take the path to a tar file. At the `MySQL root password:` prompt, the user is `root` and the password is in `~/frappe/services/secrets/db_root_password.txt` on the host, which is where fmx keeps the `mariadb` root credential. For a scripted restore, pass `--db-root-username` and `--db-root-password` on the command line instead of waiting for the prompt.

!!! danger "An external database has no root credential to hand it"
    On a bench with a `[database]` entry the schema lives on a server fmx does not own. `bench restore` will still try to drop the schema and the login and recreate them, and fmx holds no administrative credential for that server: `--db-admin-user` is create-time only and is never written to disk. Restoring there is between you and your database provider. See [External database](external-database.md).

## fmx's own backups

These exist so fmx can undo fmx. Neither of them contains your uploaded files, so neither replaces a `bench backup`.

### Before a migration

`fmx migrate` copies each bench's configuration and dumps its database before touching anything:

```
~/frappe/sites/<benchname>/backups/migrations/<DD-Mon-YY--HH-MM-SS>/<fmx version>/
```

with `bench_config.toml`, `docker-compose.yml`, `common_site_config.json`, `site_config.json` and a gzipped `db-<benchname>-<date>.sql.gz`. The global services' `docker-compose.yml` is copied to `~/frappe/backups/migrations/<timestamp>/<fmx version>/`. Individual migration versions back up extra files they rewrite; those are listed in the [Migration history](../reference/migration-history.md#version-backups). Timestamps within one run that would collide get microseconds appended.

When a bench fails to migrate, fmx restores **the copied configuration files only**. The SQL dump is never imported automatically; it is there for you to restore by hand with `bench restore` if a migration damaged data. `--on-failure` picks the policy: `prompt` (default) asks, `archive` sets the failed benches aside and keeps the rest migrated, `rollback` reverts every bench. A single-bench run always rolls back.

The host-services tier, `fmx services migrate`, has its own `--on-failure` with a different default and a different third choice: `rollback` (the default) reverts, `halt` leaves the failed cutover exactly as it stopped and prints the backup location instead of touching anything further, `prompt` asks. There is no `archive` choice here: one run covers every shared service at once, so there is nothing partial to set aside.

**Retention is yours to trigger.** fmx never deletes a backup as a side effect of anything: after a *successful* migration it prints how many old sessions the touched locations carry beyond the configured keep (`[prune].keep_backup_sessions`, 3 by default) and stops there. Trimming is a command: [`fmx prune BENCH`](../reference/configuration.md#bench-prune) for a bench's sessions, `fmx services prune` for the host tier, both plan-first: the full plan prints, then one confirmation covers it (default: no, `--yes` skips it), and `--dry-run` stops after the plan without ever prompting. Both report exactly what left the disk. Failed or rolled-back migration runs never even hint, because those backups are the rollback.

Skipping the backup is possible and rarely wise:

```bash
fmx migrate all --skip-db-backup                 # keep the cheap config backups, skip the dumps
fmx migrate all --skip-backup                    # skip both kinds
```

!!! danger
    With no backup there is nothing to restore from, so use these only when the backup itself is what fails.

#### Restoring a migration backup by hand

Backups are grouped by the migration version that took them, so the version subdirectory is part of the path.

```bash
BENCH=mybench.localhost
BACKUP=~/frappe/sites/$BENCH/backups/migrations/12-Apr-26--14-30-45/1.0.0

fmx stop $BENCH

# config files
cp "$BACKUP/bench_config.toml" ~/frappe/sites/$BENCH/

# database: the dump has to be inside the workspace, because that is the only
# part of the bench directory mounted into the containers
cp "$BACKUP"/db-*.sql.gz ~/frappe/sites/$BENCH/workspace/frappe-bench/sites/

fmx start $BENCH
fmx shell $BENCH -c "bench --site $BENCH restore sites/db-*.sql.gz"
```

The Frappe site name is the bench name, which is why the same variable serves both.

#### When migration backups misbehave

**Backup creation fails.** Usually disk space:

```bash
df -h ~/frappe
rm -rf ~/frappe/sites/mybench.localhost/backups/migrations/<old-timestamp>/
```

If space is genuinely unavailable and you have backups elsewhere, `--skip-backup` (or `--skip-db-backup`, keeping the near-free config backups) gets the migration through.

**A bench is stuck half-migrated.** The rollback was skipped, or the process was killed mid-run. List the backup timestamps and restore the right one by hand (see above); the format sorts by day-of-month, not chronologically, so read the dates rather than piping through `sort`:

```bash
ls ~/frappe/sites/mybench.localhost/backups/migrations/
```

**"Already up to date" but the config looks wrong.** Use `fmx migrate mybench.localhost --rerun` rather than editing `[schema]` by hand: it re-applies the current release's steps against the bench as it is now.

### Before a deploy or switch

An image bench dumps its database before every deploy that can change the schema, controlled by [`[switch] backup_db`](../reference/configuration.md#deploy-tables) (`true` by default, or `"auto"` to dump only when the deploy will run `bench migrate`). One directory per release, holding an uncompressed `db-<schema>.sql` plus copies of `site_config.json` and `common_site_config.json`:

```
~/frappe/sites/<benchname>/backups/deploy-<YYYYMMDDHHMMSS>/
```

The dump is skipped, with a warning rather than a failure, if the frappe container is not running or the schema name cannot be resolved.

That dump is what `fmx switch <benchname> --previous --restore-db` imports when a migration is the thing that broke. Setting `[switch] rollback_db = true` makes fmx import it automatically when a deploy fails; it is off by default, because `bench migrate` is resumable and an import is not. `fmx prune` deletes the dumps of releases it retires.

!!! warning "An import over an external schema asks first"
    `--restore-db` imports **over** the live schema, and a Frappe dump starts by dropping every table it is about to write. When the schema is on a server fmx does not own, fmx demands a typed confirmation naming the host, the schema and its current table count, and refuses outright in non-interactive mode.

## Destroying data on purpose

```bash
fmx reset mybench    # drop the site database and reinstall every app
```

`fmx reset` runs `bench reinstall`, so all site data is gone and only the app code survives. It works only for a site on one of fmx's own database servers: a bench with a `[database]` entry naming an external host is refused, because that schema is not fmx's to drop. `fmx delete` draws the same line, and never drops an external schema whatever `--delete-fm-managed-db` says.

---

!!! info "See also"
    - [Deployment](../deploy/index.md#releases-history-and-pruning): release history, the per-release dump, and what `fmx prune` keeps
    - [Migrations reference](../reference/migrations.md): how fmx migrations work and how rollbacks are triggered
    - [fmx migrate command](../commands/migrate.md): all bench-tier migration flags
    - [fmx services migrate command](../commands/services.md#fmx-services-migrate): the host-services tier's own flags and `--on-failure` choices
