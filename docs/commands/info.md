# `fmx info`

Show a bench's URL, credentials, apps, deploy history and live service state.

Every secret on the card is printed in cleartext: the administrator password, the site database password, and the basic auth password while a surface is protected. The shared mariadb root credentials moved to fmx services info.

**Usage**:

```console
$ fmx info BENCH [OPTIONS]
```

**Arguments**:

* `BENCH`: Bench to act on. Omit to pick from the benches you have.

**Options**:

* `--json`: Emit this command's result as JSON on clean stdout.  [default: false]
* `--fields TEXT`: Comma-separated keys to keep in the --json result, e.g. --fields name,status. Ignored without --json.

## Examples

### Show everything about a bench

```bash
fmx info mybench
```

### Read one fact out of it

fmx info mybench --json | jq -r '.result.url'

```bash
fmx info mybench --json
```
