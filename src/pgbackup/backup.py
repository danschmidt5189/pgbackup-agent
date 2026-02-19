"""Backup orchestration — ties together discovery, dump, upload,
and notification."""

import logging
import os
from datetime import datetime

from pgbackup.db import (
    dump_database,
    list_databases,
    parse_db_url,
    read_password_file,
)
from pgbackup.formatting import format_dest, format_s3_key
from pgbackup.models import BackupReport, BackupResult
from pgbackup.notify import (
    send_slack_notification,
    send_smtp_notification,
)
from pgbackup.storage import upload_to_s3

logger = logging.getLogger(__name__)


def run_backup(args) -> BackupReport:
    """Execute the full backup pipeline.

    1. Parse each ``--db`` URL.
    2. Discover databases on each server.
    3. Dump each database to the local ``--dest``.
    4. Optionally upload to S3.
    5. Send notifications (SMTP / Slack).
    """
    now = datetime.now().astimezone()
    report = BackupReport()

    for db_url in args.databases:
        config = parse_db_url(db_url)

        try:
            databases = list_databases(config)
        except Exception as exc:
            logger.error(
                "Failed to list databases on %s://%s: %s",
                config.driver,
                config.host,
                exc,
            )
            report.results.append(
                BackupResult(
                    database="*",
                    server=config,
                    local_path="",
                    size=0,
                    success=False,
                    error=str(exc),
                )
            )
            continue

        for dbname in databases:
            result = _backup_single(args, config, dbname, now)
            report.results.append(result)

    _send_notifications(args, report)
    return report


def _backup_single(args, config, dbname, now) -> BackupResult:
    """Back up a single database and optionally upload to S3."""
    dest = format_dest(args.dest, config, dbname, now)

    try:
        dump_database(config, dbname, dest)
        size = os.path.getsize(dest)
    except Exception as exc:
        logger.error(
            "Failed to back up %s://%s/%s: %s",
            config.driver,
            config.host,
            dbname,
            exc,
        )
        return BackupResult(
            database=dbname,
            server=config,
            local_path=dest,
            size=0,
            success=False,
            error=str(exc),
        )

    s3_uri = None
    if args.s3:
        try:
            key = format_s3_key(
                args.s3_key, config, dbname, now, dest,
            )
            s3_uri = upload_to_s3(
                dest,
                args.s3_bucket,
                key,
                endpoint_url=getattr(
                    args, "s3_endpoint_url", None
                ),
            )
        except Exception as exc:
            logger.error("Failed to upload to S3: %s", exc)
            return BackupResult(
                database=dbname,
                server=config,
                local_path=dest,
                size=size,
                success=False,
                error=f"S3 upload failed: {exc}",
            )

    return BackupResult(
        database=dbname,
        server=config,
        local_path=dest,
        size=size,
        s3_uri=s3_uri,
    )


def _send_notifications(args, report: BackupReport) -> None:
    """Dispatch configured notifications."""
    if args.smtp:
        password = _resolve_smtp_password(args)
        try:
            send_smtp_notification(
                report=report,
                server=args.smtp_server,
                port=args.smtp_port,
                sender=args.smtp_from,
                password=password,
            )
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)

    if args.slack:
        try:
            send_slack_notification(
                report=report,
                webhook_url=args.slack_webhook_url,
            )
        except Exception as exc:
            logger.error(
                "Failed to send Slack notification: %s", exc
            )


def _resolve_smtp_password(args) -> str | None:
    """Return the SMTP password from args."""
    if getattr(args, "smtp_password", None):
        return args.smtp_password
    path = getattr(args, "smtp_password_file", None)
    if path:
        return read_password_file(path)
    return None
