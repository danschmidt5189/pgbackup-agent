# PGBackup

Dockerized backup utility for **Postgres** and **MariaDB** databases. Backups are stored on the local filesystem and optionally uploaded to S3-compatible storage. Notifications can be sent via SMTP or Slack.

## Features

- Back up multiple Postgres and MariaDB servers in a single run
- Automatic database discovery (system databases are excluded)
- Flexible destination paths via template interpolation
- S3 upload to any S3-compatible storage (AWS, MinIO, etc.)
- Email notifications (SMTP with STARTTLS or implicit TLS)
- Slack notifications via incoming webhooks
- Docker Swarm–friendly `password_file` support for secrets

## Quick Start

```sh
docker pull ghcr.io/orgname/pgbackup:latest

docker run --rm ghcr.io/orgname/pgbackup:latest pgbackup \
  --db postgres://user:pass@dbhost:5432?env=production \
  --dest '/backups/{env}/{dbhost}/{dbname}-{now:%Y-%m-%d}.dump'
```

## Usage

```sh
pgbackup \
  --db postgres://user@pghost?password_file=/run/secrets/pgpass&env=production \
  --db mariadb://user@mdbhost?password_file=/run/secrets/mdbpass&env=staging \
  --dest '/srv/pgbackup/{env}/{dbhost}/{dbname}-{now:%Y-%m-%d}.dump' \
  --s3 \
  --s3-bucket my-bucket \
  --s3-key '{env}/{dbhost}/{filename}' \
  --smtp \
  --smtp-server smtp.gmail.com \
  --smtp-port 587 \
  --smtp-from alerts@example.com \
  --smtp-password-file /run/secrets/mail_password
```

### Database URLs

```
driver://user:pass@host:port?option=value&...
```

| Driver     | Default Port | Dump Tool       |
|------------|--------------|-----------------|
| `postgres` | 5432         | `pg_dump -Fc`   |
| `mariadb`  | 3306         | `mariadb-dump`  |

Special query parameters:

- **`password_file`** — Path to a file containing the password (trimmed). Preferred over inline passwords for security and Docker Swarm interoperability.

All other query parameters are available as template variables.

### Template Variables

Available in `--dest` and `--s3-key`:

| Variable   | Description                                    |
|------------|------------------------------------------------|
| `{driver}` | Database driver (`postgres` or `mariadb`)      |
| `{dbhost}` | Hostname of the database server                |
| `{dbname}` | Name of the database being backed up           |
| `{now}`    | Current time — supports format specs, e.g. `{now:%Y-%m-%d}` |
| `{*}`      | Any query parameter from the DB URL (e.g. `{env}`) |

`--s3-key` additionally supports:

| Variable     | Description                        |
|--------------|------------------------------------|
| `{filepath}` | Full local path of the dump file   |
| `{filename}` | Basename of the dump file          |
| `{filedir}`  | Directory of the dump file         |

### CLI Reference

| Flag                  | Description                            |
|-----------------------|----------------------------------------|
| `--db URL`            | Database URL (repeatable)              |
| `--dest TEMPLATE`     | Local destination path template        |
| `--s3`                | Enable S3 upload                       |
| `--s3-bucket BUCKET`  | S3 bucket name                         |
| `--s3-key TEMPLATE`   | S3 object key template                 |
| `--s3-endpoint-url`   | Custom S3 endpoint (MinIO, etc.)       |
| `--smtp`              | Enable email notifications             |
| `--smtp-server HOST`  | SMTP server hostname                   |
| `--smtp-port PORT`    | SMTP port (default: 587)               |
| `--smtp-from EMAIL`   | Sender and recipient email address     |
| `--smtp-password PW`  | SMTP password                          |
| `--smtp-password-file`| Path to file containing SMTP password  |
| `--slack`             | Enable Slack notifications             |
| `--slack-webhook-url` | Slack incoming webhook URL             |

## Development

### Prerequisites

- Docker and Docker Compose

### Build & Test

```sh
docker compose up --build --wait app
docker compose exec app ruff check src/ tests/
docker compose exec app pytest
```

The test suite runs against:

- Postgres 16, 17, 18
- MariaDB 10.11, 11.4, 11.8

along with MinIO (S3 mock) and Mailpit (SMTP mock).

### Project Structure

```
src/pgbackup/
├── __init__.py       # Package metadata
├── __main__.py       # python -m pgbackup support
├── cli.py            # Argument parsing and entry point
├── backup.py         # Orchestration (discover → dump → upload → notify)
├── db.py             # URL parsing, database listing, dumping
├── formatting.py     # Template interpolation
├── storage.py        # S3 upload
├── notify.py         # SMTP and Slack notifications
└── models.py         # Data classes (DatabaseConfig, BackupResult, BackupReport)
```

### Requirements

- 100% test coverage enforced by pytest-cov
- PEP 8 enforced by ruff
- All tests must pass before merge

## License

[MIT](LICENSE)
