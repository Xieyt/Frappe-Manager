# `fmx reset`

Destroy one site: drop its database and reinstall every app, losing all site data.

The address picks the site. fmx reset BENCH resets the bench's own site; fmx reset BENCH/SITE resets exactly SITE and leaves the bench's other sites alone.

Only a site whose database is on the server fmx owns can be reset. A site with its own \[database] entry is refused, because that schema is not fmx's to drop.

**Usage**:

```console
$ fmx reset BENCH(/SITE) [OPTIONS]
```

**Arguments**:

* `BENCH(/SITE)`: Bench, or BENCH/SITE to act on one of its sites. Without a site part, the bench's primary site is used.

**Options**:

* `-y, --yes`: Reset without the confirmation. The site data is gone either way.  [default: false]
* `--admin-pass TEXT`: Administrator password for the reinstalled site. Taken from site_config.json, then common_site_config.json, or prompted for, when omitted.

## Examples

### Reset a site to a fresh install

```bash
fmx reset mybench
```

### Reset one named site of a bench that serves several

Only that site is reinstalled. The bench and its other sites keep running and keep their data.

```bash
fmx reset mybench/shop.example.com
```

### Reset and set a new administrator password

```bash
fmx reset mybench --admin-pass 'new-password'
```

### Reset unattended

Skips the confirmation. Nothing else about the reset changes.

```bash
fmx reset mybench --yes
```
