"""The committed docs/commands/*.md pages must match what scripts/update_cli_docs.py
would produce from the live CLI right now.

Nothing before this diffed them: a flag or help string can change, nobody runs
`just docs-gen`, and the committed page quietly lags the CLI it is supposed to mirror until
someone notices by hand. Modelled on test_config_example.py's "regenerate into a throwaway
location and compare" pattern, same reasoning: generating correctly only helps if staying
generated is enforced.
"""

import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from update_cli_docs import generate_all_docs

COMMITTED = REPO_ROOT / "docs" / "commands"

# index.md is the one hand-written page in this directory; update_cli_docs.py never writes it.
COMMITTED_PAGES = sorted(p.name for p in COMMITTED.glob("*.md") if p.name != "index.md")


@pytest.fixture(scope="module")
def generated() -> Path:
    tmp = Path(tempfile.mkdtemp())
    generate_all_docs(tmp)
    return tmp / "commands"


@pytest.mark.parametrize("name", COMMITTED_PAGES)
def test_a_committed_command_page_matches_the_live_cli(generated: Path, name: str):
    generated_file = generated / name
    assert generated_file.exists(), f"{name} is committed but the live CLI no longer produces it. Run `just docs-gen`."
    actual = generated_file.read_text()
    expected = (COMMITTED / name).read_text()
    assert actual == expected, f"docs/commands/{name} is stale. Regenerate it with `just docs-gen`."


def test_the_live_cli_produces_no_page_missing_from_the_repo(generated: Path):
    generated_names = {p.name for p in generated.glob("*.md")}
    missing = generated_names - set(COMMITTED_PAGES)
    assert missing == set(), f"the live CLI produces pages not committed: {missing}. Run `just docs-gen`."
