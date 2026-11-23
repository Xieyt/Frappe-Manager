# FAQ

## Getting started

### How do I install Frappe Manager?

```bash
uv tool install --python 3.13 frappe-manager
```

`uv` owns that command, not fmx. For pipx, uvx, dev builds, and the prerequisites, see [Installation](getting-started/installation.md).

### How do I update fmx itself?

```bash
fmx self upgrade
fmx services migrate
fmx migrate all
```

The first updates the CLI. The second brings fmx's own config and the global services up to match it. The third brings your benches up to match those. `fmx migrate` refuses to run while the global services are behind, so do not skip a step. Details: [Upgrading fmx](getting-started/installation.md#upgrading-fmx).

### Can I run multiple benches on the same machine?

Yes. Each bench gets its own containers, workspace, apps and database schema. What is shared: a MariaDB server (`mariadb`) and a Postgres server (`postgres`), each running only while some bench on the host uses that engine, and one nginx proxy holding ports 80 and 443, which routes to the right bench by domain. `fmx list` shows them all.

---

## Working with benches

### How do I install ERPNext?

At create time: `fmx create mybench --apps erpnext`. On an existing `mount` bench: `fmx apps add mybench erpnext`. Refs, private repos and monorepo layouts: [App management](guides/app-management.md).

### How do I check installed apps and versions?

```bash
fmx info mybench
```

### How do I use a private GitHub repo for an app?

Pass `--github-token YOUR_TOKEN`, or export `GITHUB_TOKEN` before running the command. Either works on `fmx create` and on `fmx apps add`, and fmx never writes the token to disk: it lives in memory for that one run and is gone when it finishes, so you pass it again next time. Either way, fmx checks the repo and ref with `git ls-remote` before it starts building, so a bad token fails early. See [App management](guides/app-management.md).

### How do I change the Administrator password?

Without losing data, using Frappe's own `bench` command inside the container:

```bash
fmx shell mybench -c "bench set-admin-password 'a-better-password'"
```

`fmx reset` also takes `--admin-pass`, but it reinstalls the site from scratch and destroys everything in it.

### How do I reset a bench to a clean state?

`fmx reset mybench` drops the site's database and reinstalls every app. All site data is lost, so back up first. It only works on the database server fmx owns: a bench with its own `[database]` config entry is refused, because that schema is not fmx's to drop. See [fmx reset](commands/reset.md).

### How do I back up my bench?

Backups are Frappe's job; fmx just runs the command for you. `bench backup --with-files` is a Frappe flag, not an fmx one:

```bash
fmx shell mybench -c "bench backup --with-files"
```

Where the files land, scheduled backups, and restoring: [Backup and restore](guides/backup-restore.md).

### How do I run bench commands like migrate or build?

`fmx shell` puts you in the bench container, where the `bench` CLI lives. fmx never wraps `bench` subcommands; you call them yourself.

```bash
fmx shell mybench                      # interactive shell
fmx shell mybench -c "bench migrate"   # one command, its exit code becomes fmx's
fmx shell mybench -- bench build       # same thing, everything after -- is the command
```

`fmx shell mybench --bench-console` gets you a Frappe console with `frappe` already initialised and connected.

### How do I share my bench for testing?

Create a temporary public URL with ngrok. An auth token is required; sign up at [ngrok.com](https://ngrok.com) if you don't have one.

```bash
fmx ngrok mybench --auth-token YOUR_TOKEN --save-token
```

`--save-token` writes it to fmx's config so later runs are just `fmx ngrok mybench`. Without either `--save-token` or `--no-save-token`, fmx asks. `NGROK_AUTHTOKEN` works too.

For a stable custom domain instead of a temporary URL, see [Domains](guides/domains.md).

---

## Workers and restarts

### How do I restart just the web server or just the workers?

`fmx restart mybench --no-workers` for web only, `fmx restart mybench --no-web` for workers only, or `--service NAME` (repeatable) for one named service such as `socketio`, `nginx`, or a single worker. Inside the container, `fmx` gives finer control. See [fmx restart](commands/restart.md) and the [fmx guide](guides/fmx.md).

### How do I safely restart during a deployment without losing jobs?

`fmx restart mybench` already does this. Workers drain by default: fmx waits for in-flight RQ jobs, and if one outlasts `[workers].drain_timeout` it **aborts the restart** rather than kill the job. `--no-drain` skips the wait and interrupts running jobs (they land in the failed-jobs registry); `--force` kills everything fast. Note that `--service` skips the drain. See [fmx restart](commands/restart.md) and the [fmx guide](guides/fmx.md) for drain plus migrate and maintenance mode.

---

## Troubleshooting

### My site won't load at mybench.localhost. What should I check?

Work through these in order:

- Docker is running: `docker ps`
- The bench is listed and running: `fmx list`
- The global nginx proxy came up. It needs ports 80 and 443 on the host, so anything else already bound there will have stopped it: `fmx services start all`
- On Windows 10, `*.localhost` may not resolve; add a `hosts` entry as described in [Installation](getting-started/installation.md#windows)
- Still stuck? Read the log: `fmx logs mybench -f`, then [Reading logs](reference/logs.md)

### Docker images fail to pull. What can I try?

fmx reads the registry's own answer and names the fix in the error it prints, so start there. The causes it tells apart:

| What fmx says | What to do |
| --- | --- |
| rejected this host's stored credentials | `docker logout ghcr.io`. fmx's images are public, so no login is needed, and a stale or expired token is refused where no token at all would have worked |
| cannot run the credential helper named in `~/.docker/config.json` | install that helper, or delete the `credsStore`/`credHelpers` entry naming it. Nothing pulls at all while it is broken, public images included. A `config.json` copied from a Mac is the usual source: it names `docker-credential-desktop`, which a Linux host does not have |
| no such image is published | fmx publishes images for released versions only, so a git checkout or dev build has none. Install a released fmx, or build the images yourself with `Docker/build.sh` |
| could not reach the registry at all | DNS, the network, or an HTTP proxy. A proxy is the docker daemon's setting, not your shell's |
| is rate-limiting this host's anonymous pulls | `docker login docker.io` with any account, or wait. Six of the ten images fmx pulls come from Docker Hub |
| the TLS certificate is not trusted | an intercepting proxy. Add its CA to the docker daemon's trust store |
| the disk is full | `fmx prune`, `docker system prune` |
| refused an anonymous request | that image is private: `docker login <registry>`. fmx uses the daemon's credentials and holds none itself |

Retry with `fmx self update-images`, or by running the same command again if this was a first install. If pulls still fail, check the CLI logs for details: [Logs](reference/logs.md).

### How do I enable HTTPS for my bench?

```bash
fmx ssl add mybench/example.com
```

The default HTTP-01 challenge needs the domain's A record pointing at this server and port 80 reachable from the internet. If you cannot open port 80, use `--challenge dns01` with saved provider credentials. For a local bench that needs no public DNS at all, `--dev` issues from fmx's own CA. Already hold a certificate from your own issuer? Import it with `--custom --cert PATH --key PATH` instead of issuing one.

Behind Cloudflare's proxy (orange cloud), trust it once for the whole host with `fmx services trusted-proxies set --cdn cloudflare`, otherwise the origin's own redirect loops ([details](guides/ssl.md#behind-proxy)).

Renewal is not automatic: run `fmx ssl renew all` from a daily cron. A certificate imported with `--custom` is the one exception; fmx never rotates it, re-import a fresh one instead. [HTTPS certificates](guides/ssl.md) has step-by-step instructions for all of it.

### `fmx info` says a site is `missing` or `unmanaged`. What do they mean?

They are the two ways `bench_config.toml` and the disk can disagree, and they are opposites.

`unmanaged` is a site directory fmx has no record of, which is what `bench new-site` inside `fmx shell` leaves behind. fmx reports it and never touches it: it does not drop a schema it did not create, so `fmx delete BENCH --all-sites` will not take that database with it. Adopt it by recording it yourself, or remove the directory and its schema by hand.

`missing` is the reverse: a site recorded in `[sites]` with no `sites/<site>/site_config.json`. Frappe cannot open such a site, so it can be listed and routed while no command can act on it, and it is skipped when fmx decides which site is the bench's [primary](reference/configuration.md#primary-site). Clear the record with:

```bash
fmx delete mybench/ghost.localhost --yes
```

fmx will say it found no schema name to drop. That is the point of the message rather than an error: a schema is minted as `fm_<site>_<hex>` and the name is written only into the site config that is gone, so if a database was ever created for that site it is still on `mariadb` under a name only a listing can reveal.

### `fmx shell mybench` lands on the wrong site. Why?

A command that names a bench without naming a site acts on the bench's primary, and the first thing that decides it is Frappe's own `default_site` in `common_site_config.json`. So `bench use other.localhost`, run inside a shell at any point in the past, moves it.

`fmx info mybench` shows which site fmx resolves to, marked `● primary`. To act on a different one, address it: `fmx shell mybench/other.localhost`. The [full resolution order](reference/configuration.md#primary-site) is in the configuration reference.
