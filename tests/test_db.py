"""Tests for pgbackup.db."""

import os
from unittest.mock import MagicMock, patch

import pytest

from pgbackup.db import (
    DEFAULT_PORTS,
    dump_database,
    list_databases,
    parse_db_url,
    read_password_file,
)
from pgbackup.models import DatabaseConfig


# ------------------------------------------------------------------
# parse_db_url
# ------------------------------------------------------------------


class TestParseDbUrl:
    """URL parsing tests."""

    def test_postgres_full_url(self):
        cfg = parse_db_url("postgres://user:pass@myhost:6543")
        assert cfg.driver == "postgres"
        assert cfg.username == "user"
        assert cfg.password == "pass"
        assert cfg.host == "myhost"
        assert cfg.port == 6543
        assert cfg.options == {}

    def test_mariadb_defaults(self):
        cfg = parse_db_url("mariadb://user@myhost")
        assert cfg.driver == "mariadb"
        assert cfg.password == ""
        assert cfg.port == DEFAULT_PORTS["mariadb"]

    def test_postgres_default_port(self):
        cfg = parse_db_url("postgres://u@h")
        assert cfg.port == 5432

    def test_options_parsed(self):
        cfg = parse_db_url(
            "postgres://u@h?env=production&region=us"
        )
        assert cfg.options == {
            "env": "production",
            "region": "us",
        }

    def test_password_file(self, password_file):
        url = f"postgres://u@h?password_file={password_file}"
        cfg = parse_db_url(url)
        assert cfg.password == "secret123"
        assert "password_file" not in cfg.options

    def test_unsupported_driver(self):
        with pytest.raises(ValueError, match="Unsupported"):
            parse_db_url("sqlite://u@h")

    def test_hostname_defaults_to_localhost(self):
        cfg = parse_db_url("postgres://u@")
        assert cfg.host == "localhost"


# ------------------------------------------------------------------
# read_password_file
# ------------------------------------------------------------------


class TestReadPasswordFile:
    """Password file reading."""

    def test_strips_whitespace(self, password_file):
        assert read_password_file(password_file) == "secret123"


# ------------------------------------------------------------------
# list_databases
# ------------------------------------------------------------------


class TestListDatabases:
    """Database listing with mocked subprocess."""

    def test_postgres_filters_system_dbs(self, pg_config):
        stdout = "postgres\ntemplate0\ntemplate1\nmydb\nother\n"
        mock_result = MagicMock(stdout=stdout)
        with patch(
            "pgbackup.db.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            dbs = list_databases(pg_config)

        assert dbs == ["mydb", "other"]
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "psql"
        env = mock_run.call_args[1]["env"]
        assert env["PGPASSWORD"] == "pgpass"

    def test_postgres_no_password(self):
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="",
            host="h",
            port=5432,
        )
        mock_result = MagicMock(stdout="mydb\n")
        with patch(
            "pgbackup.db.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            dbs = list_databases(cfg)

        assert dbs == ["mydb"]
        env = mock_run.call_args[1]["env"]
        assert "PGPASSWORD" not in env

    def test_mariadb_filters_system_dbs(self, mdb_config):
        stdout = (
            "information_schema\nmysql\n"
            "performance_schema\nsys\ntestdb\n"
        )
        mock_result = MagicMock(stdout=stdout)
        with patch(
            "pgbackup.db.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            dbs = list_databases(mdb_config)

        assert dbs == ["testdb"]
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "mariadb"
        env = mock_run.call_args[1]["env"]
        assert env["MYSQL_PWD"] == "mdbpass"

    def test_mariadb_no_password(self):
        cfg = DatabaseConfig(
            driver="mariadb",
            username="u",
            password="",
            host="h",
            port=3306,
        )
        mock_result = MagicMock(stdout="testdb\n")
        with patch(
            "pgbackup.db.subprocess.run",
            return_value=mock_result,
        ) as mock_run:
            dbs = list_databases(cfg)

        assert dbs == ["testdb"]
        env = mock_run.call_args[1]["env"]
        assert "MYSQL_PWD" not in env

    def test_empty_output(self, pg_config):
        mock_result = MagicMock(stdout="")
        with patch(
            "pgbackup.db.subprocess.run",
            return_value=mock_result,
        ):
            dbs = list_databases(pg_config)
        assert dbs == []


# ------------------------------------------------------------------
# dump_database
# ------------------------------------------------------------------


class TestDumpDatabase:
    """Database dump with mocked subprocess."""

    def test_postgres_dump(self, pg_config, tmp_path):
        dest = str(tmp_path / "sub" / "db.dump")
        with patch(
            "pgbackup.db.subprocess.run"
        ) as mock_run:
            dump_database(pg_config, "mydb", dest)

        assert os.path.isdir(str(tmp_path / "sub"))
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "pg_dump"
        assert "mydb" in cmd
        env = mock_run.call_args[1]["env"]
        assert env["PGPASSWORD"] == "pgpass"

    def test_mariadb_dump(self, mdb_config, tmp_path):
        dest = str(tmp_path / "db.dump")
        with patch(
            "pgbackup.db.subprocess.run"
        ) as mock_run:
            dump_database(mdb_config, "testdb", dest)

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "mariadb-dump"
        assert "testdb" in cmd
        env = mock_run.call_args[1]["env"]
        assert env["MYSQL_PWD"] == "mdbpass"

    def test_postgres_no_password(self, tmp_path):
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="",
            host="h",
            port=5432,
        )
        dest = str(tmp_path / "db.dump")
        with patch(
            "pgbackup.db.subprocess.run"
        ) as mock_run:
            dump_database(cfg, "mydb", dest)

        env = mock_run.call_args[1]["env"]
        assert "PGPASSWORD" not in env

    def test_mariadb_no_password(self, tmp_path):
        cfg = DatabaseConfig(
            driver="mariadb",
            username="u",
            password="",
            host="h",
            port=3306,
        )
        dest = str(tmp_path / "db.dump")
        with patch(
            "pgbackup.db.subprocess.run"
        ) as mock_run:
            dump_database(cfg, "mydb", dest)

        env = mock_run.call_args[1]["env"]
        assert "MYSQL_PWD" not in env

    def test_creates_parent_dirs(self, pg_config, tmp_path):
        dest = str(tmp_path / "a" / "b" / "c" / "db.dump")
        with patch("pgbackup.db.subprocess.run"):
            dump_database(pg_config, "mydb", dest)
        assert os.path.isdir(str(tmp_path / "a" / "b" / "c"))
