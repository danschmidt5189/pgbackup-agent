"""Tests for pgbackup.models."""

from pgbackup.models import BackupResult, DatabaseConfig


class TestDatabaseConfig:
    """DatabaseConfig dataclass tests."""

    def test_defaults(self):
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="p",
            host="h",
            port=5432,
        )
        assert cfg.options == {}

    def test_with_options(self):
        cfg = DatabaseConfig(
            driver="mariadb",
            username="u",
            password="p",
            host="h",
            port=3306,
            options={"env": "prod"},
        )
        assert cfg.options == {"env": "prod"}


class TestBackupResult:
    """BackupResult dataclass tests."""

    def test_defaults(self):
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="p",
            host="h",
            port=5432,
        )
        r = BackupResult(
            database="db1",
            server=cfg,
            local_path="/tmp/db1.dump",
            size=100,
        )
        assert r.success is True
        assert r.error is None
        assert r.s3_uri is None


class TestBackupReport:
    """BackupReport tests."""

    def test_empty_report_is_successful(self, empty_report):
        assert empty_report.success is True
        assert empty_report.total_size == 0

    def test_all_success(self, success_report):
        assert success_report.success is True
        assert success_report.total_size == 2048

    def test_partial_failure(self, failure_report):
        assert failure_report.success is False
        # Only the successful result's size counts.
        assert failure_report.total_size == 2048
