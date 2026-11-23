# `fmx list`

List all benches with status, runtime, installed apps and deploy state.

A bench whose config will not load is reported as a warning and left out of the listing; every other bench still lists. --json includes it instead, as a row carrying the error.

**Usage**:

```console
$ fmx list [OPTIONS]
```

**Options**:

* `--json`: Emit this command's result as JSON on clean stdout.  [default: false]
* `--fields TEXT`: Comma-separated keys to keep in the --json result, e.g. --fields name,status. Ignored without --json.
* `-p, --paths`: Print plain 'name  path' lines instead of cards, so paths survive copying and piping.  [default: false]

## Examples

### List every bench

```bash
fmx list
```

### Copy or pipe bench paths

```bash
fmx list --paths
```

### Script over the inventory

fmx list --json | jq -r '.result[] | select(.status == "active") | .name'

```bash
fmx list --json
```
