# Commands

Every `fmx` command has a page here: arguments, options and worked examples. `fmx <command> --help` prints the same option list in the terminal.

<div class="grid cards" markdown>

-   :material-plus-circle:{ .lg .middle } **[Create a bench](create.md)**

    ---

    ```bash
    fmx create mybench
    fmx create mybench --apps erpnext
    ```

-   :material-play-circle:{ .lg .middle } **[Start and stop](start.md)**

    ---

    ```bash
    fmx start mybench
    fmx stop mybench
    ```

-   :material-console:{ .lg .middle } **[Run commands](shell.md)**

    ---

    ```bash
    fmx shell mybench
    fmx shell mybench -c "bench --version"
    ```

-   :material-certificate:{ .lg .middle } **[Add HTTPS](ssl.md)**

    ---

    ```bash
    fmx ssl add mybench/example.com
    fmx ssl add mybench/example.com --challenge dns01
    ```

</div>

## Global options

These come before the subcommand and work everywhere.

| Option | Default | Description |
|---|---|---|
| `-v`, `--verbose` | off | Show more on screen: `-v` what fmx changed and ran, `-vv` why it chose it |
| `--log-level TEXT` | `warning` | Set the level directly instead of counting `-v`: `info` matches `-v`, `debug` matches `-vv`. Also accepts `error` |
| `--no-color` | off | Render without colour. `NO_COLOR` in the environment does the same |
| `--progress VALUE` | `auto` | How progress is drawn: `auto` animates at a terminal, `plain` prints one line per step, `none` prints nothing at all. `--non-interactive` and `--events json` both imply `plain` |
| `-n`, `--non-interactive` | off | Never prompt. A prompt that would have been shown becomes an error naming the flag that answers it |
| `--events json` | off | Stream what fmx is doing as one JSON line per event (JSONL). Implies `--non-interactive` |
| `-V`, `--version` | | Print the fmx version and exit |

## Flag conventions

Seven rules hold across every command, so a flag means the same thing everywhere.

**`--yes` / `-y` answers confirmation prompts.** It means "do the thing I typed, don't ask," and never expands what a command does. Every prompt defaults to No, so a bare Enter aborts. Under `--non-interactive`, an unanswered prompt refuses and names `--yes`.

**A decision that changes what happens gets its own named flag.** `--restore-db`, `--delete-backups`, `--skip-db-backup`, `--on-failure`: that kind of choice is never buried in a prompt alone, and `--yes` never answers it for you.

**`--force` selects a stronger action**, such as recreating containers, interrupting jobs, or renewing a certificate early. It never skips a question.

**`--dry-run` prints the plan and changes nothing.** Exit 0, never prompts. It's on every plan-first command: `create`, `delete`, `migrate`, `services migrate`, `prune`, `services prune`, `update`, `self uninstall`, `ssl ca remove`. It's the scriptable way to see a plan, because a non-interactive run without `--yes` refuses instead.

**The exit code answers "did the thing I typed happen?"** Declining a confirmation exits non-zero: the command was asked to act and did not. A non-interactive run without `--yes` gives that same answer, so a script can't tell a human saying no from a refused flag, and neither reads as success. A command that finds nothing to do, such as `fmx migrate` with no stale benches, exits 0: that one did finish.

**Exit 2 means the command line was wrong; exit 1 means fmx tried and could not.** A missing or invalid argument, an unknown flag, a bad value, a flag combination fmx refuses, or a name that doesn't exist is 2, whether Click caught it or fmx did: those are all "fix what you typed." A declined confirmation, a drain that timed out, docker being unreachable: those, and everything else fmx refuses or fails, are 1. A script can branch on 2 alone to mean "my invocation is broken," without enumerating messages. These two commands are the same mistake and answer the same way:

```bash
fmx create          # exit 2, caught by the parser
fmx info            # exit 2, caught by fmx
```

**`--events` is the stream; a command's `--json` is the result.** They answer different questions and are deliberately not the same flag. `fmx --events json` describes what fmx did, as it happens: one JSON line per event, ending in a terminal exit event, useful for a CI log or a progress UI. A command's own `--json`, such as `fmx list --json`, returns the answer: one document on clean stdout, ready for `jq`. `--events` comes before the subcommand because it changes how everything is rendered; `--json` comes after it, because it belongs to that command. Docker Compose splits the same way, with `--progress json` against `ps --format json`.

### The event vocabulary

Eleven event types, named after what fmx did rather than what it drew. The first line declares the schema version; fields may be added to the stream, but no field already emitted will be renamed or change meaning. Event types are additive too: a reader must ignore a type it doesn't recognise rather than treat the line as malformed, and a new type doesn't bump the version.

| Event | When | Carries |
|---|---|---|
| `run.started` | first line of every run | `v`, fmx version, `argv` |
| `step.started` / `step.finished` | fmx opens or closes a unit of work | `step`, and `ok` on finish |
| `command.started` | fmx runs a child process | `cmd`, `argv` |
| `command.output` | that process writes a line | `cmd`, `stream` (`out`/`err`), `text` |
| `command.finished` | that process exits | `cmd`, `exit` |
| `effect` | fmx changed something | `text`, `changed` |
| `result` | the command's own answer | `data` or `text` |
| `warning`, `error` | as they occur | `text`, or `error` and `exception` |
| `run.finished` | last line of every run | `ok`, `code` |

`effect` is the one to read if you want to know what a run did to the host: a container restarted, a certificate issued, a schema dropped. `changed` is `false` on the deliberate non-changes a program still needs: a database left in place, a backup skipped because nothing changed, a `--test-ca` rehearsal that issues a real certificate and deploys nothing. Absence can't say those things, since absence is also what a crash looks like.

Every event carries `level` (`info`, `warn` or `error`), so finding what went wrong is one field rather than three shapes read together. Text fields are plain: the terminal's styling is stripped before an event is written.

Every event also carries `run`, the same correlation id fmx stamps on each line of `~/frappe/logs/fm.log`, and every `command.*` event carries `cmd`, the same four characters that tag that command's lines in the log. A run's stream and its log file can be read against each other:

```bash
fmx --events json restart mybench.localhost > run.jsonl
jq -r 'select(.event=="command.started") | "\(.cmd)  \(.argv)"' run.jsonl
grep 'cmd=a3f1' ~/frappe/logs/fm.log     # the same command, in the log
```

A step is a unit of work opening, not a sentence fmx printed. A command that polls while it waits, `fmx update` draining its queue, re-states its progress every few seconds; that narration never reaches this stream, so a wait of any length is one `step.started` and one `step.finished`.

The stream always ends with `run.finished`. A reader who has seen it knows nothing more is coming, which is the one thing tailing a pipe can't tell you on its own.

## Bench lifecycle

| Command | What it does |
|---|---|
| [`fmx create`](create.md) | Build a new bench and start it |
| [`fmx start`](start.md) | Bring a stopped bench's containers up |
| [`fmx stop`](stop.md) | Shut a bench's containers down, keeping all data |
| [`fmx restart`](restart.md) | Restart web and workers through supervisor, whole containers, or a rolling swap that minimises downtime |
| [`fmx delete`](delete.md) | Remove a bench directory, and optionally its database |
| [`fmx reset`](reset.md) | Drop the database and reinstall every app from scratch |
| [`fmx list`](list.md) | Every bench with its status, runtime and apps |
| [`fmx info`](info.md) | One bench's URL, credentials, apps and service state |

## Working on a bench

| Command | What it does |
|---|---|
| [`fmx shell`](shell.md) | A shell, a single command, or the Frappe console inside the bench |
| [`fmx code`](code.md) | Open the bench in VS Code attached to its container |
| [`fmx logs`](logs.md) | Show or follow a bench service's log |
| [`fmx compose`](compose.md) | Raw `docker compose` against a bench, with its compose files already wired up |

## Changing a bench

| Command | What it does |
|---|---|
| [`fmx update`](update.md) | Change environment, runtime, Python or Node version, restart policy, upload limit, database and Redis endpoints. Plan-first |
| [`fmx apps`](apps.md) | Fetch an app onto a bench, install it into one site or all, and list what is installed |
| [`fmx domain`](domain.md) | Add, remove and list a bench's alias domains |
| [`fmx tools`](tools.md) | Start, stop and inspect the bench's Adminer and Mailpit containers |
| [`fmx telemetry`](telemetry.md) | Turn New Relic reporting on or off, and report whether it is reporting |
| [`fmx ngrok`](ngrok.md) | Expose a local bench to the internet through an ngrok tunnel |

## Access control

| Command | What it does |
|---|---|
| [`fmx auth`](auth.md) | Put HTTP basic auth in front of the site, the admin tools, or both |
| [`fmx maintenance`](maintenance.md) | Serve a maintenance page for a bench's domains, with allow lists and a bypass URL |
| [`fmx ssl`](ssl.md) | Issue, import, renew, list and remove certificates; manage DNS credentials and the dev CA |

## Deployment

| Command | What it does |
|---|---|
| [`fmx bake`](bake.md) | Provision a bench's apps into an immutable image, from a bench or standalone in CI |
| [`fmx switch`](switch.md) | Point a bench at an image, or roll back to the previous one |
| [`fmx prune`](prune.md) | Reclaim a bench's disk: old releases, old backup sessions, oversized logs |

The full workflow is in the [Deployment guide](../deploy/index.md).

## Host and shared services

| Command | What it does |
|---|---|
| [`fmx services`](services.md) | Manage the shared MariaDB and nginx proxy: info, migrate, start, stop, restart, shell, ports, trusted-proxies, prune |
| [`fmx migrate`](migrate.md) | Bring benches up to the installed fmx version, with backups and rollback |
| [`fmx self`](self.md) | Upgrade fmx, pull images, stop everything fmx manages, or uninstall it |
