#!/usr/bin/env python3
"""Docs checks that mkdocs does not do: dash style, link hygiene, and flags/commands/config
keys that do not exist, in the docs and in the messages fmx prints.

Run via `just docs-lint`. CI runs it on every PR.

Why each check exists, so nobody has to guess before deleting one:

- **Dashes.** House style is no em/en dashes and no ` -- ` connector in prose. Typer help
  text is rendered verbatim, so a dash that lands in a docstring ships to the terminal.
- **Links.** mkdocs happily builds a site full of links to files that do not exist. Every
  removed command leaves a trail of them: deleting `fm deploy` left `docs/commands/index.md`
  pointing at a `deploy.md` that was no longer generated.
- **Flags.** Renaming a flag does not rename it in prose. The real flag set is read from the
  live CLI, not a checked-in list, so this cannot drift: rename a flag and the stale mention
  fails here. Checked in docs AND in fmx's own messages, because a rename rots fastest where
  nothing looks: six stale mentions shipped past a green suite at once, including the refusal
  `fm bake` printed telling the operator to run a flag that had just been renamed. Tests pin
  what a message says, never whether what it says still exists.
- **Doc commands and their flags.** The flat checks above answer "does this flag exist
  ANYWHERE in fmx", not "does the command written next to it own it", and they never ask
  whether the command itself is real. A five-way audit found a renamed subcommand and a flag
  documented on the wrong page in the same pass that the flat checks above passed clean.
  `check_doc_commands` walks `fm_command_spec` per invocation instead, the same machinery
  `check_message_commands` uses on fm's own source, so a chain and its flags are judged
  together, not against the flat union of everything fm accepts anywhere.
- **Config keys, both directions.** Every field a `BenchConfig`/`FMConfigManager` model
  actually writes to disk should have a documented key in configuration.md, and every key
  that page documents should come from a real field. Neither direction is implied by the
  flag checks, which only look at `--cli-flags`, not TOML keys: `tools_user`, `tools_password`,
  `backend_subnet_cidr` and `startup_timeout` all went missing from the page at once with
  nothing here to notice until this check existed.

Generated pages (`docs/commands/`) are exempt from *style* checks, because their content comes
from help text that this script cannot fix, but their *links* and the commands/flags they name
are checked: that is where a removed command or a renamed flag shows up first.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Another tool's flags, named in a message that also names an fm command. The flag is real, it
# just is not ours: fm explains what IT will run on your behalf.
SOURCE_FOREIGN = {
    "--no-setup-db",  # bench new-site, in the external-database flow explanations
}

FMX_SRC = ROOT / "Docker" / "frappe" / "fmx"

# Flags owned by other tools, legitimately named as theirs in our docs.
FOREIGN = {
    # generic, or ours-by-coincidence across many tools
    "--help",
    "--version",
    "--verbose",
    "--debug",
    "--quiet",
    "--force",
    "--yes",
    "--list",
    "--info",
    "--file",
    "--user",
    "--site",
    "--port",
    "--queue",
    "--tail",
    "--from",
    "--reinstall",
    "--upgrade",
    "--log-level",
    "--non-interactive",
    "--challenge-alias",  # acme.sh
    "--db-root-username",
    "--db-root-password",
    "--with-files",  # bench
    "--with-private-files",
    "--with-public-files",
    "--sync-config",  # bench
    "--depth",  # git
    "--fetch-python",  # uv
    "--preload",
    "--threads",
    "--worker-class",
    "--max-requests",  # gunicorn
    "--graceful-timeout",
    "--max-requests-jitter",
    "--host",  # gunicorn
    "--skip-character-set-client-handshake",  # mariadb
    "--load",
    "--platform",
    "--push",
    "--target",
    "--build-arg",
    "--label",  # docker/buildx
    "--db-instance-identifier",
    "--db-snapshot-identifier",  # aws rds
}

DASHES = {"\u2014": "em dash", "\u2013": "en dash", "\u2015": "horizontal bar", "\u2012": "figure dash"}


# Anything under these is somebody else's markdown: a virtualenv, an installed package, a
# node_modules tree. `just test-fmx` builds Docker/frappe/fmx/.venv, which put a vendored
# typer SKILL.md inside the Docker/ glob and failed this check on a flag typer documents
# about itself.
VENDORED = {".venv", "venv", "site-packages", "node_modules", ".git", "dist", "build", "__pycache__"}


def _ours(path: Path) -> bool:
    return not VENDORED.intersection(path.parts)


def hand_written() -> list[Path]:
    """Docs we author. Generated command pages and the changelog are excluded from style checks."""
    md = sorted(p for p in Path("docs").rglob("*.md") if _ours(p))
    md = [p for p in md if p.parts[:2] != ("docs", "commands") and p != Path("docs/changelog.md")]
    return md + sorted(p for p in Path("Docker").rglob("*.md") if _ours(p))


def fm_flags() -> set[str]:
    """Every option name the real CLI accepts, read from the live Typer/Click app."""
    import typer.core
    import typer.main

    from frappe_manager.commands import app

    def walk(cmd):
        yield cmd
        if isinstance(cmd, typer.core.TyperGroup):
            for sub in cmd.commands.values():
                yield from walk(sub)

    flags: set[str] = set()
    for cmd in walk(typer.main.get_command(app)):
        for param in cmd.params:
            flags |= set(param.opts) | set(param.secondary_opts)
    return flags


def fmx_flags() -> set[str]:
    """fmx's options, parsed from source: it imports supervisor, so it cannot load on a host.

    Every string literal that looks like an option declaration counts, including the
    ``"--drain/--no-drain"`` pairs typer uses for negatable flags, and short forms like
    ``"-p"``: a renamed host CLI now shares fmx's own name, so a doc line that quotes a
    container command through it (``fmx start short-worker -p short-worker_1``) needs
    fmx's short flags recognised too, not just its long ones.

    Vendored trees are excluded, and that matters more here than for the docs glob: every
    flag found becomes an ALLOWED name, so sweeping in a venv's site-packages inflates the
    allowlist (176 real flags became 638) and lets a doc typo pass by matching some flag in
    an unrelated dependency.
    """
    flags: set[str] = set()
    for py in FMX_SRC.rglob("*.py"):
        if not _ours(py):
            continue
        try:
            tree = ast.parse(py.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for part in node.value.split("/"):
                    if re.fullmatch(r"-{1,2}[a-z][a-z0-9-]*", part):
                        flags.add(part)
    return flags


def anchors_of(text: str) -> set[str]:
    """Heading anchors mkdocs will emit: explicit ``{#id}`` plus the auto-slug."""
    found: set[str] = set()
    for m in re.finditer(r"^#{1,6}\s+(.*)$", text, re.M):
        heading = m.group(1)
        explicit = re.search(r"\{#([\w-]+)\}", heading)
        if explicit:
            found.add(explicit.group(1))
        bare = re.sub(r"\{#[\w-]+\}", "", heading)
        found.add(re.sub(r"[^\w\s-]", "", bare).strip().lower().replace(" ", "-"))
    return found


def check_dashes(files: list[Path]) -> list[str]:
    """A spaced ` -- ` connector in prose, outside a fenced block, outside a backtick span.

    Used to exempt the WHOLE LINE whenever any ``--flag``-looking token appeared anywhere on
    it, so a sentence naming a flag could carry a prose ` -- ` connector elsewhere on the same
    line and never be seen: six shipped that way in docs/commands/index.md and
    docs/deploy/index.md before this was narrowed. A flag has no space after its dashes, so a
    spaced ` -- ` is never one; the only legitimate reason to see one is a quoted flag/command
    example inside backticks on that line, which is what the exemption is narrowed to now.
    """
    hits = []
    for f in files:
        fenced = False
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue  # style is about prose; `--` in a shell example is an argument separator
            for ch, name in DASHES.items():
                if ch in line:
                    hits.append(f"{f}:{i} {name}: {line.strip()[:70]}")
            backticked = [m.span() for m in re.finditer(r"`[^`]*`", line)]
            for m in re.finditer(r"\S -- \S", line):
                if not any(start <= m.start() < end for start, end in backticked):
                    hits.append(f"{f}:{i} prose --: {line.strip()[:70]}")
    return hits


def all_docs() -> list[Path]:
    """Every markdown page docs/**/*.md we ship, generated pages included: a stale command or
    flag name shows up in a generated page (its text mirrors live `--help`) exactly as readily
    as in a hand-written one, so the command/flag/link checks all read this same set.
    """
    return sorted(p for p in Path("docs").rglob("*.md") if _ours(p))


def check_links() -> tuple[list[str], list[str]]:
    """Absolute links, and links whose target file or anchor does not exist."""
    all_md = all_docs()
    anchors = {f: anchors_of(f.read_text()) for f in all_md}

    absolute: list[str] = []
    broken: list[str] = []
    for f in all_md:
        for m in re.finditer(r"\[[^\]]*\]\(([^)\s]+)", f.read_text()):
            target = m.group(1)
            if target.startswith("/"):
                absolute.append(f"{f}: {target}")
                continue
            if target.startswith(("http", "mailto:")):
                continue
            rel, _, frag = target.partition("#")
            if not rel:
                if frag and frag not in anchors[f]:
                    broken.append(f"{f}: #{frag} (missing anchor, same page)")
                continue
            # A directory link resolves to its index page, which is what mkdocs serves.
            raw = rel + "index.md" if rel.endswith("/") else rel
            resolved = Path(os.path.normpath(f.parent / raw))
            if not resolved.exists():
                broken.append(f"{f}: {target} (missing file)")
            elif frag and resolved.suffix == ".md" and frag not in anchors.get(resolved, set()):
                broken.append(f"{f}: {target} (missing anchor)")
    return absolute, broken


def check_flags(files: list[Path], real: set[str]) -> dict[str, set[str]]:
    unknown: dict[str, set[str]] = {}
    for f in files:
        for m in re.finditer(r"(?<![\w-])(--[a-z][a-z0-9-]{2,})", f.read_text()):
            flag = m.group(1)
            if flag not in real:
                unknown.setdefault(flag, set()).add(str(f))
    return unknown


def source_strings() -> list[tuple[Path, str]]:
    """Every string literal in fm's own source that can REACH AN OPERATOR, with its file.

    Parsed rather than grepped so only real literals count, and docstrings are dropped: they
    explain the code to whoever reads it next, including by naming flags that have since been
    retired ("this owns what `fm update --newrelic` used to"). That is history stated on purpose,
    not an instruction anyone can follow, and failing on it would train people to delete the
    explanation instead of fixing the message.
    """
    out: list[tuple[Path, str]] = []
    for path in sorted(Path("frappe_manager").rglob("*.py")):
        if not _ours(path):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:
            continue
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                out.append((path, node.value))
    return out


def check_source_flags(real: set[str]) -> dict[str, set[str]]:
    """Flags named in fm's own operator-facing instructions that the CLI does not have.

    Docs were checked against the live flag set from the start; MESSAGES were not, and that is
    exactly where a rename rots unseen. A green suite shipped six of them at once, including the
    refusal `fm bake` prints for an image bench, which told the operator to run `--image` after
    that flag had become `--app-image`. Tests pin what a message SAYS, never whether what it says
    still exists.

    Scoped to strings that tell someone to run an fm command, because fm's source is full of
    legitimate third-party flags it passes to docker, git, bench, acme.sh and uv. Widening this to
    every literal reports 58 findings of which ~56 are `docker --filter` and friends, and a check
    that must be skimmed is a check that gets ignored. A flag is only a lie when it sits next to
    the `fm` command that supposedly accepts it.
    """
    unknown: dict[str, set[str]] = {}
    for path, text in source_strings():
        if not re.search(r"(?<![\w-])fm [a-z]", text):
            continue
        for m in re.finditer(r"(?<![\w-])(--[a-z][a-z0-9-]{2,})", text):
            flag = m.group(1)
            if flag not in real:
                unknown.setdefault(flag, set()).add(str(path))
    return unknown


def fm_command_spec() -> dict[tuple[str, ...], dict]:
    """Per-command shape from the live app: its flags, which take a value, and how many
    positionals it accepts.

    The flat flag set above answers "does this flag exist ANYWHERE in fm", which is not the
    question a recovery message raises. `fm ssl add <bench> <domain>` names a real command and
    no flags at all, and Click still refuses it: that command takes ONE combined argument.
    """
    import typer.core
    import typer.main

    from frappe_manager.commands import app

    spec: dict[tuple[str, ...], dict] = {}

    def walk(cmd, path: tuple[str, ...]) -> None:
        flags: dict[str, bool] = {}
        max_pos = 0
        for param in cmd.params:
            if getattr(param, "param_type_name", "") == "option":
                takes_value = not param.is_flag and param.nargs != 0
                for name in list(param.opts) + list(param.secondary_opts):
                    flags[name] = takes_value
            elif getattr(param, "param_type_name", "") == "argument":
                max_pos = 99 if param.nargs == -1 else max_pos + param.nargs
        spec[path] = {
            "flags": flags,
            "max_pos": max_pos,
            # `fm shell` and `fm compose` hand argv to another program; their positionals and
            # unknown flags belong to whatever runs inside.
            "allow_extra": bool(cmd.context_settings.get("allow_extra_args")),
            "group": isinstance(cmd, typer.core.TyperGroup),
        }
        if isinstance(cmd, typer.core.TyperGroup):
            for name, sub in cmd.commands.items():
                walk(sub, (*path, name))

    walk(typer.main.get_command(app), ())
    return spec


# A token that follows a command without being a subcommand: a placeholder to substitute, or a
# concrete example value.
_PLACEHOLDER = re.compile(r"^(<[^>]+>|\{[^}]+\}|[A-Z][A-Z0-9_/:-]*|[a-z0-9][\w.-]*\.(localhost|com|dev|test))$")


def check_message_commands(
    spec: dict[tuple[str, ...], dict], container_flags: frozenset[str] = frozenset()
) -> list[str]:
    """`fmx ...` invocations in fmx's own messages that the CLI would refuse.

    Catches a flag named on a command that does not own it, and the wrong number of
    positionals -- the acme.sh helper told operators to run `fm ssl add <benchname> <domain>`
    and Click answered "Got unexpected extra argument".

    It CANNOT catch a command that is legal by signature and refused by its own body: `fm bake
    BENCH --apps APP:REF` declares both and rejects the pair at runtime. No declaration-based
    checker can see that, so it stays a human rule. Do not widen this docstring without
    widening the check.

    `container_flags` is the OTHER fmx's flag set (see `fmx_flags`): the in-container service
    manager, not this host CLI. The rename gave the host the exact name that tool already used
    for its own `restart`/`start`/`stop`, so a message telling someone to run it from a shell
    (`fmx restart --migrate`) now parses as a host invocation too and needs its flags allowed
    the same way a third-party tool's are in `FOREIGN`.
    """
    problems: list[str] = []
    for path, text in source_strings():
        for match in re.finditer(r"(?<![\w-])fmx ((?:[a-z][a-z0-9-]*)(?: [^\s'\"`,;]+)*)", text):
            tokens = match.group(1).split()
            chain: tuple[str, ...] = ()
            index = 0
            while index < len(tokens) and (*chain, tokens[index]) in spec:
                chain = (*chain, tokens[index])
                index += 1
            if not chain or spec[chain]["group"] or spec[chain]["allow_extra"]:
                continue
            shape = spec[chain]
            command = "fmx " + " ".join(chain)
            positionals = 0
            expect_value = False
            for token in tokens[index:]:
                # Messages write flags as prose: a rich tag can be glued on (`--dev[/fm.muted]`),
                # a negatable pair is written `--push/--no-push`, and a trailing bracket belongs
                # to the sentence. Judge the flag, not the punctuation around it.
                token = re.sub(r"\[/?[\w.]+\]", "", token).strip("().,;:'\"`")
                if not token:
                    continue
                if expect_value:
                    expect_value = False
                elif token.startswith("-"):
                    names = token.split("=", 1)[0].split("/")
                    if any(name in FOREIGN or name in container_flags for name in names):
                        continue
                    missing = [name for name in names if name not in shape["flags"]]
                    if missing:
                        problems.append(f"{path}: '{command}' does not accept {', '.join(missing)}")
                        continue
                    expect_value = shape["flags"][names[0]] and "=" not in token
                elif _PLACEHOLDER.match(token):
                    positionals += 1
                else:
                    break
            if positionals > shape["max_pos"]:
                problems.append(
                    f"{path}: '{command}' takes {shape['max_pos']} argument(s), the message passes {positionals}"
                )
    return problems


def check_stale_fm_messages(spec: dict[tuple[str, ...], dict]) -> list[str]:
    """fmx's own messages that still spell out the retired `fm` name for an invocation.

    `fm` still runs (it prints a one-line deprecation warning, see `main.py`) but is going
    away in 1.0.0; a message built with `fm <command>` is telling the operator to type the
    name that stops working. Chain-walked against the live spec exactly like
    `check_message_commands`, so an ordinary sentence ("fm will...", "fm also...") never
    counts, only `fm` followed by a real command does -- the same signal that keeps
    `fm_config.toml`, `fm.log` and the `# fm:` nginx markers out of this, none of them have a
    space after `fm`.
    """
    problems: list[str] = []
    for path, text in source_strings():
        for match in re.finditer(r"(?<![\w-])fm ((?:[a-z][a-z0-9-]*)(?: [^\s'\"`,;]+)*)", text):
            tokens = match.group(1).split()
            chain: tuple[str, ...] = ()
            index = 0
            while index < len(tokens) and (*chain, tokens[index]) in spec:
                chain = (*chain, tokens[index])
                index += 1
            if not chain:
                continue
            command = " ".join(chain)
            problems.append(f"{path}: tells the operator to run 'fm {command}', the retired name; say 'fmx {command}'")
    return problems


def check_doc_commands(
    files: list[Path], spec: dict[tuple[str, ...], dict], container_flags: frozenset[str] = frozenset()
) -> list[str]:
    """`fmx ...` invocations written in the docs, prose or fenced, that the live CLI would
    refuse: an unknown subcommand under a real group, a flag the named command does not own,
    or too many positionals.

    Reuses `fm_command_spec` and the chain-walk from `check_message_commands` rather than a
    second parser. A command whose first word is not real is left alone, same as there: this
    file says "fmx will", "fmx also", "fmx itself" constantly, and treating every one as an
    unknown command would drown the real findings in noise. A dangling, unresolved subcommand
    under a group that DOES exist -- the shape `fm services real-ip` took after the rename to
    `trusted-proxies` -- is only flagged when it is quoted (backticked, or inside a fenced
    block): that is how every genuine command reference in these docs is written, and it is
    the one signal that tells a stale subcommand name apart from an ordinary sentence.

    The flag check is command-specific, unlike `check_flags` above: a flag belongs to the
    chain it is written next to, or to the root callback, or to the `FOREIGN` allowlist, never
    to "some command somewhere". That is what catches a flag copied onto the wrong page.

    `container_flags` carries the OTHER fmx's own flags in the same way: the host CLI shares
    its new name with the in-container service manager, so a doc line showing what to run
    inside a shell (`fmx start short-worker -p short-worker_1`) parses as a host `fmx start`
    invocation and would otherwise be told it does not own `-p`.
    """
    problems: list[str] = []
    root_flags = spec[()]["flags"]
    for f in files:
        fenced = False
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            backticks = [m.span() for m in re.finditer(r"`[^`]*`", line)]
            quoted = lambda pos: fenced or any(start <= pos < end for start, end in backticks)  # noqa: E731

            for match in re.finditer(r"(?<![\w-])fmx ((?:[a-z][a-z0-9-]*)(?: [^\s'\"`,;]+)*)", line):
                tokens = match.group(1).split()
                chain: tuple[str, ...] = ()
                index = 0
                while index < len(tokens) and (*chain, tokens[index]) in spec:
                    chain = (*chain, tokens[index])
                    index += 1
                if not chain:
                    continue
                shape = spec[chain]
                command = "fmx " + " ".join(chain)
                quoted_invocation = quoted(match.start(1))
                if shape["group"]:
                    if shape["allow_extra"]:
                        continue
                    leftover = tokens[index] if index < len(tokens) else None
                    if leftover and re.match(r"^[a-z][a-z0-9-]*$", leftover) and quoted_invocation:
                        problems.append(f"{f}:{lineno}: '{command} {leftover}' is not a real command")
                    continue
                if shape["allow_extra"]:
                    continue
                positionals = 0
                expect_value = False
                for token in tokens[index:]:
                    token = re.sub(r"\[/?[\w.]+\]", "", token).strip("().,;:'\"`|")
                    if not token:
                        continue
                    if expect_value:
                        expect_value = False
                    elif token.startswith("-"):
                        names = token.split("=", 1)[0].split("/")
                        if any(name in FOREIGN or name in root_flags or name in container_flags for name in names):
                            continue
                        missing = [name for name in names if name not in shape["flags"]]
                        if missing:
                            problems.append(f"{f}:{lineno}: '{command}' does not accept {', '.join(missing)}")
                            continue
                        expect_value = shape["flags"][names[0]] and "=" not in token
                    elif _PLACEHOLDER.match(token):
                        positionals += 1
                    elif quoted_invocation and re.match(r"^[a-z][\w.-]*$", token):
                        # A bench/site/domain name written in plain lowercase inside a quoted
                        # or fenced invocation (`fm bake mybench --app-image ...`), which fm's
                        # own messages never do but these docs do constantly. Lets the scan
                        # reach a later flag without counting it as a declared positional, so
                        # it cannot inflate the max_pos check below on its own.
                        continue
                    else:
                        break
                if positionals > shape["max_pos"]:
                    problems.append(
                        f"{f}:{lineno}: '{command}' takes {shape['max_pos']} argument(s), "
                        f"the text passes {positionals}"
                    )
    return problems


def check_stale_fm_docs(files: list[Path], spec: dict[tuple[str, ...], dict]) -> list[str]:
    """Docs that still tell the reader to type the retired `fm` name instead of `fmx`.

    Same chain-walk as `check_doc_commands`, against `fm ` instead of `fmx `. A line that
    resolves to a real command under the old name is stale regardless of whether its flags
    would also be valid: the instruction itself names the wrong binary. Unlike the dangling-
    subcommand case in `check_doc_commands`, this does not require the invocation to be
    quoted -- `fm` has no in-container namesake to confuse it with, so a resolved chain is
    unambiguous wherever it appears. The caller excludes changelog.md the same way it does for
    `check_doc_commands`, since that file names `fm` on purpose as shipped history.
    """
    problems: list[str] = []
    for f in files:
        for lineno, line in enumerate(f.read_text().splitlines(), 1):
            for match in re.finditer(r"(?<![\w-])fm ((?:[a-z][a-z0-9-]*)(?: [^\s'\"`,;]+)*)", line):
                tokens = match.group(1).split()
                chain: tuple[str, ...] = ()
                index = 0
                while index < len(tokens) and (*chain, tokens[index]) in spec:
                    chain = (*chain, tokens[index])
                    index += 1
                if not chain:
                    continue
                command = " ".join(chain)
                problems.append(f"{f}:{lineno}: uses the retired name 'fm {command}'; say 'fmx {command}'")
    return problems



CONFIG_DOC = Path("docs/reference/configuration.md")

# model_of/unwrap below stop recursing at these two files' boundary: a nested model defined
# elsewhere (SSLCertificate, DNSProviderConfig) is out of scope for THIS check, which reads
# only frappe_manager/site_manager/bench_config.py and frappe_manager/metadata_manager.py.
_CONFIG_MODULES = {"frappe_manager.site_manager.bench_config", "frappe_manager.metadata_manager"}

# A key that collides by name between a site-scoped field and a global one (the bench's own
# `[sites."<name>".auth]` reuses `WebAuthConfig`, same as the bench-wide `[auth]`) is checked
# against text found only in a `sites."..."`-scoped section, never the whole page, which is the
# only way a per-site `upload_limit` missing from every such section is told apart from the
# bench-level key of the same name having its own heading. These two are documented only by
# the cross-reference in "Per-site auth" ('same keys as `[auth]` except...'), whose own example
# shows web/user/password but not the allow lists.
SITE_CONFIG_KEY_ALLOWLIST: dict[str, str] = {
    "allow_ips": "Per-site auth refers to [auth] by name instead of relisting its keys.",
    "allow_paths": "same reference as allow_ips.",
}


def _unwrap_optional(ann):
    import typing

    if typing.get_origin(ann) is typing.Union:
        args = [a for a in typing.get_args(ann) if a is not type(None)]
        if len(args) == 1:
            return _unwrap_optional(args[0])
    return ann


def _model_of(ann):
    import typing

    from pydantic import BaseModel

    ann = _unwrap_optional(ann)
    origin = typing.get_origin(ann)
    if origin in (list, set, frozenset):
        args = typing.get_args(ann)
        return _model_of(args[0]) if args else None
    if origin is dict:
        args = typing.get_args(ann)
        return _model_of(args[1]) if len(args) == 2 else None
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        return ann
    return None


def persisted_config_fields() -> list[tuple[str, str]]:
    """Every `(scope, key)` a `BenchConfig`/`FMConfigManager` field actually writes to disk.

    `scope` is ``"site"`` for a field reached through `BenchConfig.sites` (one bench_config.toml
    can serve several sites) and ``"global"`` for everything else. Stops, by rule rather than by
    allowlist, at `NOT_WRITTEN_TO_DISK`, the global config's equivalent `GLOBAL_NOT_WRITTEN`
    (gen_config_example.py), and any field pydantic itself excludes from `model_dump`
    (`Field(..., exclude=True)`) -- `set_default_site` is create-time-only this second way and
    is not in `NOT_WRITTEN_TO_DISK`, so checking the field's own `exclude` flag catches it where
    the named list alone would not. Also stops at a nested model defined outside these two files
    (see `_CONFIG_MODULES`).
    """
    from frappe_manager.metadata_manager import FMConfigManager
    from frappe_manager.site_manager.bench_config import NOT_WRITTEN_TO_DISK, BenchConfig
    from gen_config_example import GLOBAL_NOT_WRITTEN

    found: list[tuple[str, str]] = []
    seen: set[tuple[type, str]] = set()

    def walk(model, scope: str, exclude: frozenset) -> None:
        if (model, scope) in seen:
            return
        seen.add((model, scope))
        for name, field in model.model_fields.items():
            if name in exclude or field.exclude:
                continue
            nested = _model_of(field.annotation)
            if nested is not None and nested.__module__ in _CONFIG_MODULES:
                walk(nested, "site" if name == "sites" else scope, frozenset())
            else:
                found.append((scope, field.alias or name))

    walk(BenchConfig, "global", NOT_WRITTEN_TO_DISK)
    walk(FMConfigManager, "global", GLOBAL_NOT_WRITTEN)
    return found


def all_model_keys() -> set[str]:
    """Every TOML key name reachable from the two root configs, `NOT_WRITTEN_TO_DISK` fields
    included: used only to check the OTHER direction (a key the docs claim exists that no
    field backs at all), where a field fm merely does not write is still a real name to find.
    """
    from frappe_manager.metadata_manager import FMConfigManager, recognised_fm_config_keys
    from frappe_manager.site_manager.bench_config import (
        BenchConfig,
        recognised_bench_config_keys,
        recognised_deployments_keys,
        recognised_ssl_keys,
    )

    keys: set[str] = set()
    seen: set[type] = set()

    def walk(model) -> None:
        if model in seen:
            return
        seen.add(model)
        for name, field in model.model_fields.items():
            keys.add(field.alias or name)
            nested = _model_of(field.annotation)
            if nested is not None and nested.__module__ in _CONFIG_MODULES:
                walk(nested)

    walk(BenchConfig)
    walk(FMConfigManager)
    keys |= recognised_bench_config_keys() | recognised_ssl_keys() | recognised_deployments_keys()
    keys |= recognised_fm_config_keys()
    return keys


def documented_config_keys(doc_text: str) -> set[str]:
    """Key names the page claims to document: a `**File key:**` line, a `| Key | ... |` table,
    a dotted-name heading (`` `network.subnet_cidr` ``), or a `- `key`: ...` field list.

    SSL certificate and DNS-provider fields are skipped on purpose: those live on
    `SSLCertificate`/`DNSProviderConfig`, outside the two files this check reads models from, so
    a key named only there is out of scope for this check, not a mismatch.
    """
    keys: set[str] = set()
    ident = re.compile(r"`([a-z][a-z0-9_]*)`")
    dotted = re.compile(r"`[a-z][a-z0-9_.]*\.([a-z][a-z0-9_]*)`")
    bullet = re.compile(r"^\s*-\s*`([a-z][a-z0-9_]*)`\s*:")

    headings = list(re.finditer(r"^#{2,4}\s+(.*)$", doc_text, re.M))
    for idx, h in enumerate(headings):
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(doc_text)
        heading_text = h.group(1)
        block = doc_text[h.start() : end]
        skip_bullets = bool(re.search(r"ssl certificates|dns providers", heading_text, re.I))

        if heading_text.startswith("`"):
            keys |= set(dotted.findall(heading_text))
            bare = re.match(r"^`([a-z][a-z0-9_]*)`", heading_text)
            if bare:
                keys.add(bare.group(1))

        in_table = False
        for line in block.splitlines():
            if "**File key:**" in line:
                keys |= set(ident.findall(line.split("**File key:**", 1)[1]))
            elif not skip_bullets and bullet.match(line):
                keys.add(bullet.match(line).group(1))
            if re.match(r"\|\s*Key\s*\|", line):
                in_table = True
                continue
            if in_table:
                if not line.strip().startswith("|"):
                    in_table = False
                elif not re.match(r"\|\s*-{2,}", line):
                    cell = line.split("|")[1].strip()
                    m = ident.match(cell)
                    if m:
                        keys.add(m.group(1))
    return keys


def check_config_keys() -> tuple[list[str], list[str]]:
    """Every persisted model field documented, and every documented key backed by a field.

    This is what would have caught `tools_user`, `tools_password`, `backend_subnet_cidr` and
    `startup_timeout` all missing from docs/reference/configuration.md at once: each is a real
    field on a model that already has a page, which neither the flag checks above nor mkdocs
    itself has any reason to notice.
    """
    if not CONFIG_DOC.exists():
        return [], []
    doc_text = CONFIG_DOC.read_text()

    site_blocks = []
    headings = list(re.finditer(r"^#{2,4}\s+.*$", doc_text, re.M))
    for idx, h in enumerate(headings):
        end = headings[idx + 1].start() if idx + 1 < len(headings) else len(doc_text)
        block = doc_text[h.start() : end]
        if 'sites."' in block:
            site_blocks.append(block)
    site_text = "\n".join(site_blocks)

    missing: list[str] = []
    for scope, key in sorted(set(persisted_config_fields())):
        if scope == "site" and key in SITE_CONFIG_KEY_ALLOWLIST:
            continue
        haystack = site_text if scope == "site" else doc_text
        if not re.search(rf"(?<![\w-]){re.escape(key)}(?![\w-])", haystack):
            missing.append(f"{CONFIG_DOC}: {scope} key `{key}` has no model field documented on this page")

    model_keys = all_model_keys()
    unknown = [
        f"{CONFIG_DOC}: documents `{key}`, which no BenchConfig/FMConfigManager field produces"
        for key in sorted(documented_config_keys(doc_text) - model_keys)
    ]
    return missing, unknown


def main() -> int:
    os.chdir(ROOT)
    files = hand_written()
    all_files = all_docs()
    # changelog.md is append-only history: it names retired commands and flags on purpose
    # ("`fm services real-ip` becomes `fm services trusted-proxies`"), so it is excluded from
    # the command/flag resolution check the same way it is excluded from style checks.
    command_check_files = [p for p in all_files if p != Path("docs/changelog.md")]
    fm, fmx = fm_flags(), fmx_flags()

    # A silent no-op is worse than a failure: an empty glob or a CLI that stopped importing
    # would otherwise report a clean run and let anything through.
    if len(files) < 10 or len(fm) < 50:
        print(f"docslint is not working: {len(files)} docs, {len(fm)} fm flags, {len(fmx)} fmx flags")
        return 2

    dash_hits = check_dashes(files)
    absolute, broken = check_links()
    unknown = check_flags(files, fm | fmx | FOREIGN)
    unknown_src = check_source_flags(fm | fmx | FOREIGN | SOURCE_FOREIGN)

    for label, items in (
        ("dash violations", dash_hits),
        ("absolute links", absolute),
        ("broken links", broken),
    ):
        print(f"{label}: {len(items)}")
        for line in items[:12]:
            print(f"  {line}")
    print(f"flags in docs that exist in neither fm nor fmx: {len(unknown)}")
    for flag, where in sorted(unknown.items()):
        print(f"  {flag:<32} {sorted(where)[:2]}")
    print(f"flags in fm's own messages that the CLI does not have: {len(unknown_src)}")
    for flag, where in sorted(unknown_src.items()):
        print(f"  {flag:<32} {sorted(where)[:2]}")

    spec = fm_command_spec()
    bad_commands = check_message_commands(spec, container_flags=fmx)
    print(f"fmx commands in fmx's own messages that would be refused: {len(bad_commands)}")
    for line in bad_commands[:12]:
        print(f"  {line}")

    bad_doc_commands = check_doc_commands(command_check_files, spec, container_flags=fmx)
    print(f"fmx commands/flags written in the docs that the CLI would refuse: {len(bad_doc_commands)}")
    for line in bad_doc_commands[:40]:
        print(f"  {line}")

    stale_messages = check_stale_fm_messages(spec)
    print(f"fmx's own messages that still tell the operator to run the retired 'fm' name: {len(stale_messages)}")
    for line in stale_messages[:12]:
        print(f"  {line}")

    stale_docs = check_stale_fm_docs(command_check_files, spec)
    print(f"docs that still tell the reader to run the retired 'fm' name: {len(stale_docs)}")
    for line in stale_docs[:40]:
        print(f"  {line}")

    missing_keys, unknown_keys = check_config_keys()
    print(f"persisted config fields undocumented in configuration.md: {len(missing_keys)}")
    for line in missing_keys[:40]:
        print(f"  {line}")
    print(f"documented config keys with no backing model field: {len(unknown_keys)}")
    for line in unknown_keys[:40]:
        print(f"  {line}")

    failed = bool(
        dash_hits
        or absolute
        or broken
        or unknown
        or unknown_src
        or bad_commands
        or bad_doc_commands
        or stale_messages
        or stale_docs
        or missing_keys
        or unknown_keys
    )
    if not failed:
        print(f"\nclean: {len(files)} hand-written docs checked against {len(fm | fmx)} real flags")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
