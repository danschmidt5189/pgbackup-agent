"""Tests for pgbackup.formatting."""

from datetime import datetime, timezone

from pgbackup.formatting import (
    _build_context,
    format_dest,
    format_s3_key,
)
from pgbackup.models import DatabaseConfig


NOW = datetime(2026, 2, 18, 23, 45, 52, tzinfo=timezone.utc)

CFG = DatabaseConfig(
    driver="postgres",
    username="u",
    password="p",
    host="myhost",
    port=5432,
    options={"env": "production"},
)


class TestFormatDest:
    """Destination path template formatting."""

    def test_basic_interpolation(self):
        tpl = "/backup/{driver}/{dbhost}/{dbname}.dump"
        result = format_dest(tpl, CFG, "mydb", NOW)
        assert result == "/backup/postgres/myhost/mydb.dump"

    def test_now_formatting(self):
        tpl = "/backup/{dbname}-{now:%Y-%m-%d}.dump"
        result = format_dest(tpl, CFG, "mydb", NOW)
        assert result == "/backup/mydb-2026-02-18.dump"

    def test_option_interpolation(self):
        tpl = "/backup/{env}/{dbname}.dump"
        result = format_dest(tpl, CFG, "mydb", NOW)
        assert result == "/backup/production/mydb.dump"

    def test_full_example(self):
        """Matches the example from the instructions."""
        tpl = (
            "/srv/pgbackup/{env}/{dbhost}/"
            "{dbname}-{now:%Y-%m-%d}.dump"
        )
        result = format_dest(tpl, CFG, "boulderers", NOW)
        assert result == (
            "/srv/pgbackup/production/myhost/"
            "boulderers-2026-02-18.dump"
        )


class TestFormatS3Key:
    """S3 key template formatting."""

    def test_basic_s3_key(self):
        tpl = "{driver}/{filename}"
        result = format_s3_key(
            tpl, CFG, "mydb", NOW,
            "/backups/mydb-2026-02-18.dump",
        )
        assert result == "postgres/mydb-2026-02-18.dump"

    def test_filepath_variables(self):
        tpl = "{filedir}/{filename}"
        result = format_s3_key(
            tpl, CFG, "mydb", NOW,
            "/backups/sub/mydb.dump",
        )
        assert result == "/backups/sub/mydb.dump"

    def test_full_s3_example(self):
        tpl = "{env}/{dbhost}/{filename}"
        result = format_s3_key(
            tpl, CFG, "boulderers", NOW,
            "/srv/pgbackup/production/myhost/"
            "boulderers-2026-02-18.dump",
        )
        assert result == (
            "production/myhost/boulderers-2026-02-18.dump"
        )


class TestBuildContext:
    """Context dictionary construction."""

    def test_builtins_override_options(self):
        """Built-in vars take precedence over options."""
        cfg = DatabaseConfig(
            driver="postgres",
            username="u",
            password="p",
            host="h",
            port=5432,
            options={"driver": "should-be-overridden"},
        )
        ctx = _build_context(cfg, "db", NOW)
        assert ctx["driver"] == "postgres"

    def test_options_merged(self):
        ctx = _build_context(CFG, "db", NOW)
        assert ctx["env"] == "production"
        assert ctx["dbname"] == "db"
