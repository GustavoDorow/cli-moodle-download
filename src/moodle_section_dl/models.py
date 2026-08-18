from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Activity:
    name: str
    url: str


@dataclass(frozen=True)
class DownloadedFile:
    activity: str
    source_url: str
    path: Path
    size: int


@dataclass(frozen=True)
class SkippedActivity:
    name: str
    url: str
    reason: str


@dataclass(frozen=True)
class DownloadReport:
    files: tuple[DownloadedFile, ...]
    skipped: tuple[SkippedActivity, ...]
