<div align="center">

# Frappe Manager

**Run Frappe benches on Docker: one command to create one, one to ship it.**

`fmx` gives every Frappe bench its own containers, database, workers and web server, then takes it from a local `.localhost` URL to an HTTPS production deploy without you writing a compose file.

[![PyPI](https://img.shields.io/pypi/v/frappe-manager.svg)](https://pypi.org/project/frappe-manager/) [![Python](https://img.shields.io/badge/python-3.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/) [![Tests](../../actions/workflows/pytest.yml/badge.svg)](../../actions/workflows/pytest.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**[Documentation](https://opensource.rtcamp.com/Frappe-Manager/dev/)** · [Install](https://opensource.rtcamp.com/Frappe-Manager/dev/getting-started/installation/) · [First bench](https://opensource.rtcamp.com/Frappe-Manager/dev/getting-started/quick-start/) · [Commands](https://opensource.rtcamp.com/Frappe-Manager/dev/commands/) · [FAQ](https://opensource.rtcamp.com/Frappe-Manager/dev/faq/)

</div>

![fmx create pinned.localhost --apps erpnext, then fmx info pinned.localhost](docs/assets/fm-demo.svg)

## Quick start

You need [Docker](https://docs.docker.com/get-docker/) running and Python 3.13.

```bash
# 1. install
uv tool install --python 3.13 frappe-manager

# 2. create a bench (add --apps erpnext for ERPNext)
fmx create mybench

# 3. visit it
#    http://mybench.localhost
```

`fmx create` builds the bench, starts it, and prints the URL and login. A bare name becomes a `.localhost` domain, so nothing to add to `/etc/hosts`. The Administrator password is generated per site and printed when the bench is ready; `fmx info mybench` shows it again later.

Prefer pipx, want to try it without installing, or need a dev build? See the [Installation guide](https://opensource.rtcamp.com/Frappe-Manager/dev/getting-started/installation/).

> [!IMPORTANT]
> From v0.20.0 the CLI installs under two names, `fmx` and `fm`, which run the same program. These docs write `fmx`, and that is the name to put in scripts and cron jobs. `fm` still works, including in 1.0.0, but every run prints a deprecation warning and the name will be withdrawn in a later release, because macOS 27 ships Apple's own `/usr/bin/fm`.

## What you get

| Capability | What it means |
|---|---|
| **Isolated benches** | Each bench owns its containers, apps and database, and several run side by side on one host. `fmx list` shows them all. |
| **Dev or prod, per bench** | `dev` mounts an editable workspace with admin tools on; `prod` runs lean behind the shared proxy. Switch with `fmx update -e`. |
| **Any Frappe app** | Install ERPNext, HRMS or your own repo with `--apps`, pinned to a branch, tag or commit. |
| **HTTPS in one command** | `fmx ssl add` issues a Let's Encrypt certificate over HTTP-01 or DNS-01; `fmx ssl renew all` is cron-safe. |
| **VS Code, attached** | `fmx code mybench` opens the bench inside its running container, `--debugger` adds the Frappe debug config. |
| **Immutable deploys** | `fmx bake` builds an image of the bench, `fmx switch` swaps onto it with a rolling web swap, `fmx switch --previous` rolls back. |
| **Batteries for debugging** | Adminer and Mailpit path-routed under the bench URL, behind basic auth, on by default for `dev`. |
| **Scriptable** | Every command takes `-n` for non-interactive use and `--json` for one JSON line per output event. |

## Commands

`fmx` groups its commands by what you address: a bench, one site in a bench, a domain, or the host.

```bash
fmx create mybench --apps erpnext     # create a bench and install apps
fmx start mybench                     # start, stop, restart it
fmx info mybench                      # URL, credentials, apps, deploy history
fmx shell mybench                     # a shell in the frappe container
fmx ssl add mybench/example.com       # HTTPS for a domain it serves
fmx bake mybench                      # build an image of the bench
fmx switch mybench local/mybench:TAG  # deploy onto it, rolling swap
fmx switch mybench --previous         # roll back to the last image
```

Run `fmx --help` for the grouped command list, or `fmx <command> --help` for a command's options and worked examples. The [command reference](https://opensource.rtcamp.com/Frappe-Manager/dev/commands/) documents all of them.

## Documentation

| Section | What is in it |
|---|---|
| [Getting started](https://opensource.rtcamp.com/Frappe-Manager/dev/getting-started/installation/) | Install, prerequisites, and your first bench |
| [Guides](https://opensource.rtcamp.com/Frappe-Manager/dev/guides/) | SSL, apps, domains, external databases, VS Code, hosting |
| [Command reference](https://opensource.rtcamp.com/Frappe-Manager/dev/commands/) | Every command, flag and example |
| [Configuration](https://opensource.rtcamp.com/Frappe-Manager/dev/reference/configuration/) | Every key in `fm_config.toml` and `bench_config.toml` |
| [FAQ](https://opensource.rtcamp.com/Frappe-Manager/dev/faq/) | Common failures and how to get out of them |

Docs are versioned: [`/latest/`](https://opensource.rtcamp.com/Frappe-Manager/latest/) matches the released version you get from PyPI, [`/dev/`](https://opensource.rtcamp.com/Frappe-Manager/dev/) matches `develop`.

## Contributing and support

Issues and pull requests are welcome.

- [Report a bug or request a feature](../../issues)
- [Ask a question in Discussions](../../discussions)

Working on `fmx` itself: clone the repo, `uv sync`, and run the CLI with `uv run fmx`. `just test` runs the suite and `just docs` serves the documentation locally.

## Credits and license

Built on the official [Frappe Docker](https://github.com/frappe/frappe_docker) images, and maintained by [rtCamp](https://rtcamp.com/).

MIT, see [LICENSE](LICENSE).
