# When fmx writes to your files

Most fmx commands write more than the thing you asked for. A `fmx start` refreshes nginx overlays, a `fmx create` mints secrets and picks a subnet, a `fmx services start` rebuilds vhosts. That is by design: fmx owns a set of generated artifacts and keeps them current so the operation you ran can actually succeed.

This page says which files fmx considers its own, which ones it shares with you, and when a change reaches an install that already exists. It is also the rule contributors apply when deciding where a new write belongs.

## Two mechanisms, and the line between them

fmx changes an existing host in exactly two ways.

### Reconcile on use

Re-derive an artifact fmx wholly owns, on every run, and write only when the content differs. Cheap, silent, self-healing: a file deleted by hand, lost with a recreated container or never written by an older fmx comes back on the next command.

This is correct only when all three hold:

- the artifact is fmx-generated and disposable, so regenerating it costs nothing;
- its absence or staleness breaks the very operation about to run;
- the content is derived from **runtime state**, such as the live network subnet, which database engines have sites, or which proxy ranges are trusted.

`ensure_fm_nginx_confs` is the model. It writes the bench's real-ip, upload-limit and auth overlays from the live subnet and the bench's own config, compares content before writing, touches only blocks carrying an fmx marker, reloads nginx once if anything changed, and refuses to leave a config nginx rejects.

### Migration

`fmx services migrate` for the shared services tier, `fmx migrate` for benches. Versioned, one-shot, backed up, and allowed to stop things.

This is correct when the change is tied to **fmx's version** rather than to runtime state, and especially when it rewrites a durable file you can edit: `docker-compose.yml`, `bench_config.toml`, `site_config.json`, `fm_config.toml`.

### The line

The question that separates them is not "is this a file write" but **"what decides the content?"**

If the answer is *the state of this host right now*, it belongs in a reconcile. If the answer is *which version of fmx is installed*, it belongs in a migration.

Getting that backwards produces a specific, recognisable failure: a command you ran for one reason silently edits a file you own, at a moment you did not choose, and the edit does not take effect when it is made. The file on disk and the process actually running then disagree indefinitely, with nothing said.

A deferred effect is the tell: if the code has to print "applies on the next recreate", the change wanted a migration.

Two properties decide whether a version-derived reconcile is survivable:

| | safe | not safe |
|---|---|---|
| artifact | fmx-generated, disposable, regenerated from scratch | durable state you may have edited |
| effect | immediate, or on a reload the same command performs | deferred to a later recreate or restart |

`fm_headers.conf` is rewritten whenever fmx ships different content for it, which is version-derived, and that is fine: it is a file fmx wholly owns and the worst case is one stale header until the next reload. The same treatment applied to a compose file would not be fine, because a compose file carries the host's subnets, ports and secret paths and its environment is read once, at container creation.

## What fmx owns outright

fmx regenerates these without asking. Editing them is pointless, and nothing you write there survives.

| artifact | written by | derived from |
|---|---|---|
| `services/nginx-proxy/confd/fm_headers.conf` | every command, via the services manager | fmx's own template |
| `services/nginx-proxy/confd/fm-forwarded-trust.conf` | every command | the trusted-proxy set and `[proxy]` |
| `services/nginx-proxy/confd/fm-real-ip.conf` | `fmx services trusted-proxies` | that command's arguments |
| `sites/<bench>/configs/nginx/conf/custom/*.conf` | every `fmx start` | the live frontend subnet, bench config |
| `sites/<bench>/workspace/frappe-bench/config/*.fm.supervisor.conf` | `fmx start --reconfigure-supervisor`, `fmx restart` | bench config, host CPU and RAM |
| `sites/<bench>/workspace/frappe-bench/config/fm-web-server.sh` | the same commands | gunicorn sizing, the host's trusted-proxy set |

## What fmx shares with you

These files are yours; fmx owns only part of them and finds its part by a marker it writes. Content outside the marked block is never touched.

| file | fmx's block |
|---|---|
| `services/nginx-proxy/vhostd/<domain>` | `# fm:https-redirect`, `# fm:hsts`, `# fm:maintenance`, plus the upload-limit directive |
| bench nginx `custom/` | files fmx wrote, identified by marker; anything else you drop there is left alone |
| `config/newrelic.ini` | seeded once if missing, never rewritten |

Deleting a marker strands the block permanently: fmx can no longer find what it wrote, so it will neither update nor remove it.

## What is durable state

fmx writes these too, but the write should always be either the command's stated purpose or a migration. If one of them changes during a command that did not mention it, that is a bug worth reporting.

- `fm_config.toml`, including the `[network]` subnets recorded when they are first chosen and the `[proxy]` table written by `fmx services ports`
- `services/docker-compose.yml`, including published ports, the proxy's environment and which database services are switched off
- `sites/<bench>/bench_config.toml`
- each site's `site_config.json`, with one standing exception: `max_file_size` is fmx's, reasserted from `upload_limit` on every `fmx start`. fmx says so when it overwrites a value you set. See [`upload_limit`](configuration.md#upload-limit)

## Reading the effect of a change

Where a change lands is not the same as when it takes effect.

| written to | applied by |
|---|---|
| a proxy `conf.d` or `vhost.d` file | an nginx reload, which the writing command performs |
| a bench nginx `custom/` file | bench nginx starting, so the next `fmx start` |
| a supervisor program's `command=` line, such as the gunicorn wrapper | `fmx restart BENCH`, which re-executes it from disk |
| a container's environment or published ports | recreating that container, not restarting it |
| a bind mount | recreating that container |

The last two are why `fmx services ports` recreates the proxy rather than restarting it, and why `fmx restart` is the command that applies a changed gunicorn wrapper: nothing can reach an already-running supervisor program's in-memory command line except re-executing it.

## Commands that write nothing

`fmx list`, `fmx info`, `fmx logs`, `fmx services info`, `fmx ssl list`, `fmx apps list`, `fmx domain list` and `fmx tools status` are observers. They hold no host lock, so they keep working during a migration, and they never start the global stack.

One exception is worth knowing: on a host with no services directory at all, any command including an observer will create the shared services, because there is nothing to observe until they exist.
