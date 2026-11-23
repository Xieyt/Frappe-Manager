# Runtimes: mount vs image

Runtime decides where a bench's code lives, and it is locked in at `fmx create`. There is no command that moves a bench between the two afterwards.

| | `mount` (default) | `image` |
|---|---|---|
| Code lives in | an editable **workspace** on your disk, bind-mounted into the containers | an immutable **Docker image**, baked ahead of time |
| Change code by | editing files (changes are live) | building a new image and switching to it (`fmx bake` then `fmx switch`) |
| Made for | development, simple servers | production: repeatable deploys, instant rollbacks |

## Mount: the editable workspace

```bash
fmx create mybench                          # clone + install apps into a workspace
fmx create mybench --apps-from repo:tag    # or seed the workspace from a baked image (near-instant)
```

Your apps live at `~/frappe/sites/<bench>/workspace/frappe-bench/apps/`, a normal bench directory you can edit, commit from, and debug against. Everything code-related works here:

- `fmx apps add mybench app:branch`: graft apps onto the bench (`appname:ref` or `org/repo:ref`; replaced code is stashed, never deleted, then assets rebuild and the site migrates)
- `fmx update --python 3.12 --node 22`: swap toolchains (recreates the venv and reinstalls apps; `--no-recreate-python-env` keeps the existing venv)
- `fmx bake`: provision this bench's apps into an immutable image, or snapshot the workspace as it stands with `--source workspace`

## Image: the immutable release

```bash
fmx bake mybench                                             # build the image pair from a bench (prints both tags)
fmx create prodbench --runtime image --app-image repo:tag   # or create a bench directly on a pre-built image
```

In that second form, `--app-image` names the release the bench is *born* on, not a permanent pin: fmx persists only the repository half, in the bench's top-level `image` key, while the full reference lives in `[deployments].current.app_image`, rewritten by `fmx switch` on every deploy.

A bake produces two images: the app image holds the code, the venv and the built assets, and the paired `<repo>-nginx` image holds those assets again for the bench's nginx to serve. The bench itself keeps only mutable data host-side: the site directory, `common_site_config.json`, `apps.txt`, logs and config. The database is never in an image; it stays on whichever server the bench uses, `mariadb` or an external one.

There is nothing to edit on an image bench, and that is the point:

- deploys are atomic and repeatable, and rollback is one command away; see [Deployment](../deploy/index.md) and [Rolling back](../deploy/rollback.md)
- `fmx update` accepts settings only: environment, upload limit, restart policy, redis endpoints (`--redis-cache`/`--redis-queue`, and `--no-redis-cache`/`--no-redis-queue` to move a side back), external-database CA. APM is `fmx telemetry enable` now, not an update flag. `--python`, `--node` and `--developer-mode enable` are refused, since those are baked in
- alias domains (`fmx domain add`/`fmx domain remove`), admin tools (`fmx tools enable`/`fmx tools disable`) and app code (`fmx apps add`) are separate commands now; the last of those still needs an editable workspace, so it is refused on an image bench the same way

The full pipeline, baking, minimal-downtime rolling swaps, rollbacks with DB restore, release pruning, is covered in the [Deployment guide](../deploy/index.md).

## Runtime is fixed at create time

There is no command that flips a bench from one runtime to the other, in either direction:

- **Need an editable copy of what an image bench runs?** Don't touch the image bench: `fmx create NAME --apps-from REPO:TAG` creates a *new* bench and extracts the same paths out of the same image into its workspace.
- **Need an image bench?** Create one directly: `fmx create NAME --runtime image --app-image REPO:TAG`. Move it to later releases with `fmx bake` then `fmx switch`; see the [Deployment guide](../deploy/index.md).

The backing key ([`runtime`](../reference/configuration.md#runtime)) is documented in the configuration reference; it is set once, at create, and `fmx update` does not touch it.

## Three image flags, three jobs

`--app-image`, `--apps-from` and `--base-image` all name image references, which is exactly why they get mixed up. Each belongs to a different command and does a different job:

| Flag | Command | Does |
|---|---|---|
| `--app-image` | `fmx create` | Names the image the bench's containers actually run. Mount runtime: the base frappe image sitting under your editable workspace, static once set. Image runtime: the app image itself, the release the bench starts on; `fmx switch` moves it to later images from there. |
| `--apps-from` | `fmx create`, mount runtime only | Fills a fresh workspace once, at create, from the apps already built inside a baked image. `--apps`, `--python` and `--node` then override whatever that image carried. Not an image the bench runs afterwards; kept only as provenance in [`apps_from`](../reference/configuration.md#images). |
| `--base-image` | `fmx bake` | Names the image the runtime Dockerfile builds FROM. Defaults to `[build].base_image`, else fmx's published frappe image for this fmx version. |

`fmx bake` has its own `--app-image`/`--nginx-image` pair too, but there the names mean the opposite thing: the image and its nginx companion that the bake *produces*, not something it starts from. The `--base-image` it builds from is a separate flag again.

`--app-image` and `--apps-from` are not alternatives on `fmx create`, and one bench can carry both: `fmx create b --app-image ghcr.io/acme/frappe:v16 --apps-from ghcr.io/acme/app:v42` boots its containers on the v16 frappe image and fills its workspace from the v42 app image. The app image is read at every start; the apps-from image is read once, at create.

## Runtime and environment combine freely

Runtime says where code lives; [environment](environments.md) says how the web process runs. All four combinations are valid; see [How fmx works](index.md) for the matrix.

The one asymmetry: developer mode is refused on an image bench even in a `dev` environment, because DocType authoring writes app source files into the container layer that the next deploy throws away.

## Where to next

- Daily work on a mount bench → [Guides](../guides/index.md)
- Shipping an image bench → [Deployment](../deploy/index.md)
