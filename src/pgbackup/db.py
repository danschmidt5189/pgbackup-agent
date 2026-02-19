"""Database URL parsing and operations."""

import os
import subprocess
from urllib.parse import parse_qs, urlparse

from pgbackup.models import DatabaseConfig

DEFAULT_PORTS = {
    "postgres": 5432,
    "mariadb": 3306,
}

SYSTEM_DATABASES = {
    "postgres": {"template0", "template1", "postgres"},
    "mariadb": {
        "information_schema",
        "mysql",
        "performance_schema",
        "sys",
    },
}


def parse_db_url(url: str) -> DatabaseConfig:
    """Parse a database URL into a DatabaseConfig.

    URL format: driver://user:pass@host:port?option=val&...
    Special query param ``password_file`` is consumed and used to
    read the password from the given file path.
    """
    parsed = urlparse(url)
    driver = parsed.scheme
    if driver not in DEFAULT_PORTS:
        raise ValueError(f"Unsupported database driver: {driver}")

    username = parsed.username or ""
    password = parsed.password or ""
    host = parsed.hostname or "localhost"
    port = parsed.port or DEFAULT_PORTS[driver]

    query_params = parse_qs(parsed.query, keep_blank_values=True)
    options = {k: v[0] for k, v in query_params.items()}

    password_file = options.pop("password_file", None)
    if password_file:
        password = read_password_file(password_file)

    return DatabaseConfig(
        driver=driver,
        username=username,
        password=password,
        host=host,
        port=port,
        options=options,
    )


def read_password_file(path: str) -> str:
    """Read and strip a password from a file."""
    with open(path) as f:
        return f.read().strip()


def list_databases(config: DatabaseConfig) -> list[str]:
    """List non-system databases on the given server."""
    if config.driver == "postgres":
        return _list_postgres_databases(config)
    return _list_mariadb_databases(config)


def _list_postgres_databases(
    config: DatabaseConfig,
) -> list[str]:
    """List user databases on a Postgres server."""
    env = os.environ.copy()
    if config.password:
        env["PGPASSWORD"] = config.password

    result = subprocess.run(
        [
            "psql",
            "-h", config.host,
            "-p", str(config.port),
            "-U", config.username,
            "-t", "-A",
            "-c",
            "SELECT datname FROM pg_catalog.pg_database "
            "WHERE datistemplate = false ORDER BY datname",
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    system_dbs = SYSTEM_DATABASES["postgres"]
    return [
        line.strip()
        for line in result.stdout.strip().splitlines()
        if line.strip() and line.strip() not in system_dbs
    ]


def _list_mariadb_databases(
    config: DatabaseConfig,
) -> list[str]:
    """List user databases on a MariaDB server."""
    env = os.environ.copy()
    if config.password:
        env["MYSQL_PWD"] = config.password

    result = subprocess.run(
        [
            "mariadb",
            "-h", config.host,
            "-P", str(config.port),
            "-u", config.username,
            "--skip-column-names",
            "-e", "SHOW DATABASES",
        ],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    system_dbs = SYSTEM_DATABASES["mariadb"]
    return [
        line.strip()
        for line in result.stdout.strip().splitlines()
        if line.strip() and line.strip() not in system_dbs
    ]


def dump_database(
    config: DatabaseConfig,
    dbname: str,
    dest: str,
) -> None:
    """Dump a single database to the given destination path."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    if config.driver == "postgres":
        _dump_postgres(config, dbname, dest)
    else:
        _dump_mariadb(config, dbname, dest)


def _dump_postgres(
    config: DatabaseConfig,
    dbname: str,
    dest: str,
) -> None:
    """Dump a Postgres database using pg_dump."""
    env = os.environ.copy()
    if config.password:
        env["PGPASSWORD"] = config.password

    with open(dest, "wb") as f:
        subprocess.run(
            [
                "pg_dump",
                "-h", config.host,
                "-p", str(config.port),
                "-U", config.username,
                "-Fc",
                dbname,
            ],
            stdout=f,
            stderr=subprocess.PIPE,
            check=True,
            env=env,
        )


def _dump_mariadb(
    config: DatabaseConfig,
    dbname: str,
    dest: str,
) -> None:
    """Dump a MariaDB database using mariadb-dump."""
    env = os.environ.copy()
    if config.password:
        env["MYSQL_PWD"] = config.password

    with open(dest, "wb") as f:
        subprocess.run(
            [
                "mariadb-dump",
                "-h", config.host,
                "-P", str(config.port),
                "-u", config.username,
                "--single-transaction",
                dbname,
            ],
            stdout=f,
            stderr=subprocess.PIPE,
            check=True,
            env=env,
        )
