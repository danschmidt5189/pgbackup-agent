"""Template string interpolation for backup paths."""

import os
from datetime import datetime

from pgbackup.models import DatabaseConfig


def format_dest(
    template: str,
    config: DatabaseConfig,
    dbname: str,
    now: datetime,
) -> str:
    """Format a destination path template.

    Available variables: ``{driver}``, ``{dbhost}``, ``{dbname}``,
    ``{now:format}``, plus any query-parameter options from the
    database URL.
    """
    context = _build_context(config, dbname, now)
    return template.format_map(context)


def format_s3_key(
    template: str,
    config: DatabaseConfig,
    dbname: str,
    now: datetime,
    filepath: str,
) -> str:
    """Format an S3 key template.

    Supports all variables from :func:`format_dest` plus
    ``{filepath}``, ``{filename}``, and ``{filedir}``.
    """
    context = _build_context(config, dbname, now)
    context["filepath"] = filepath
    context["filename"] = os.path.basename(filepath)
    context["filedir"] = os.path.dirname(filepath)
    return template.format_map(context)


def _build_context(
    config: DatabaseConfig,
    dbname: str,
    now: datetime,
) -> dict:
    """Build the interpolation context dictionary.

    Query-parameter options are included but cannot override the
    built-in variables (driver, dbhost, dbname, now).
    """
    context: dict = dict(config.options)
    context.update(
        {
            "driver": config.driver,
            "dbhost": config.host,
            "dbname": dbname,
            "now": now,
        }
    )
    return context
