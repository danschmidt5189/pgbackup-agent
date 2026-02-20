"""Shared test fixtures and helpers."""

import os

import pytest

from pgbackup.models import BackupReport, BackupResult, DatabaseConfig

IN_DOCKER = os.path.exists("/.dockerenv")

integration = pytest.mark.skipif(
    not IN_DOCKER,
    reason="Integration tests require Docker Compose services",
)

PG_HOSTS = ["postgres16", "postgres17", "postgres18"]
MDB_HOSTS = ["mariadb1011", "mariadb118", "mariadb114"]

PG_SEED_DBS = {"climbers", "athletes", "pguser"}
MDB_SEED_DBS = {"testdb", "racing"}


# --- Simple (non-parametrized) unit-test fixtures ---


@pytest.fixture()
def pg_config():
    """A Postgres DatabaseConfig for unit tests."""
    return DatabaseConfig(
        driver="postgres",
        username="pguser",
        password="pgpass",
        host="localhost",
        port=5432,
        options={"env": "test"},
    )


@pytest.fixture()
def mdb_config():
    """A MariaDB DatabaseConfig for unit tests."""
    return DatabaseConfig(
        driver="mariadb",
        username="mdbuser",
        password="mdbpass",
        host="localhost",
        port=3306,
        options={"env": "test"},
    )


@pytest.fixture()
def password_file(tmp_path):
    """Create a temporary password file."""
    pf = tmp_path / "password"
    pf.write_text("  secret123  \n")
    return str(pf)


@pytest.fixture()
def success_report(pg_config):
    """A BackupReport where everything succeeded."""
    return BackupReport(
        results=[
            BackupResult(
                database="mydb",
                server=pg_config,
                local_path="/backups/mydb.dump",
                size=2048,
                s3_uri="s3://bucket/mydb.dump",
            ),
        ]
    )


@pytest.fixture()
def failure_report(pg_config):
    """A BackupReport with a failed backup."""
    return BackupReport(
        results=[
            BackupResult(
                database="mydb",
                server=pg_config,
                local_path="/backups/mydb.dump",
                size=2048,
            ),
            BackupResult(
                database="baddb",
                server=pg_config,
                local_path="",
                size=0,
                success=False,
                error="connection refused",
            ),
        ]
    )


@pytest.fixture()
def empty_report():
    """An empty BackupReport."""
    return BackupReport()
