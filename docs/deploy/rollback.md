# Rollback

The deploy went bad. Here's the way back:

```bash
fmx switch mybench --previous                 # code rollback; migrate disabled automatically
fmx switch mybench --previous --restore-db    # code AND database back together
```

Need to go further back than one release?

```bash
fmx switch mybench local/mybench:<older-tag> --no-migrate   # further than one release
```

`fmx info` lists the images this bench has run. An older image only works if it's still on the daemon: `fmx prune` protects the current and previous images, the seed and base images, and whatever the kept history rows reference, and removes the rest.

Rollbacks run the same [switch pipeline](index.md#the-switch-pipeline) as forward deploys, pointed backwards. The same snapshots, health gate, and abort safety apply.

## What the flags do

- **`--previous`** disables migrate for the run: old code must never migrate a newer schema. Override with an explicit `--migrate`. It's exclusive with an explicit IMAGE: pass one or the other.
- **`--restore-db`** restores the DB dump recorded on the **current** (bad) deploy's own record, and imports it before the swap. A restore is schema-grade, so it runs under the maintenance window like a migrate does. Rows written after the bad deploy went live are discarded, which is why it's never implicit. It fails up front, before anything is touched, when the current deploy has no recorded dump. Dumps live under `<bench>/backups/deploy-*/`.
- After a rollback, `[deployments].previous.app_image` points at the image you just left. Running `fmx switch --previous` again re-deploys it: rollback of a rollback is a redo, deliberately.

## What to check after

```bash
fmx info mybench
```

- The **deploys** section should show the release you rolled back to as current, with the history intact.
- Hit the site and confirm it serves normally.
