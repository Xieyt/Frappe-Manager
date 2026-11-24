---
hide:
  - navigation
---

# Frappe Manager

`fmx` runs Frappe and ERPNext benches on Docker. One command builds a bench, starts its containers, and prints the URL and login. The same tool takes that bench to a server, gives it a real domain and a Let's Encrypt certificate, and ships it as an immutable image.

It replaces the stack most Frappe developers end up hand-rolling: a bench directory, MariaDB, Redis, a supervisor config, an nginx vhost, and a pile of shell aliases.

<div class="grid cards" markdown>

-   :lucide-rocket:{ .lg .middle } &nbsp; **[Up and running in minutes](getting-started/quick-start.md)**

    ---

    One command creates a Frappe bench and starts it: containers, database, workers, and web server. You bring Docker; fmx does the rest.

-   :lucide-layers:{ .lg .middle } &nbsp; **[One model, two axes](concepts/index.md)**

    ---

    Every bench is described by its runtime (editable workspace or immutable image) and environment (dev or prod). Run as many as you need, side by side.

-   :lucide-shield-check:{ .lg .middle } &nbsp; **[HTTPS in one command](guides/ssl.md)**

    ---

    Issue a Let's Encrypt certificate for any bench domain with `fmx ssl add`, over HTTP-01 or DNS-01, or import one you already have with `--custom`. Renewal is `fmx ssl renew all`, safe to run from a daily cron.

-   :lucide-code-2:{ .lg .middle } &nbsp; **[Built for developers](guides/vscode.md)**

    ---

    `fmx code mybench` opens the bench in VS Code attached to its running container; add `--debugger` for the Frappe debug launch config. On a `mount` bench your edits are live.

-   :lucide-puzzle:{ .lg .middle } &nbsp; **[Install any Frappe app](guides/app-management.md)**

    ---

    Add ERPNext, HRMS, or any custom app with `--apps`, at create time or later on a running `mount` bench. Pin each one to a branch, tag, or commit.

-   :lucide-wrench:{ .lg .middle } &nbsp; **[Admin tools, on request](guides/admin-tools.md)**

    ---

    Read outgoing mail in Mailpit and browse the database in Adminer, path-routed under the bench URL. Off by default; turn them on with `fmx tools enable BENCH`, and protect them separately with `fmx auth enable BENCH --tools`.

-   :lucide-ship:{ .lg .middle } &nbsp; **[Ship immutable deploys](deploy/index.md)**

    ---

    Bake your bench into a Docker image and deploy it with a rolling swap that minimises downtime, or a maintenance window for zero request loss. Roll back with `fmx switch --previous`, or add `--restore-db` to take the database back with the code.

</div>

## Requirements

| Requirement | Detail |
|---|---|
| Docker | Engine 20.10+ with the Compose v2 plugin, daemon running |
| Python | 3.13 or 3.14, to run the `fmx` tool itself |
| Platform | Linux, macOS, or Windows via WSL 2 |
| Disk | About 4 GB for the first bench, less for each one after |

fmx talks to the Docker daemon on every command. If Docker is not running, it exits before it does anything.

## Install

```bash
uv tool install --python 3.13 frappe-manager
```

Then check it:

```bash
fmx --version
```

Other installers and how to upgrade: [Installation](getting-started/installation.md).

## Create a bench

```bash
fmx create mybench
```

A bare name becomes a `.localhost` domain, so this bench answers on `http://mybench.localhost`. Creating a bench also starts it: fmx prints the URL and the Administrator login when it finishes. The password is a random string fmx mints for this site and writes into its `site_config.json`; read it back any time with `fmx info mybench`, or set your own up front with `--admin-pass`.

To include ERPNext, name the apps you want:

```bash
fmx create mybench --apps erpnext
```

Walk through the rest of the first session in [Your first bench](getting-started/quick-start.md).

## Where to go next

<div class="grid" markdown>

!!! info "New to Frappe Manager?"

    Start with [Installation](getting-started/installation.md), then follow [Your first bench](getting-started/quick-start.md).

!!! example "Already installed?"

    Learn the model in [How fmx works](concepts/index.md), work the daily loop in the [Guides](guides/index.md), and ship with the [Deployment guide](deploy/index.md).

</div>
