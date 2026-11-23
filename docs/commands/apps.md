# `fmx apps`

Manage the apps installed on a bench.

**Usage**:

```console
$ fmx apps COMMAND [ARGS]...
```

| Command | Description |
|---|---|
| [`fmx apps add`](#fmx-apps-add) | Fetch app code onto a bench and install it into its site(s). |
| [`fmx apps list`](#fmx-apps-list) | List the apps a bench has recorded, and what is actually on disk. |

## `fmx apps add`

Fetch app code onto a bench and install it into its site(s).

Fetching an app's code and installing it into a site's database are different things. A plain fmx apps add BENCH fetches the code and adds the app to the bench's sites/apps.txt, so any site created afterwards gets it, and installs it into nothing. It does not write an \[\[apps]] entry in bench_config.toml -- that is a bake config's job, which is why fmx apps list reports such an app as present on disk but not recorded. fmx apps add BENCH/SITE installs and migrates that one site, and fmx apps add BENCH/all does every site the bench serves, reporting failures per site and exiting non-zero without stopping at the first.

An image-runtime bench ships app changes by baking a standalone image with the apps: fmx bake --apps APP:REF --app-image REPO:TAG, then fmx switch.

**Usage**:

```console
$ fmx apps add BENCH(/SITE|all) APP:REF... [OPTIONS]
```

**Arguments**:

* `BENCH(/SITE|all)`: Bench, BENCH/SITE for one of its sites, or BENCH/all for every site it serves.
* `APP:REF...`: Apps to fetch and install (repeatable; appname:ref or org/repo:ref, or org/repo:ref#subdir for a monorepo app). Replaced code is stashed, never deleted.

**Options**:

* `--github-token TEXT`: GitHub token for a private app repository. Used for this run only; fmx does not store it.
* `--drain/--no-drain`: Suspend RQ workers and wait for in-flight jobs before migrating; --no-drain interrupts them instead.  [default: true]

### Examples

#### Fetch an app's code onto the bench

Records the app on the bench and installs it into nothing; any site created afterwards picks it up. Install it into an existing site with 'fmx apps add mybench/SITE ...' or 'fmx apps add mybench/all ...'.

```bash
fmx apps add mybench erpnext:version-15
```

#### Install into one site

Fetches the code, installs it into SITE, then runs bench migrate and restarts.

```bash
fmx apps add mybench/SITE erpnext:version-15
```

#### Install into every site the bench serves

A site that fails to install or migrate is reported and the rest still run; the command exits non-zero if any site failed.

```bash
fmx apps add mybench/all hrms:version-15
```

#### Install without draining in-flight RQ jobs

Interrupted jobs land in the failed-jobs registry (SIGUSR1, force-stop after [workers].kill_timeout).

```bash
fmx apps add mybench/all erpnext:version-15 --no-drain
```

## `fmx apps list`

List the apps a bench has recorded, and what is actually on disk.

Recorded apps come from bench_config.toml, with their pinned refs. Installed apps come from sites/apps.txt, which is bind-mounted into every bench -- mount OR image -- so this reads it the same way on both; "installed" is left out, not guessed, only when that file genuinely isn't there.

**Usage**:

```console
$ fmx apps list BENCH [OPTIONS]
```

**Arguments**:

* `BENCH`: Bench to act on. Omit to pick from the benches you have.

**Options**:

* `--json`: Emit this command's result as JSON on clean stdout.  [default: false]
* `--fields TEXT`: Comma-separated keys to keep in the --json result, e.g. --fields name,status. Ignored without --json.

### Examples

#### List a bench's apps

```bash
fmx apps list mybench
```
