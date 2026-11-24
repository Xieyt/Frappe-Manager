# Admin tools: Mailpit and Adminer

Mailpit catches every mail a site sends, and Adminer browses its database. Both are path-routed under the bench URL, so neither publishes a host port.

```bash
fmx tools enable mybench    # turn them on
fmx tools disable mybench   # turn them off
```

- Mailpit: `http://mybench.localhost/mailpit/`
- Adminer: `http://mybench.localhost/adminer/`

## Neither is password-protected by default

`fmx tools enable` only routes the paths; protecting them is a separate call, `fmx auth enable mybench --tools`, and `fmx tools enable` warns when you skip it. Adminer is the sharper edge of the two: it answers unauthenticated, and on a bench reachable from outside the machine that is a real database console with no lock on the door. `fmx info mybench` prints the credentials once a password exists.

Adminer opens on one-click login cards rather than a blank login form: one per site database, plus the bench's Redis cache and Redis queue. The cards are read from the mounted `sites` directory on every request, so a password change, a restore, a rotation, is picked up without regenerating anything.

!!! warning "The one-click card does not apply a pinned CA"
    A site whose external database has a CA pinned with `--db-ca` (see [External database](external-database.md#tls)) gets a card whose subtitle ends in `· TLS not applied by Adminer`. The CA lives under the bench's `config/tls/<site>/` directory, outside the one directory the Adminer container mounts, and this plugin has no `connectSsl()` override to apply it even where it could reach the file. Clicking the card still connects: without the CA, that means unencrypted and unverified against a server where TLS is optional, and refused outright against one that enforces it. fmx's own tooling is unaffected, since `bench`, dumps, restores and Frappe's own driver all run inside the bench container, where the CA is mounted.

!!! note "A `db_socket` site with no `db_host` gets no card"
    `db_socket` silently overrides `db_host` and `db_port` for Frappe, and the Adminer container can never reach a unix socket that belongs to a different container. Without `db_host` set too, the fallback the other cards use would point this one at the bench's shared `mariadb`, a different, real, writable database, and a button aimed at the wrong one is worse than no button. Set `db_host` alongside `db_socket` to name a TCP endpoint Adminer can actually dial, and the card comes back.

!!! warning "Off by default on every environment"
    `fmx create --environment dev` does not turn the tools on. Adminer is a full database console routed on the bench's own hostname, and a dev bench is not always a laptop, so turning it on automatically would publish that console to anyone who reached the host, unauthenticated, since nothing mints a password on your behalf either. `fmx tools enable BENCH` is the one way in; protecting it afterward is `fmx auth enable BENCH --tools`. `fmx update --environment` never toggles them either way.

## Serving them from some hostnames only

On a bench serving several sites, the tools answer on every hostname it has, because they are path-routed under the bench URL. Add a site part to take the route away from one site:

```bash
# /adminer/ and /mailpit/ stop answering on this site's hostnames and its aliases
fmx tools disable mybench/b.example.com

# and back
fmx tools enable mybench/b.example.com
```

Reach for this when a bench serves an internal hostname you administer from and a customer-facing domain: the tools stay reachable on the first and stop existing on the second.

The address says the scope, and the mechanism follows from it:

| Address | Acts on | Effect |
| --- | --- | --- |
| `mybench` | the bench | Starts or stops the one Adminer and Mailpit pair. Off for the bench can stop the containers because nothing is left needing them. |
| `mybench/b.example.com` | one site | Adds or removes the `/adminer/` and `/mailpit/` routes from that site's server block. The containers keep running, because the bench's other sites still reach them. |

`mybench/all` sets the route on every site the bench serves, which is how you clear several opt-outs in one call. It is not the bench form: the containers keep running, so a bench-wide `disable` and `all disable` differ in whether Adminer is up at all.

The bench form is a floor: `fmx tools enable mybench/b.example.com` is refused while the bench's tools are off, since routing a hostname at a stopped container is a 502 rather than an enable.

!!! note "Needs a bench whose nginx conf has one server block per site"
    The conf is rendered once, at the nginx container's first boot, so it reflects whatever image created the bench. On a bench whose conf predates per-site server blocks, `fmx tools enable`/`fmx tools disable BENCH/SITE` is refused rather than recorded and ignored: nginx would include none of it. Update the bench's nginx image, then `fmx restart BENCH --nginx --recreate`. The bench-wide form works on every bench.

### Why this and not a per-site password

There is exactly one Adminer and one Mailpit per bench, and every hostname routes to the same pair. A per-site password would be a bypass: an attacker who found the weaker hostname would reach the identical tool, with the identical reach into the databases. Two doors, one room.

Removing the route is a real reduction instead. A hostname with no `location ^~ /adminer/` has no way in at all, and what stays reachable is still behind the bench's one password. That is also why `fmx auth` refuses a site part for `--tools`.

## Mailpit as the site's mail server

`--mailpit-as-default-mail-server` routes outgoing mail to Mailpit by writing three keys: `mail_server`, `mail_port` and `disable_mail_smtp_authentication`. Where it writes them depends on the address:

| Address | Writes into | Scope |
| --- | --- | --- |
| `mybench` | `common_site_config.json` | Every site the bench holds, including ones created later. |
| `mybench/SITE` | that site's own `site_config.json` | That one site only; its value wins over the bench-wide fallback. |
| `mybench/all` | refused | Use the bare `BENCH` address for a bench-wide setting instead. |

```bash
fmx tools enable mybench --mailpit-as-default-mail-server
fmx tools enable mybench/site1.localhost --mailpit-as-default-mail-server
```

It is only applied on `fmx tools enable`, so pass the flag on that same call, whether or not the tools are already on. It is also only a fallback: Frappe uses it for a site with no default outgoing Email Account configured, and leaves a site that already has one alone.

`fmx tools disable mybench` takes those three keys back out, both from the common config and from every site's own `site_config.json`, but only where they still hold fmx's values: a `mail_server` you have since pointed at a real relay is left alone.

If you need the SMTP endpoint manually (inside the Docker network): host `fm__<benchname>__mailpit`, port 1025, where `<benchname>` is the full bench name with dots replaced by underscores. For example, bench `mybench` (full name `mybench.localhost`) gives host `fm__mybench_localhost__mailpit`.

!!! note
    Mailpit keeps up to 5,000 messages. Older messages are automatically deleted when the limit is reached.

## The basic auth prompt

`fmx auth` owns the prompt. A bench has two independently protectable surfaces, both enforced by the bench nginx against one credential pair:

| Surface | Covers |
| --- | --- |
| `tools` | `/adminer/` and `/mailpit/` only. Off by default; `fmx tools enable` routes them without protecting them. |
| `web` | frappe and socketio, so every other path including `/api/*`. Off by default. The ACME challenge path opts out, so certificate renewal keeps working. |

`fmx auth enable` turns a surface on, `fmx auth disable` turns it off, and `fmx auth status` reports without writing. `--web` and `--tools` select which surfaces the call acts on, and naming one says nothing about the other: `fmx auth enable mybench --web` leaves the admin tools exactly as they were. Naming neither acts on both.

```bash
# Password-protect every site of the bench, admin tools included
fmx auth enable mybench

# Protect the site only, leaving the tools as they are
fmx auth enable mybench --web

# Turn the site prompt off again; admin tools are untouched either way
fmx auth disable mybench --web

# Report the current state, writing nothing
fmx auth status mybench
```

Credentials and allow lists are kept when a surface goes off, so re-enabling asks for nothing.

### One site at a time

`fmx auth enable BENCH` sets what every site of the bench follows. On a bench serving several sites, one of them can have a prompt of its own instead:

```bash
# This site's hostnames prompt, with credentials of its own. The bench's other sites are untouched.
fmx auth enable mybench/b.example.com --web

# Whether that site has its own auth or follows the bench
fmx auth status mybench/b.example.com
```

A site with no auth of its own follows the bench's, so `fmx auth enable mybench --web` still covers every site. Giving a site its own is a clean break: it stops following the bench, including the bench's password, and `fmx auth disable mybench/b.example.com --web` turns that one site's prompt off while its neighbours keep theirs.

`--tools` takes no site part. There is one Adminer and one Mailpit per bench and both answer on every hostname it serves, so protecting them for one site would leave the same tools reachable unprotected on its neighbours, one of two doors into the same room. fmx refuses rather than applying it bench-wide behind your back.

### Credentials

One username and password serve both surfaces of the bench, and a site with its own auth has its own pair. `--user` sets the name (default `admin`), and a random password is minted the first time a surface goes on. To set your own without leaving it in the shell history, read it from stdin:

```bash
fmx auth enable mybench --user alice --password -
```

`--rotate` replaces the password with a fresh random one, which invalidates any browser session that cached the old one.

### TLS

Basic auth sends the credentials base64-encoded on every request, not encrypted. On a bench with no certificate:

- Protecting `web` is refused outright, because it would put those credentials in front of every path including `/api`. Add HTTPS with `fmx ssl add mybench/example.com`, or pass `--insecure` to accept it.
- Protecting `tools` warns and proceeds, since that is fmx's own default state. `--insecure` silences the warning.

### Exemptions

Two allow lists let specific callers skip the prompt, and they are OR'd: a request matching either one is served without a challenge.

```bash
# Addresses or CIDRs, on whichever surfaces are protected
fmx auth enable mybench --web --allow-ip 203.0.113.4 --allow-ip 10.0.0.0/8

# Absolute path prefixes, web surface only
fmx auth enable mybench --web --allow-path /api/method/payment_webhook
```

Each flag **replaces** its stored list rather than appending, and omitting the flag leaves that list alone. `--clear-exemptions` empties both, and is applied before any `--allow-ip`/`--allow-path` in the same call.

!!! note "`--allow-path` is web-surface only"
    Passing it when the resulting state does not protect `web` is an error, not a silent no-op. There is no path-level exemption for the admin tools: `/adminer/` and `/mailpit/` are all-or-nothing.

!!! warning "Allow lists behind a proxy"
    `--allow-ip` matches the address nginx sees. Behind a CDN or load balancer that is the proxy, not your client, until the front is trusted. See `fmx services trusted-proxies`.

### Two things that catch people out

- `fmx auth enable --tools` on a bench whose admin tools are **disabled** stores the intent and warns: there are no `/adminer/` and `/mailpit/` locations to gate yet. It starts applying once you run `fmx tools enable mybench`.
- `fmx tools enable` on a bench whose `[auth]` does not protect `tools` warns the mirror way: it routes Adminer and Mailpit and names the `fmx auth enable BENCH --tools` call that protects them, rather than protecting them itself.
- Protecting `web` is refused on a bench whose nginx conf predates the `Authorization`-header fix, because nginx would forward the credentials it just checked and frappe would answer 401 to every authenticated request. `fmx migrate` re-renders the conf on a mount bench; an image bench needs `fmx bake` then `fmx switch`. The `tools` surface is unaffected either way.

See also: [Environments](../concepts/environments.md) for the dev/prod defaults behind these tools, [`[auth]`](../reference/configuration.md#auth) for the config keys `fmx auth` writes, and [Architecture](../reference/architecture.md) for how the tools are routed inside the bench.
