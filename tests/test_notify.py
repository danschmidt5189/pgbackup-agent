"""Tests for pgbackup.notify."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pgbackup.models import (
    BackupReport,
    BackupResult,
)
from pgbackup.notify import (
    _build_body,
    _build_slack_body,
    _build_subject,
    _format_size,
    send_slack_notification,
    send_smtp_notification,
)


# ------------------------------------------------------------------
# _format_size
# ------------------------------------------------------------------


class TestFormatSize:
    """Human-readable file-size formatting."""

    @pytest.mark.parametrize(
        ("size", "expected"),
        [
            (0, "0 B"),
            (1, "1 B"),
            (512, "512 B"),
            (1023, "1023 B"),
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (1048576, "1.0 MB"),
            (1073741824, "1.0 GB"),
            (1099511627776, "1.0 TB"),
            (1125899906842624, "1.0 PB"),
        ],
    )
    def test_format_size(self, size, expected):
        assert _format_size(size) == expected


# ------------------------------------------------------------------
# _build_subject / _build_body / _build_slack_body
# ------------------------------------------------------------------


class TestBuildSubject:
    """Subject line rendering."""

    def test_success(self, success_report):
        subj = _build_subject(success_report)
        assert "SUCCESS" in subj
        assert "1 databases backed up" in subj

    def test_failure(self, failure_report):
        subj = _build_subject(failure_report)
        assert "FAILURE" in subj
        assert "1 failed" in subj

    def test_empty(self, empty_report):
        subj = _build_subject(empty_report)
        assert "SUCCESS" in subj
        assert "0 databases backed up" in subj


class TestBuildBody:
    """Plain-text body rendering."""

    def test_success_includes_details(self, success_report):
        body = _build_body(success_report)
        assert "/backups/mydb.dump" in body
        assert "s3://bucket/mydb.dump" in body
        assert "2.0 KB" in body

    def test_failure_includes_error(self, failure_report):
        body = _build_body(failure_report)
        assert "connection refused" in body
        assert "FAILED" in body

    def test_no_s3(self, pg_config):
        report = BackupReport(
            results=[
                BackupResult(
                    database="db",
                    server=pg_config,
                    local_path="/x",
                    size=100,
                ),
            ]
        )
        body = _build_body(report)
        assert "S3:" not in body


class TestBuildSlackBody:
    """Slack mrkdwn body rendering."""

    def test_success_emoji(self, success_report):
        body = _build_slack_body(success_report)
        assert ":white_check_mark:" in body

    def test_failure_emoji(self, failure_report):
        body = _build_slack_body(failure_report)
        assert ":x:" in body

    def test_s3_uri_shown(self, success_report):
        body = _build_slack_body(success_report)
        assert "s3://bucket/mydb.dump" in body

    def test_no_s3(self, pg_config):
        report = BackupReport(
            results=[
                BackupResult(
                    database="db",
                    server=pg_config,
                    local_path="/x",
                    size=100,
                ),
            ]
        )
        body = _build_slack_body(report)
        assert "s3://" not in body


# ------------------------------------------------------------------
# send_smtp_notification
# ------------------------------------------------------------------


class TestSendSmtp:
    """SMTP notification with mocked smtplib."""

    def test_plain_smtp(self, success_report):
        mock_smtp = MagicMock()
        with patch(
            "pgbackup.notify.smtplib.SMTP",
            return_value=mock_smtp,
        ):
            send_smtp_notification(
                success_report,
                server="mail",
                port=1025,
                sender="a@b.com",
            )
        mock_smtp.ehlo.assert_called()
        mock_smtp.sendmail.assert_called_once()

    def test_starttls_with_password(self, success_report):
        mock_smtp = MagicMock()
        with patch(
            "pgbackup.notify.smtplib.SMTP",
            return_value=mock_smtp,
        ):
            send_smtp_notification(
                success_report,
                server="mail",
                port=587,
                sender="a@b.com",
                password="secret",
            )
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with(
            "a@b.com", "secret"
        )

    def test_ssl_port_465(self, success_report):
        mock_smtp = MagicMock()
        with patch(
            "pgbackup.notify.smtplib.SMTP_SSL",
            return_value=mock_smtp,
        ) as mock_cls:
            send_smtp_notification(
                success_report,
                server="mail",
                port=465,
                sender="a@b.com",
                password="secret",
            )
        mock_cls.assert_called_once_with("mail", 465)
        mock_smtp.starttls.assert_not_called()
        mock_smtp.login.assert_called_once_with(
            "a@b.com", "secret"
        )


# ------------------------------------------------------------------
# send_slack_notification
# ------------------------------------------------------------------


class TestSendSlack:
    """Slack webhook notification."""

    def test_sends_webhook(self, success_report):
        with patch(
            "pgbackup.notify.urlopen"
        ) as mock_urlopen:
            send_slack_notification(
                success_report,
                webhook_url="https://hooks.slack.com/xxx",
            )
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://hooks.slack.com/xxx"
        payload = json.loads(req.data)
        assert "text" in payload
        assert "blocks" in payload
