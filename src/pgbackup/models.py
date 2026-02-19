"""Data models for pgbackup."""

from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Parsed database connection configuration."""

    driver: str
    username: str
    password: str
    host: str
    port: int
    options: dict[str, str] = field(default_factory=dict)


@dataclass
class BackupResult:
    """Result of backing up a single database."""

    database: str
    server: DatabaseConfig
    local_path: str
    size: int
    s3_uri: str | None = None
    success: bool = True
    error: str | None = None


@dataclass
class BackupReport:
    """Overall backup run report."""

    results: list[BackupResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all individual backups succeeded."""
        return all(r.success for r in self.results)

    @property
    def total_size(self) -> int:
        """Total size of all successful backups in bytes."""
        return sum(r.size for r in self.results if r.success)
