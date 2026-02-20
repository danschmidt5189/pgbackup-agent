"""Tests for pgbackup.backup orchestration."""

from argparse import Namespace
from unittest.mock import patch


from pgbackup.backup import (
    _backup_single,
    _resolve_smtp_password,
    _send_notifications,
    run_backup,
)
from pgbackup.models import (
    DatabaseConfig,
)


def _make_args(**overrides):
    """Build a minimal Namespace imitating parsed CLI args."""
    defaults = {
        "databases": ["postgres://u:p@h"],
        "dest": "/tmp/{dbname}.dump",
        "s3": False,
        "s3_bucket": None,
        "s3_key": None,
        "s3_endpoint_url": None,
        "smtp": False,
        "smtp_server": None,
        "smtp_port": 587,
        "smtp_from": None,
        "smtp_password": None,
        "smtp_password_file": None,
        "slack": False,
        "slack_webhook_url": None,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


# ------------------------------------------------------------------
# run_backup
# ------------------------------------------------------------------


class TestRunBackup:
    """Full backup pipeline tests."""

    @patch("pgbackup.backup.dump_database")
    @patch("pgbackup.backup.list_databases", return_value=["db1"])
    def test_basic_success(
        self, mock_list, mock_dump, tmp_path,
    ):
        dest = str(tmp_path / "{dbname}.dump")
        args = _make_args(dest=dest)

        # Create a fake dump file so os.path.getsize works.
        dump_path = tmp_path / "db1.dump"
        dump_path.write_bytes(b"x" * 100)

        report = run_backup(args)
        assert report.success
        assert len(report.results) == 1
        assert report.results[0].database == "db1"
        assert report.results[0].size == 100

    @patch("pgbackup.backup.list_databases")
    def test_list_databases_failure(self, mock_list):
        mock_list.side_effect = RuntimeError("conn refused")
        args = _make_args()
        report = run_backup(args)
        assert not report.success
        assert report.results[0].database == "*"
        assert "conn refused" in report.results[0].error

    @patch("pgbackup.backup.dump_database")
    @patch(
        "pgbackup.backup.list_databases",
        return_value=["db1", "db2"],
    )
    def test_multiple_databases(
        self, mock_list, mock_dump, tmp_path,
    ):
        dest = str(tmp_path / "{dbname}.dump")
        args = _make_args(dest=dest)
        for name in ("db1", "db2"):
            (tmp_path / f"{name}.dump").write_bytes(b"x")

        report = run_backup(args)
        assert len(report.results) == 2

    @patch("pgbackup.backup.upload_to_s3")
    @patch("pgbackup.backup.dump_database")
    @patch("pgbackup.backup.list_databases", return_value=["db1"])
    def test_s3_upload(
        self, mock_list, mock_dump, mock_s3, tmp_path,
    ):
        dest = str(tmp_path / "{dbname}.dump")
        args = _make_args(
            dest=dest,
            s3=True,
            s3_bucket="bkt",
            s3_key="{filename}",
        )
        (tmp_path / "db1.dump").write_bytes(b"data")
        mock_s3.return_value = "s3://bkt/db1.dump"

        report = run_backup(args)
        assert report.success
        assert report.results[0].s3_uri == "s3://bkt/db1.dump"
        mock_s3.assert_called_once()


# ------------------------------------------------------------------
# _backup_single
# ------------------------------------------------------------------


class TestBackupSingle:
    """Individual database backup."""

    @patch("pgbackup.backup.dump_database")
    def test_dump_failure(self, mock_dump, tmp_path):
        mock_dump.side_effect = RuntimeError("dump failed")
        args = _make_args(dest=str(tmp_path / "{dbname}.dump"))
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="p",
            host="h",
            port=5432,
        )
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = _backup_single(args, cfg, "mydb", now)
        assert not result.success
        assert "dump failed" in result.error

    @patch("pgbackup.backup.upload_to_s3")
    @patch("pgbackup.backup.dump_database")
    def test_s3_failure(
        self, mock_dump, mock_s3, tmp_path,
    ):
        mock_s3.side_effect = RuntimeError("s3 err")
        dest = str(tmp_path / "{dbname}.dump")
        args = _make_args(
            dest=dest,
            s3=True,
            s3_bucket="bkt",
            s3_key="{filename}",
        )
        (tmp_path / "mydb.dump").write_bytes(b"data")

        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="p",
            host="h",
            port=5432,
        )
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        result = _backup_single(args, cfg, "mydb", now)
        assert not result.success
        assert "S3 upload failed" in result.error
        assert result.size > 0


# ------------------------------------------------------------------
# _send_notifications
# ------------------------------------------------------------------


class TestSendNotifications:
    """Notification dispatch."""

    @patch("pgbackup.backup.send_smtp_notification")
    def test_smtp_sent(self, mock_smtp, success_report):
        args = _make_args(
            smtp=True,
            smtp_server="mail",
            smtp_port=1025,
            smtp_from="a@b.com",
        )
        _send_notifications(args, success_report)
        mock_smtp.assert_called_once()

    @patch("pgbackup.backup.send_smtp_notification")
    def test_smtp_failure_logged(
        self, mock_smtp, success_report,
    ):
        mock_smtp.side_effect = RuntimeError("smtp err")
        args = _make_args(
            smtp=True,
            smtp_server="mail",
            smtp_port=1025,
            smtp_from="a@b.com",
        )
        # Should not raise — error is logged.
        _send_notifications(args, success_report)

    @patch("pgbackup.backup.send_slack_notification")
    def test_slack_sent(self, mock_slack, success_report):
        args = _make_args(
            slack=True,
            slack_webhook_url="https://hooks/xxx",
        )
        _send_notifications(args, success_report)
        mock_slack.assert_called_once()

    @patch("pgbackup.backup.send_slack_notification")
    def test_slack_failure_logged(
        self, mock_slack, success_report,
    ):
        mock_slack.side_effect = RuntimeError("slack err")
        args = _make_args(
            slack=True,
            slack_webhook_url="https://hooks/xxx",
        )
        _send_notifications(args, success_report)

    def test_no_notifications(self, success_report):
        args = _make_args()
        # Neither smtp nor slack — nothing happens.
        _send_notifications(args, success_report)


# ------------------------------------------------------------------
# _resolve_smtp_password
# ------------------------------------------------------------------


class TestResolveSmtpPassword:
    """SMTP password resolution."""

    def test_password_arg(self):
        args = _make_args(smtp_password="s3cret")
        assert _resolve_smtp_password(args) == "s3cret"

    def test_password_file(self, password_file):
        args = _make_args(smtp_password_file=password_file)
        assert _resolve_smtp_password(args) == "secret123"

    def test_no_password(self):
        args = _make_args()
        assert _resolve_smtp_password(args) is None
