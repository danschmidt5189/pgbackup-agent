"""Command-line interface for pgbackup."""

import argparse
import logging
import sys

from pgbackup.backup import run_backup


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="pgbackup",
        description=(
            "Backup utility for Postgres and MariaDB databases."
        ),
    )

    parser.add_argument(
        "--db",
        action="append",
        dest="databases",
        metavar="URL",
        help=(
            "Database URL in the form "
            "driver://user:pass@host:port?opt=val. "
            "May be specified multiple times."
        ),
    )
    parser.add_argument(
        "--dest",
        help=(
            "Destination path template. Supports {driver}, "
            "{dbhost}, {dbname}, {now:fmt}, and query params."
        ),
    )

    # --- S3 options ---
    s3 = parser.add_argument_group("S3 options")
    s3.add_argument(
        "--s3",
        action="store_true",
        default=False,
        help="Enable S3 upload.",
    )
    s3.add_argument(
        "--s3-bucket",
        metavar="BUCKET",
        help="S3 bucket name.",
    )
    s3.add_argument(
        "--s3-key",
        metavar="KEY",
        help=(
            "S3 key template. Supports all --dest variables "
            "plus {filepath}, {filename}, {filedir}."
        ),
    )
    s3.add_argument(
        "--s3-endpoint-url",
        metavar="URL",
        help="Custom S3 endpoint (for MinIO, etc.).",
    )

    # --- SMTP options ---
    smtp = parser.add_argument_group("SMTP options")
    smtp.add_argument(
        "--smtp",
        action="store_true",
        default=False,
        help="Enable SMTP email notification.",
    )
    smtp.add_argument(
        "--smtp-server",
        metavar="HOST",
        help="SMTP server hostname.",
    )
    smtp.add_argument(
        "--smtp-port",
        type=int,
        default=587,
        metavar="PORT",
        help="SMTP server port (default: 587).",
    )
    smtp.add_argument(
        "--smtp-from",
        metavar="EMAIL",
        help="Sender/recipient email address.",
    )
    smtp.add_argument(
        "--smtp-password",
        metavar="PASSWORD",
        help="SMTP password.",
    )
    smtp.add_argument(
        "--smtp-password-file",
        metavar="FILE",
        help="Path to file containing the SMTP password.",
    )

    # --- Slack options ---
    slack = parser.add_argument_group("Slack options")
    slack.add_argument(
        "--slack",
        action="store_true",
        default=False,
        help="Enable Slack notification.",
    )
    slack.add_argument(
        "--slack-webhook-url",
        metavar="URL",
        help="Slack incoming webhook URL.",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    """Entry point for the ``pgbackup`` command."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.databases:
        parser.print_help()
        sys.exit(0)

    if not args.dest:
        parser.error(
            "--dest is required when --db is specified"
        )

    if args.s3 and not args.s3_bucket:
        parser.error(
            "--s3-bucket is required when --s3 is enabled"
        )

    if args.s3 and not args.s3_key:
        parser.error(
            "--s3-key is required when --s3 is enabled"
        )

    if args.smtp and not args.smtp_server:
        parser.error(
            "--smtp-server is required when --smtp is enabled"
        )

    if args.smtp and not args.smtp_from:
        parser.error(
            "--smtp-from is required when --smtp is enabled"
        )

    if args.slack and not args.slack_webhook_url:
        parser.error(
            "--slack-webhook-url is required "
            "when --slack is enabled"
        )

    report = run_backup(args)
    sys.exit(0 if report.success else 1)
