# Your first bench

This assumes fmx is installed. If not, start with [Installation](installation.md).

## Create the bench

```bash
fmx create mybench
```

The bench name is also its domain. A bare name has no dot in it, so fmx appends `.localhost` and this bench answers on `mybench.localhost`. Creating a bench also starts it; fmx prints the URL, the login credentials and the installed apps when it finishes.

!!! tip "Need ERPNext?"
    `--apps` is repeatable, and each app can be pinned to a branch, tag, or commit:

    ```bash
    fmx create mybench --apps erpnext --apps hrms
    ```

!!! note "Names with a dot in them"
    `fmx create mybench.test` is used verbatim rather than getting `.localhost` appended, and nothing resolves it for you. Add a `hosts` file entry pointing the name at `127.0.0.1`, or use a real domain with [HTTPS](../guides/ssl.md).

## Open the site

Visit `http://mybench.localhost` and log in as `Administrator`. fmx mints a random password for each site it creates and records it, so read it off the card:

```bash
fmx info mybench
```

Pick your own instead with `fmx create mybench --admin-pass 'your-password'`, or change it later with Frappe's own command inside the bench:

```bash
fmx shell mybench -c "bench set-admin-password 'a-better-password'"
```

## The commands you will use daily

```bash
fmx list             # every bench, with status, runtime and installed apps
fmx info mybench     # this bench's URL, credentials, apps and service state
fmx stop mybench     # free the resources; fmx start mybench brings it back
fmx logs mybench -f  # follow the web server log
fmx shell mybench    # a shell inside the bench container
```

## Next

Read [How fmx works](../concepts/index.md). It is five minutes and it explains the two choices, runtime and environment, that every later decision depends on.
