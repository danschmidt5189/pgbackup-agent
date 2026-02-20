"""Tests for pgbackup.cli."""

import pytest

from pgbackup.cli import build_parser, main


class TestBuildParser:
    """Verify the argument parser structure."""

    def test_returns_parser(self):
        parser = build_parser()
        assert parser.prog == "pgbackup"

    def test_defaults(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.databases is None
        assert args.s3 is False
        assert args.smtp is False
        assert args.slack is False
        assert args.smtp_port == 587


class TestMainNoDb:
    """When no --db is given, print help and exit 0."""

    def test_no_args(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0
        assert "pgbackup" in capsys.readouterr().out

    def test_none_argv(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "sys.argv", ["pgbackup"]
        )
        with pytest.raises(SystemExit) as exc_info:
            main(None)
        assert exc_info.value.code == 0


class TestMainValidation:
    """Argument-validation error paths."""

    def test_db_without_dest(self):
        with pytest.raises(SystemExit) as exc_info:
            main(["--db", "postgres://u@h"])
        assert exc_info.value.code == 2

    def test_s3_without_bucket(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", "/tmp/{dbname}.dump",
                "--s3",
            ])
        assert exc_info.value.code == 2

    def test_s3_without_key(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", "/tmp/{dbname}.dump",
                "--s3", "--s3-bucket", "b",
            ])
        assert exc_info.value.code == 2

    def test_smtp_without_server(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", "/tmp/{dbname}.dump",
                "--smtp",
            ])
        assert exc_info.value.code == 2

    def test_smtp_without_from(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", "/tmp/{dbname}.dump",
                "--smtp", "--smtp-server", "mail",
            ])
        assert exc_info.value.code == 2

    def test_slack_without_webhook(self):
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", "/tmp/{dbname}.dump",
                "--slack",
            ])
        assert exc_info.value.code == 2


class TestMainRunsBackup:
    """When args are valid, main() delegates to run_backup."""

    def test_success_exit_0(self, monkeypatch, tmp_path):
        from pgbackup.models import BackupReport

        monkeypatch.setattr(
            "pgbackup.cli.run_backup",
            lambda args: BackupReport(),
        )
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", str(tmp_path / "{dbname}.dump"),
            ])
        assert exc_info.value.code == 0

    def test_failure_exit_1(self, monkeypatch, tmp_path):
        from pgbackup.models import (
            BackupReport,
            BackupResult,
            DatabaseConfig,
        )

        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="",
            host="h",
            port=5432,
        )
        report = BackupReport(
            results=[
                BackupResult(
                    database="db",
                    server=cfg,
                    local_path="",
                    size=0,
                    success=False,
                    error="fail",
                ),
            ]
        )
        monkeypatch.setattr(
            "pgbackup.cli.run_backup",
            lambda args: report,
        )
        with pytest.raises(SystemExit) as exc_info:
            main([
                "--db", "postgres://u@h",
                "--dest", str(tmp_path / "{dbname}.dump"),
            ])
        assert exc_info.value.code == 1
