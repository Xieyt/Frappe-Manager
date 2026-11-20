"""v1.0.0 migration: container log caps reach compose files that already exist.

Docker's json-file driver never rotates, and every compose file written before 1.0.0 carries no
`logging` block at all, so those containers grow on an operator's disk for as long as they run.
The template only decides what a NEW install gets, which is why this has to happen here.
"""

from unittest.mock import MagicMock

import yaml

from frappe_manager.migration_manager.migrations.migrate_1_0_0 import MigrationV100


def _run(tmp_path, doc):
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(yaml.safe_dump(doc, sort_keys=False))

    migration = MigrationV100.__new__(MigrationV100)
    migration.logger = MagicMock()
    migration._cap_container_logs(tmp_path)

    return yaml.safe_load(compose.read_text())


def test_a_service_without_a_cap_gets_one(tmp_path):
    """The bug this closes: an upgraded bench kept writing container output without a ceiling."""
    doc = _run(tmp_path, {"services": {"frappe": {"image": "old:1"}}})

    logging_block = doc["services"]["frappe"]["logging"]
    assert logging_block["driver"] == "json-file"
    assert logging_block["options"]["max-size"]
    assert logging_block["options"]["max-file"]


def test_an_operators_own_logging_block_is_left_alone(tmp_path):
    """A declared block is either a newer write or a deliberate choice; neither is ours to take."""
    doc = _run(tmp_path, {"services": {"nginx": {"image": "old:1", "logging": {"driver": "local"}}}})

    assert doc["services"]["nginx"]["logging"] == {"driver": "local"}


def test_every_compose_file_in_the_bench_directory_is_covered(tmp_path):
    """Workers and admin tools live in sibling compose files and grow the same way."""
    (tmp_path / "docker-compose.yml").write_text(yaml.safe_dump({"services": {"frappe": {"image": "old:1"}}}))
    (tmp_path / "docker-compose.workers.yml").write_text(
        yaml.safe_dump({"services": {"long-worker": {"image": "old:1"}}})
    )

    migration = MigrationV100.__new__(MigrationV100)
    migration.logger = MagicMock()
    migration._cap_container_logs(tmp_path)

    workers = yaml.safe_load((tmp_path / "docker-compose.workers.yml").read_text())
    assert workers["services"]["long-worker"]["logging"]["options"]["max-size"]
