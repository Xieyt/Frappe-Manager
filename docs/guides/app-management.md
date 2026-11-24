# App management

Install apps when you create a bench, or add and update them later with `fmx apps add`.

You never have to ask for Frappe itself. FM puts it at the head of the app list whether or not you name it, and pins `version-16` when you leave the ref off. Everything else you pass installs after it, in the order you gave.

## Installing

At create time:

```bash
fmx create mybench --apps erpnext
```

On an existing bench, `fmx apps add` takes one of three addresses:

```bash
# Fetch the code and record it on the bench, installed into nothing yet
fmx apps add mybench erpnext

# Fetch the code and install it into every site the bench serves
fmx apps add mybench/all erpnext

# Fetch the code and install it into one site only
fmx apps add mybench/SITE erpnext
```

FM always clones the app, installs its Python and Node dependencies, and builds its assets. A bare `BENCH` stops there: the app is recorded on the bench but installed into nothing, so a site created afterwards picks it up. Naming a site with `BENCH/SITE` or `BENCH/all` goes further: it installs the app into that site's database, runs `bench migrate`, and cycles the web and worker processes so the new code is live. `BENCH/all` reports a per-site failure and keeps going instead of stopping at the first.

!!! note "Mount benches only"
    `fmx apps add` needs an editable workspace (the default `mount` runtime). On an `image` bench, app code is baked into the image: ship changes with `fmx bake` then `fmx switch`. Runtime is fixed at create time; if you need an editable copy of what an image bench runs, create a new bench with `fmx create NAME --apps-from REPO:TAG`. See the [Deployment guide](../deploy/index.md).

## Private repos

Give fmx a token with `--github-token` (`-t` on `fmx create`), or set `GITHUB_TOKEN` in the environment. The flag exists on both `fmx create` and `fmx apps add`:

```bash
fmx create mybench --apps org/private-app:main --github-token YOUR_TOKEN
```

fmx uses the token for that one run only. It is never written to `bench_config.toml`, so a later `fmx apps add` for the same private app needs the token passed again.

For an `org/repo` spec, fmx tries authentication in order: the token first, then plain HTTPS, then SSH with whatever keys the host has. A spec given as a full HTTPS or SSH URL is cloned from that URL only, no fallback.

!!! tip "SSH instead of a token"
    Give the app as an SSH URL (`git@github.com:org/repo:main`) and fmx clones with the host's keys. Nothing to pass, nothing to type twice.

## App string formats

```
erpnext                                    -> frappe/erpnext, repo default branch
erpnext:version-16                         -> frappe/erpnext, version-16 branch
frappe/erpnext:version-16                  -> organization/repo and branch
https://github.com/org/repo:main           -> full GitHub URL
git@github.com:org/repo:main               -> SSH URL for private repos
frappe/frappe:version-16#apps/frappe       -> monorepo subdirectory (repo#path/to/subdir)
frappe/erpnext:<40-char-sha>               -> full commit SHA as the ref
```

!!! tip "Monorepo apps"
    When an app lives inside a subdirectory of a larger repo, common in company monorepos, use the `#` separator: `org/repo:branch#apps/my-app`. FM clones the repo once and picks the right subdirectory.

## Removing an app

There is no `fmx` command for this. Use the bench CLI inside the bench:

```bash
fmx shell mybench -c "bench --site mybench.localhost remove-app erpnext"
```

`fmx shell mybench` without `-c` drops you into an interactive shell with the same access. That is where anything the `fmx` commands do not cover belongs: `bench migrate`, `bench build`, `bench console`, and the rest.

!!! tip
    `fmx apps list mybench` prints what is actually installed on disk (`sites/apps.txt`). It also prints any `[[apps]]` recorded in `bench_config.toml`, normally nothing: fmx never writes that table, and it exists only in a config you wrote yourself for `fmx bake --config`. `fmx info mybench` lists the installed apps with the ref each one sits on and its commit.

## Updating or switching an app's version

`fmx apps add` also works on apps that are already installed; it grafts the requested ref onto the running bench:

```bash
# Move an installed app to another branch or tag, on every site the bench serves
fmx apps add mybench/all erpnext:version-16

# Several apps at once
fmx apps add mybench/all erpnext:version-16 hrms:version-16
```

For each app, FM replaces the code with a fresh clone at the requested ref, reinstalls dependencies, and rebuilds that app's assets, whether or not a site is named. Naming a site (`mybench/SITE` or `mybench/all`) is what installs the new code into that site: it runs `bench migrate` there and cycles web and worker. A bare `fmx apps add mybench erpnext:version-16` only grafts the code, the same as fetching a new app.

The replaced code is **stashed, never deleted**: it moves to a timestamped `.fm-apps-stash-*` directory inside the workspace, and FM prints the path, because it may hold uncommitted work. Nothing prunes it, so delete it yourself once you have looked.

!!! note "Draining, not just cycling"
    `fmx apps add` drains RQ workers by default. Before installing or migrating, it suspends them and waits, up to `[workers].drain_timeout` (300 seconds by default), for in-flight jobs to finish, then cycles the web and worker supervisor processes and resumes the workers. A drain that times out changes nothing: the workers resume and the command exits non-zero, so raise `[workers].drain_timeout` or re-run in a quieter window.

    Every command that drains follows that same rule. `fmx stop` is one of them: a timeout there leaves the bench running rather than stopping it with jobs mid-flight, and a plain container stop (bypassing fmx) kills a running job after ten seconds and leaves it recorded as started forever. `fmx restart` follows the same drain/`--no-drain` rule, and so does `fmx update` for the flags that disturb workers (`--python`, `--node`, `--recreate-python-env`, and `--restart-policy`, which recreates the worker containers outright).

    `--no-drain` skips the wait, so a job still running when the SIGUSR1 cycle lands is interrupted once `[workers].kill_timeout` (15 seconds by default) elapses.

    See the [fmx guide](fmx.md) for driving either from inside the container, and [`[workers]`](../reference/configuration.md#workers) for the timeouts.
