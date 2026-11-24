# `fmx self`

Manage the fmx installation itself: upgrade it, pull images, stop everything, uninstall.

**Usage**:

```console
$ fmx self COMMAND [ARGS]...
```

| Command | Description |
|---|---|
| [`fmx self upgrade`](#fmx-self-upgrade) | Upgrade fmx to the latest release published on PyPI. |
| [`fmx self update-images`](#fmx-self-update-images) | Pull the docker images fmx's stack runs on. |
| [`fmx self stop`](#fmx-self-stop) | Stop every bench on this host, then the global services (nginx-proxy, mariadb). |
| [`fmx self uninstall`](#fmx-self-uninstall) | Remove everything fmx put on this host: benches, shared services, its own files, and its dev CA. |

## `fmx self upgrade`

Upgrade fmx to the latest release published on PyPI.

An install already ahead of PyPI, such as a dev or pre-release build, is reported as up to date and left alone: fmx is never downgraded under benches whose on-disk state a newer fmx wrote.

**Usage**:

```console
$ fmx self upgrade [OPTIONS]
```

**Options**:

* `-y, --yes`: Upgrade without asking for confirmation.  [default: false]

### Examples

#### Upgrade fmx to the latest release

```bash
fmx self upgrade
```

#### Upgrade without the confirmation prompt

```bash
fmx self upgrade --yes
```

## `fmx self update-images`

Pull the docker images fmx's stack runs on.

Running containers keep the image they started with until they are recreated.

Which tags get pulled is fixed by the installed fmx version, so a newer stack starts with fmx self upgrade.

fmx republishes a release's image tags when their base picks up fixes, and a pull is skipped while the tag is already on disk, so --check is how a host learns it is behind.

**Usage**:

```console
$ fmx self update-images [OPTIONS]
```

**Options**:

* `--check`: Report which images have moved in the registry and pull nothing.  [default: false]

### Examples

#### Pull the images fmx's stack runs on

```bash
fmx self update-images
```

#### Say which images have a newer build published, without pulling any

```bash
fmx self update-images --check
```

## `fmx self stop`

Stop every bench on this host, then the global services (nginx-proxy, mariadb).

Nothing fmx manages is left running unless you narrow the blast radius with --benches-only or --global-only.

A bench that fails to stop does not abort the run: the remaining benches and the global services are still stopped, and fmx ends by naming what is still up and exiting non-zero.

**Usage**:

```console
$ fmx self stop [OPTIONS]
```

**Options**:

* `--global-only`: Stop the global services only, leaving every bench running.  [default: false]
* `--benches-only`: Stop every bench only, leaving the global services running.  [default: false]

### Examples

#### Stop everything

```bash
fmx self stop
```

#### Stop the global services, leave the benches up

```bash
fmx self stop --global-only
```

#### Stop the benches, leave the global services up

```bash
fmx self stop --benches-only
```

## `fmx self uninstall`

Remove everything fmx put on this host: benches, shared services, its own files, and its dev CA.

This destroys every bench and every database in fmx's own mariadb and postgres, with no undo and no backup taken. A schema on a database server fmx does not own is never touched, and neither is any data outside the four tiers below.

What each --only tier owns, by where the state actually lives (paths below assume fmx's default home; FRAPPE_MANAGER_HOME moves all of it, and the plan always prints resolved paths):
- benches   ~/frappe/sites/<bench>, its containers, network and volumes
- services  ~/frappe/services, the shared db/proxy containers and volumes
- host      the rest of ~/frappe, ~/.cache/fm, and every image fmx pulled or built
- trust     fmx's dev root CA, in the OS and browser trust stores

So 'host' is fmx's own files (fm_config.toml, logs, locks, backups) plus the cache directory outside ~/frappe that a hand-rolled cleanup always misses, and its images, which belong to the machine rather than to any one bench. And 'trust' is the tier that outlives 'rm -rf ~/frappe': a root CA whose private key sat in a deleted directory stays trusted by your browser forever. That tier is also why this command needs neither docker nor a config fmx can still parse.

Plan-first: every object in scope is listed with its size before anything happens, then one typed confirmation covers all of it, and --dry-run stops after the plan. Everything fmx made is included by default, its images with it; --keep-images and --keep-backups opt back out. The image set is read from fmx's own compose templates and from the containers being removed, not guessed from a name, so mariadb, redis, nginx-proxy, mailpit, adminer and postgres go too -- except any image some other container on this host still runs, which is kept and named in the plan.

fmx's own package is not uninstalled here: the command to do that is printed at the end, because a running process cannot reliably delete the environment it is executing from.

**Usage**:

```console
$ fmx self uninstall [OPTIONS]
```

**Options**:

* `--only [benches|services|host|trust]`: Act on these tiers only (repeatable): benches, services, host, trust. Default: all four.
* `--keep-images`: Leave every docker image fmx pulled or built on disk (fmx's own and the stock mariadb/postgres/redis/nginx-proxy/mailpit/adminer set).  [default: false]
* `--keep-backups`: Leave the backups directory in fmx's home (~/frappe/backups by default) on disk.  [default: false]
* `-y, --yes`: Uninstall without asking, including the typed confirmation.  [default: false]
* `--dry-run`: Print the plan and exit without removing anything; never prompts.  [default: false]

### Examples

#### See everything that would be removed, change nothing

The plan names every bench, container, network, volume, path, image and trust store, with sizes. Read it before running the real thing.

```bash
fmx self uninstall --dry-run
```

#### Remove every trace of fmx from this host

Prints the same plan, then asks for the word 'uninstall' typed back.

```bash
fmx self uninstall
```

#### Start over with a clean slate, keep the host set up

Destroys every bench and its databases; the shared services, fmx's config and its images stay, so the next 'fmx create' does not re-pull or re-provision anything.

```bash
fmx self uninstall --only benches
```

#### Remove fmx but keep the images for a reinstall

Keeps fmx's images and the stock mariadb/postgres/redis/proxy set, so reinstalling costs no pull, and the backups directory survives to be restored into the new install.

```bash
fmx self uninstall --keep-images --keep-backups
```

#### Untrust the dev CA on a host where ~/frappe was already deleted by hand

A root CA outlives the directory its key lived in: deleting ~/frappe leaves your browsers and keychain trusting a CA nobody controls any more. Needs neither docker nor a readable fmx config.

```bash
fmx self uninstall --only trust
```
