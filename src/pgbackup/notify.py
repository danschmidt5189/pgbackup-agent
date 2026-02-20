"""Notification functionality (SMTP and Slack)."""

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import Request, urlopen

from pgbackup.models import BackupReport

logger = logging.getLogger(__name__)


def send_smtp_notification(
    report: BackupReport,
    server: str,
    port: int,
    sender: str,
    password: str | None = None,
) -> None:
    """Send a backup report via email.

    The *sender* address is used as both ``From`` and ``To``.
    When a *password* is supplied, STARTTLS (or implicit TLS on
    port 465) plus LOGIN authentication are used.
    """
    subject = _build_subject(report)
    body = _build_body(report)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = sender
    msg.attach(MIMEText(body, "plain"))

    if port == 465:
        logger.debug(
            "Connecting to SMTP server %s:%d (SSL)",
            server, port,
        )
        smtp = smtplib.SMTP_SSL(server, port)
    else:
        logger.debug(
            "Connecting to SMTP server %s:%d",
            server, port,
        )
        smtp = smtplib.SMTP(server, port)

    with smtp:
        smtp.ehlo()
        if password:
            if port != 465:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(sender, password)
        smtp.sendmail(sender, [sender], msg.as_string())
    logger.info(
        "Email notification sent to %s via %s:%d",
        sender, server, port,
    )


def send_slack_notification(
    report: BackupReport,
    webhook_url: str,
) -> None:
    """Send a backup report via a Slack incoming webhook."""
    payload = {
        "text": _build_subject(report),
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": _build_slack_body(report),
                },
            },
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    urlopen(req)
    logger.info("Slack notification sent")


def _build_subject(report: BackupReport) -> str:
    """Build the notification subject line."""
    status = "SUCCESS" if report.success else "FAILURE"
    count = len(report.results)
    failed = sum(1 for r in report.results if not r.success)
    if failed:
        return (
            f"[pgbackup] {status}: {count} databases, "
            f"{failed} failed"
        )
    return f"[pgbackup] {status}: {count} databases backed up"


def _build_body(report: BackupReport) -> str:
    """Build the plain-text email body."""
    lines: list[str] = [_build_subject(report), ""]

    for result in report.results:
        status = "OK" if result.success else "FAILED"
        lines.append(
            f"  [{status}] {result.server.driver}://"
            f"{result.server.host}/{result.database}"
        )
        if result.success:
            lines.append(f"    Local: {result.local_path}")
            lines.append(f"    Size:  {_format_size(result.size)}")
            if result.s3_uri:
                lines.append(f"    S3:    {result.s3_uri}")
        else:
            lines.append(f"    Error: {result.error}")
        lines.append("")

    lines.append(f"Total size: {_format_size(report.total_size)}")
    return "\n".join(lines)


def _build_slack_body(report: BackupReport) -> str:
    """Build a Slack mrkdwn-formatted body."""
    lines: list[str] = []

    for result in report.results:
        if result.success:
            emoji = ":white_check_mark:"
        else:
            emoji = ":x:"
        lines.append(
            f"{emoji} `{result.server.driver}://"
            f"{result.server.host}/{result.database}`"
        )
        if result.success:
            lines.append(f"  Local: `{result.local_path}`")
            lines.append(
                f"  Size: {_format_size(result.size)}"
            )
            if result.s3_uri:
                lines.append(f"  S3: `{result.s3_uri}`")
        else:
            lines.append(f"  Error: {result.error}")

    lines.append("")
    lines.append(
        f"*Total size: {_format_size(report.total_size)}*"
    )
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Format a byte count in human-readable form."""
    if size_bytes == 0:
        return "0 B"

    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(size) < 1024:
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
