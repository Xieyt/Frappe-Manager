# `fmx telemetry`

Manage a bench's telemetry (APM) backends.

**Usage**:

```console
$ fmx telemetry COMMAND [ARGS]...
```

| Command | Description |
|---|---|
| [`fmx telemetry enable`](#fmx-telemetry-enable) | Turn on APM reporting for a bench. |
| [`fmx telemetry disable`](#fmx-telemetry-disable) | Turn off APM reporting for a bench. |
| [`fmx telemetry status`](#fmx-telemetry-status) | Report which APM providers are configured on a bench and whether they are reporting. |

## `fmx telemetry enable`

Turn on APM reporting for a bench.

The license key is recorded in bench_config.toml and passed to the agent through the container environment, so a key rotation is just this command again with the new key.

The agent's own config file (config/newrelic.ini) is seeded once and then yours: fmx never rewrites it, so a disable/enable cycle keeps your tuning. Use --force-config to take fmx's generated version back.

**Usage**:

```console
$ fmx telemetry enable BENCH PROVIDER [OPTIONS]
```

**Arguments**:

* `BENCH`: Bench to act on. Omit to pick from the benches you have.
* `PROVIDER`: APM backend to enable.

**Options**:

* `--license-key TEXT`: Ingest license key for the provider. Required the first time; reused from bench_config.toml afterwards.
* `--force-config`: Overwrite the provider's on-disk agent config with fmx's generated one, discarding local edits.  [default: false]

### Examples

#### Start reporting to NewRelic

Recreates the frappe container so the web process starts under the agent.

```bash
fmx telemetry enable mybench newrelic --license-key YOUR_INGEST_KEY
```

#### Re-enable after a disable, reusing the stored key

Your edits to config/newrelic.ini are kept.

```bash
fmx telemetry enable mybench newrelic
```

#### Rotate the ingest key

```bash
fmx telemetry enable mybench newrelic --license-key NEW_KEY
```

#### Throw away local agent tuning and restore fmx's generated newrelic.ini

```bash
fmx telemetry enable mybench newrelic --force-config
```

## `fmx telemetry disable`

Turn off APM reporting for a bench.

The web process is recreated without the agent, and the provider's license key is removed from the compose file. Nothing on disk is deleted: the recorded key stays in bench_config.toml and the agent's config file keeps your tuning, so re-enabling needs no arguments. Sweep an orphaned agent config with fmx prune.

**Usage**:

```console
$ fmx telemetry disable BENCH PROVIDER
```

**Arguments**:

* `BENCH`: Bench to act on. Omit to pick from the benches you have.
* `PROVIDER`: APM backend to disable.

### Examples

#### Stop reporting to NewRelic

The stored license key and your config/newrelic.ini are kept, so enabling again is one command.

```bash
fmx telemetry disable mybench newrelic
```

## `fmx telemetry status`

Report which APM providers are configured on a bench and whether they are reporting.

A provider needs both a stored license key and the enabled flag to report; either alone is shown as not reporting, because the web process falls back to plain Gunicorn.

**Usage**:

```console
$ fmx telemetry status BENCH [OPTIONS]
```

**Arguments**:

* `BENCH`: Bench to act on. Omit to pick from the benches you have.

**Options**:

* `--json`: Emit this command's result as JSON on clean stdout.  [default: false]
* `--fields TEXT`: Comma-separated keys to keep in the --json result, e.g. --fields name,status. Ignored without --json.

### Examples

#### Show APM state for a bench

```bash
fmx telemetry status mybench
```
