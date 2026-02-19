# PGBackup

PGBackup is a Dockerized Python 3.14 program that creates logical backups of Postgres and MariaDB database servers. Backups are stored on the local filesystem and optionally uploaded to S3-compatible storage. Notifications describing the given backup run, indicating success/failure, size, and local and remote backup locations for each target database server and discovered database can be optionally sent via SMTP or Slack notification.

## Building and Testing

The applications is fully Dockerized, including its test environment. You can build and run the test suite like so:

```sh
docker compose up --build --wait app
docker compose exec app pytest
```

Tests run against the following databases:

- Postgres 16.12
- Postgres 17.18
- Postgres 18.2
- MariaDB 12.3
- MariaDB 11.8
- MariaDB 10.11

## Running the Program

The application revolves around the `pgbackup` utility which serves as the program's entrypoint. By default, it simply prints `--help` output. A complete example is given below:

```sh
pgbackup \
  --db driver1://user:pass@host:port?option=val1… \
  --db driver2://user:pass@host:port?option=val2… \
  --dest '/srv/pgbackup/{driver}/{option}/{host}/{dbname}-{now:%Y-%m-%d}.dump' \
  --s3 \
  --s3-bucket some-bucket \
  --s3-key '{driver}/{option}/{host}/{filename}' \
  --smtp \
  --smtp-server smtp.gmail.com \
  --smtp-port 467 \
  --smtp-from authuser@corp.com \
  --smtp-password-file /run/secrets/mail_password
```

As you can see, the `dest` and `s3-key` arguments support interpolation. The following variables are available:

- `driver`: The database driver being used, corresponding to the scheme part of the DB URL (e.g. postgres, mariadb)
- `option`: A free-form variable corresponding to the value of the named query param on the DB URL. This allows you support arbitrary destinations for a given DB URL. For example, you could set `?env=` to indicate the deployment environment (production, staging, etc.).
- `dbhost`: The hostname of the database server being backed up.
- `dbname`: The name of the database being backed up.
- `now`: The current time (using the system's timezone).

`--s3-key` also supports a few additional variables, since it comes later and acts on a given backup file:

- `filepath`: The full path to the dump being uploaded.
- `filename`: The name of the file (basename).
- `filedir`: The directory of the file (dirname).

Database URLs also support a special query param `password_file`, indicating the path to a file from which that database's password can be retrieved. The file is trimmed, so leading or trailing whitespace are not allowed. Prefer `password_file` whenever possible to help conceal your passwords, and for interoperability with Docker Swarm.

### Example

Given the following databases:

```yaml
databases:
  - driver: postgres
    host: postgres
    port: null # i.e. the default 5432
    username: pg-read-only
    options:
      env: production
      password_file: /run/secrets/pgpass
    databases:
      - boulderers
      - sport-climbers
  - driver: mariadb
    host: mariadb
    port: null # i.e. the default 3306
    username: mdb-read-only
    options:
      env: staging
      password_file: /run/secrets/mdbpass
    databases:
      - formula1
      - nascar
```

Then running this command at `Wed Feb 18 23:45:52 PST 2026`:

```sh
pgbackup \
  --db postgres://pg-read-only@postgres?password_file=/run/secrets/pgpass&env=production \
  --db mariadb://mdb-read-only@mariadb?password_file=/run/secrets/mdbpass&env=staging \
  --dest '/srv/pgbackup/{env}/{dbhost}/{dbname}-{now:%Y-%m-%d}.dump' \
  --s3 \
  --s3-bucket pgbackup \
  --s3-key '{env}/{dbhost}/{dbname}-{filename}.dump' \
  --smtp \
  --smtp-from test@megacorp.com \
  --smtp-server smtp.gmail.com \
  --smtp-password-file /run/secrets/mail_password
```

Should result in the following outputs:

```yaml
localbackups:
  - /srv/pgbackup/production/postgres/boulderers-2026-02-18.dump
  - /srv/pgbackup/production/postgres/sport-climbers-2026-02-18.dump
  - /srv/pgbackup/staging/mariadb/formula1-2026-02-18.dump
  - /srv/pgbackup/staging/mariadb/nascar-2026-02-18.dump
s3objects:
  - s3://pgbackup/production/postgres/boulderers-2026-02-18.dump
  - s3://pgbackup/production/postgres/sport-climbers-2026-02-18.dump
  - s3://pgbackup/staging/mariadb/formula1-2026-02-18.dump
  - s3://pgbackup/staging/mariadb/nascar-2026-02-18.dump
```

And a summary email sent to test@megacorp.com.

## Testing

- The required test coverage is 100%.
- All tests must pass before merging will be considered.
- Tests are run using `pytest`.
- All testing can be done locally without access to GMail or AWS S3. The included Compose file provides suitable mocks for testing purposes.
- Metaprogramming and dynamic fixtures are encouraged so long as readability and idiomatic coding styles are maintained.

## Coding Style

- Code strictly follows PEP8 standards.
- The standard is enforced by the test suite and GitHub Actions build.

## CI/CD

- Every commit is built and tested using GitHub Actions.
- The build artifact is a Docker image, which is pushed to the repo's ghcr.io registry (ghcr.io/orgname/pgbackup).
- Images built from commits are tagged as follows:
  - All images are tagged with their git short-SHA and a build ID suffix. This is the only truly immutable tag, as it cannot be rebuilt. (Doing so changes the build ID.)
  - Every image is tagged with its branch name.
  - Every image is tagged with its git short-SHA.
  - Images built from the default branch are tagged `edge` and `latest`.
- Git tags do not trigger rebuilds. Instead, the most recent image built for the target commit is tagged with the git-tag. If the git-tag follows semver, its components are broken out into additional tags with the following logic:
  - `1.2.3`: `1`, `1.2`, and `1.2.3` tags are created or updated.
  - `1.2.3-456`: `1`, `1.2`, `1.2.3`, and `1.2.3-456` tags are created or updated.
  - `1.2.3-rc1`: only the `1.2.3-rc1` tag is created or updated, due to the "rc" prefix of the latter portion of the tag indicating this is a prerelease.
