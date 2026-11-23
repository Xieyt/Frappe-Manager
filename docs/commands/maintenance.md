# `fmx maintenance`

Put a bench's domains, aliases included, behind a maintenance page.

**Usage**:

```console
$ fmx maintenance COMMAND [ARGS]...
```

| Command | Description |
|---|---|
| [`fmx maintenance enable`](#fmx-maintenance-enable) | Put a bench's domains, aliases included, behind a maintenance page. |
| [`fmx maintenance disable`](#fmx-maintenance-disable) | Take the addressed domains out of maintenance and serve them again. |
| [`fmx maintenance status`](#fmx-maintenance-status) | Report maintenance state per domain, with the bypass URL. |

## `fmx maintenance enable`

Put a bench's domains, aliases included, behind a maintenance page.

fmx maintenance enable BENCH covers every hostname the bench serves. fmx maintenance enable BENCH/SITE covers that one site's own name and its aliases, leaving the bench's other sites serving: the page is written per domain in the shared proxy, so one site can be down while its neighbours are up.

Enabling prints a secret bypass URL: open it once and a cookie lets you through to the real site for a day while everyone else gets the page (visit /fm-bypass/off to drop it sooner).

Each enable rewrites the settings from the flags you pass, so repeat the ones you still want; only the bypass token carries over, unless you ask for --rotate-token.

**Usage**:

```console
$ fmx maintenance enable BENCH(/SITE) [OPTIONS]
```

**Arguments**:

* `BENCH(/SITE)`: Bench, or BENCH/SITE for one site's hostnames only.

**Options**:

* `--response-code INTEGER`: HTTP status code served while maintenance is on (400-599).  [default: 503]
* `--retry-after INTEGER`: Retry-After header in seconds; 0 omits it.  [default: 300]
* `--allow-ip TEXT`: Client IP that reaches the real site (repeatable; single addresses, no CIDR). Behind a CDN see fmx services trusted-proxies.
* `--allow-path TEXT`: Request path served the real site, e.g. /api/method/ping (repeatable). Exact match; append * for a prefix.
* `--message TEXT`: Text shown on fmx's built-in maintenance page.
* `--page PATH`: HTML file served as the page, instead of --message. A bench's configs/maintenance.html is used automatically.
* `--rotate-token`: Mint a fresh bypass token, invalidating every bypass URL and cookie already handed out.  [default: false]
* `-y, --yes`: Serve the maintenance page without asking for confirmation.  [default: false]

### Examples

#### Put a bench into maintenance

```bash
fmx maintenance enable mybench
```

#### Put one site of a multi-site bench into maintenance

```bash
fmx maintenance enable mybench/shop.example.com
```

#### Let the office and a payment webhook through

```bash
fmx maintenance enable mybench --allow-ip 203.0.113.7 --allow-path '/api/method/payment_webhook*'
```

#### Say when you will be back

```bash
fmx maintenance enable mybench --message 'Back at 17:00 UTC' --retry-after 1800
```

## `fmx maintenance disable`

Take the addressed domains out of maintenance and serve them again.

A bare bench name covers every domain it serves; BENCH/SITE covers that one site's own name and its aliases, leaving the bench's other sites as they are.

**Usage**:

```console
$ fmx maintenance disable BENCH(/SITE)
```

**Arguments**:

* `BENCH(/SITE)`: Bench, or BENCH/SITE for one site's hostnames only. A bare bench name covers every domain it serves.

### Examples

#### Bring the bench back

```bash
fmx maintenance disable mybench
```

#### Bring one site back, leaving the bench's others in maintenance

```bash
fmx maintenance disable mybench/shop.example.com
```

## `fmx maintenance status`

Report maintenance state per domain, with the bypass URL.

Writes nothing. Without a bench, lists every domain currently in maintenance across every bench.

**Usage**:

```console
$ fmx maintenance status BENCH(/SITE) [OPTIONS]
```

**Arguments**:

* `BENCH(/SITE)`: Bench, or BENCH/SITE for one site's hostnames only. Omit it to list every domain in maintenance, across every bench.

**Options**:

* `--json`: Emit this command's result as JSON on clean stdout.  [default: false]
* `--fields TEXT`: Comma-separated keys to keep in the --json result, e.g. --fields name,status. Ignored without --json.

### Examples

#### Check one bench

```bash
fmx maintenance status mybench
```

#### Check one site's hostnames only

```bash
fmx maintenance status mybench/shop.example.com
```

#### See every domain in maintenance, across every bench

```bash
fmx maintenance status
```
