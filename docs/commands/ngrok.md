# `fmx ngrok`

Expose a running bench on a public ngrok URL.

The tunnel rewrites the Host header on every request, so it reaches exactly one of the bench's hostnames: fmx ngrok BENCH/DOMAIN reaches that one, and a bare fmx ngrok BENCH reaches the bench's primary site. A bench serving several sites needs the domain named, because one tunnel cannot answer for all of them.

Needs an ngrok auth token: pass --auth-token, set NGROK_AUTHTOKEN, or save one in fmx's config.

**Usage**:

```console
$ fmx ngrok BENCH(/DOMAIN) [OPTIONS]
```

**Arguments**:

* `BENCH(/DOMAIN)`: Bench, or BENCH/DOMAIN to reach one hostname it serves. Without a domain part, the bench's primary site is used.

**Options**:

* `-t, --auth-token TEXT`: ngrok auth token. Falls back to the one saved in fmx's config.
* `--save-token/--no-save-token`: Save this token to fmx's config for later runs, or leave the config alone. fmx asks when a new token arrives and neither flag is passed.

## Examples

### Tunnel a running bench

```bash
fmx ngrok mybench
```

### Supply a token and remember it

```bash
fmx ngrok mybench --auth-token 2abcXYZ --save-token
```

### Tunnel one alias of a multi-domain bench

```bash
fmx ngrok mybench/shop.example.com
```

## See also

- [Domains and remote access](../guides/domains.md)
