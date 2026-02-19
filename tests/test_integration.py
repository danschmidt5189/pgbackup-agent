"""Integration tests — require Docker Compose services.

These tests are parametrized across all configured database
versions and exercise the real dump / list / upload / email
pipeline end-to-end.
"""

import json
import os
from urllib.request import urlopen

import boto3
import pytest

from pgbackup.backup import run_backup
from pgbackup.cli import build_parser
from pgbackup.db import dump_database, list_databases
from pgbackup.models import DatabaseConfig

IN_DOCKER = os.path.exists("/.dockerenv")

pytestmark = pytest.mark.skipif(
    not IN_DOCKER,
    reason="Integration tests require Docker Compose services",
)

# -----------------------------------------------------------------
# Database fixtures (parametrized over versions)
# -----------------------------------------------------------------

PG_HOSTS = ["postgres16", "postgres17", "postgres18"]
MDB_HOSTS = ["mariadb1011", "mariadb118", "mariadb114"]


@pytest.fixture(params=PG_HOSTS, ids=PG_HOSTS)
def pg_int_config(request):
    return DatabaseConfig(
        driver="postgres",
        username="pguser",
        password="pgpass",
        host=request.param,
        port=5432,
        options={"env": "test"},
    )


@pytest.fixture(params=MDB_HOSTS, ids=MDB_HOSTS)
def mdb_int_config(request):
    return DatabaseConfig(
        driver="mariadb",
        username="mdbuser",
        password="mdbpass",
        host=request.param,
        port=3306,
        options={"env": "test"},
    )


@pytest.fixture()
def s3_client():
    return boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin",
    )


@pytest.fixture()
def s3_bucket(s3_client):
    bucket = "pgbackup-integration"
    try:
        s3_client.create_bucket(Bucket=bucket)
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        pass
    return bucket


# -----------------------------------------------------------------
# Expected seed databases from initdb/ scripts
# -----------------------------------------------------------------

PG_SEED_DBS = {"climbers", "athletes"}
MDB_SEED_DBS = {"testdb", "racing"}

# -----------------------------------------------------------------
# list_databases
# -----------------------------------------------------------------


class TestListDatabasesIntegration:
    """Verify database discovery against real servers."""

    def test_postgres_discovers_seed_databases(
        self, pg_int_config,
    ):
        dbs = list_databases(pg_int_config)
        assert PG_SEED_DBS.issubset(set(dbs))

    def test_postgres_excludes_system_databases(
        self, pg_int_config,
    ):
        dbs = list_databases(pg_int_config)
        for sysdb in ("template0", "template1", "postgres"):
            assert sysdb not in dbs

    def test_mariadb_discovers_seed_databases(
        self, mdb_int_config,
    ):
        dbs = list_databases(mdb_int_config)
        assert MDB_SEED_DBS.issubset(set(dbs))

    def test_mariadb_excludes_system_databases(
        self, mdb_int_config,
    ):
        dbs = list_databases(mdb_int_config)
        for sysdb in (
            "information_schema", "mysql",
            "performance_schema", "sys",
        ):
            assert sysdb not in dbs


# -----------------------------------------------------------------
# dump_database
# -----------------------------------------------------------------


class TestDumpDatabaseIntegration:
    """Verify dumps produce non-empty files."""

    def test_postgres_dump(self, pg_int_config, tmp_path):
        dest = str(tmp_path / "climbers.dump")
        dump_database(pg_int_config, "climbers", dest)
        assert os.path.getsize(dest) > 0

    def test_mariadb_dump(self, mdb_int_config, tmp_path):
        dest = str(tmp_path / "testdb.dump")
        dump_database(mdb_int_config, "testdb", dest)
        assert os.path.getsize(dest) > 0

    def test_mariadb_dump_racing(self, mdb_int_config, tmp_path):
        dest = str(tmp_path / "racing.dump")
        dump_database(mdb_int_config, "racing", dest)
        assert os.path.getsize(dest) > 0


# -----------------------------------------------------------------
# Full pipeline
# -----------------------------------------------------------------


class TestFullPipeline:
    """End-to-end: backup → S3 → email."""

    def test_postgres_pipeline(
        self, pg_int_config, tmp_path, s3_bucket,
    ):
        host = pg_int_config.host
        parser = build_parser()
        args = parser.parse_args([
            "--db",
            f"postgres://pguser:pgpass@{host}"
            "?env=integration",
            "--dest",
            str(tmp_path / "{env}/{dbhost}/{dbname}.dump"),
            "--s3",
            "--s3-bucket", s3_bucket,
            "--s3-key", "{env}/{dbhost}/{filename}",
            "--s3-endpoint-url", "http://minio:9000",
        ])

        report = run_backup(args)

        assert report.success
        backed_up_dbs = {r.database for r in report.results}
        assert PG_SEED_DBS.issubset(backed_up_dbs)
        for r in report.results:
            assert os.path.exists(r.local_path)
            assert r.size > 0
            assert r.s3_uri is not None

    def test_mariadb_pipeline(
        self, mdb_int_config, tmp_path, s3_bucket,
    ):
        host = mdb_int_config.host
        parser = build_parser()
        args = parser.parse_args([
            "--db",
            f"mariadb://mdbuser:mdbpass@{host}"
            "?env=integration",
            "--dest",
            str(tmp_path / "{env}/{dbhost}/{dbname}.dump"),
            "--s3",
            "--s3-bucket", s3_bucket,
            "--s3-key", "{env}/{dbhost}/{filename}",
            "--s3-endpoint-url", "http://minio:9000",
            "--smtp",
            "--smtp-server", "mailpit",
            "--smtp-port", "1025",
            "--smtp-from", "test@pgbackup.local",
        ])

        report = run_backup(args)

        assert report.success
        backed_up_dbs = {r.database for r in report.results}
        assert MDB_SEED_DBS.issubset(backed_up_dbs)
        for r in report.results:
            assert os.path.exists(r.local_path)
            assert r.size > 0
            assert r.s3_uri is not None

    def test_smtp_email_received(self, tmp_path):
        """Verify Mailpit actually received an email."""
        parser = build_parser()
        # Pick any available MariaDB host.
        args = parser.parse_args([
            "--db",
            "mariadb://mdbuser:mdbpass@mariadb1011"
            "?env=mailtest",
            "--dest",
            str(tmp_path / "{dbname}.dump"),
            "--smtp",
            "--smtp-server", "mailpit",
            "--smtp-port", "1025",
            "--smtp-from", "verify@pgbackup.local",
        ])

        run_backup(args)

        # Query Mailpit API for received messages.
        resp = urlopen(
            "http://mailpit:8025/api/v1/messages"
        )
        data = json.loads(resp.read())
        subjects = [
            m["Subject"] for m in data.get("messages", [])
        ]
        assert any("[pgbackup]" in s for s in subjects)
