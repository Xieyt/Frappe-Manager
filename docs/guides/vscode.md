# VS Code integration

`fmx code` attaches VS Code to a bench's running frappe container, so you edit the mounted workspace with the bench's own Python interpreter and tooling.

You need VS Code with the **Dev Containers** extension, and the bench must be running (`--force-start` starts it for you). The `code` CLI is not required: without it, fmx still prepares the bench, it just cannot launch VS Code on your machine itself. See [Connecting without the `code` CLI](#connecting-without-the-code-cli) below.

```bash
fmx code mybench
```

Start the bench first if it is down:

```bash
fmx code mybench --force-start   # or -f
```

Enable debugger support:

```bash
fmx code mybench --debugger   # or -d
```

## Extensions

fmx always installs its own set: debugpy, command-variable, Python, Ruff, ESLint and Prettier. `-e/--extension` **adds** to that set, it does not replace it, and it is repeatable:

```bash
fmx code mybench -e ms-toolsai.jupyter -e vscodevim.vim
```

The list and the connecting user are stored as a `devcontainer.metadata` label on the frappe service. Changing either rewrites the label and brings the service back up so VS Code picks it up; running `fmx code` again with the same values touches nothing.

## Connecting without the `code` CLI

Preparing the bench, writing the devcontainer metadata and, with `--debugger`, the launch configs, always happens and does not need the `code` CLI at all. Attaching VS Code is the one step that does: it launches VS Code on your machine and needs `code` on `PATH` to do it.

Without `code` on `PATH`, fmx prepares the bench and prints how to finish the connection instead of attaching: open VS Code on another machine, Remote-SSH to this host, then run "Dev Containers: Attach to Running Container" and pick the bench's frappe container. This is the normal way to reach a bench on a server, where nobody runs VS Code on the host itself.

`--attach/--no-attach` controls this explicitly:

| Option | What it does |
| --- | --- |
| `--attach` (default) | Launch VS Code on this machine once the bench is prepared, if the `code` CLI is on `PATH`. Falls back to the connect-from-another-machine instructions if it is not. |
| `--no-attach` | Prepare the bench and stop there, even if `code` is available. What a server wants: connect later with Remote-SSH. |

## Other options

| Option | What it does |
| --- | --- |
| `--user` | User VS Code connects as inside the container. Defaults to `frappe`. |
| `--work-dir` / `-w` | Directory VS Code opens. Defaults to `/workspace/frappe-bench`. |

!!! warning "Image-mode benches"
    An `image` bench has no live-mounted workspace, so edits made through `fmx code` live only in that container and are lost on the next `fmx switch`. `fmx code` warns when you do it. Use it to reproduce and observe; ship real changes through the [deployment pipeline](../deploy/index.md).

## How the debugger works

`--debugger` needs a workspace `--work-dir`; point it elsewhere and fmx warns and skips the setup. When it does run, it writes `launch.json`, `tasks.json` and `settings.json` into `<work-dir>/.vscode` (backing up any existing file to a timestamped copy first) and installs `ruff` into the bench virtualenv.

`launch.json` carries three configurations:

- **fm-frappe-debug**: `bench serve` on port 80 under debugpy, with `DEV_SERVER=1` and `justMyCode` off, so you can step into framework code.
- **Debug Specific Queue**: a `frappe worker` for a queue you are prompted for.
- **Debug specific fuction**: `frappe execute` on a path you are prompted for.

The first one is the interesting case. It binds port 80, the same port the supervised web server already holds, so it declares a `preLaunchTask` called `fm-kill-port` that VS Code runs first:

```bash
fmx stop frappe && sleep 2
```

When you end the debug session the supervised web server stays stopped. Bring it back with:

```bash
fmx shell mybench -c "fmx start frappe"
```

`fmx` talks to supervisord inside the container over a Unix socket, so this cycles one process rather than the whole bench. See the [fmx guide](fmx.md) for the rest of what it can do.
