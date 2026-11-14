"""Data model + snapshot loading for the logging coverage audit."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


class SnapshotError(ValueError):
    """Raised when a snapshot file is malformed."""


RESOURCE_TYPES = ("vcn", "load_balancer", "object_bucket")
MIN_RETENTION_DAYS = 30


@dataclass(frozen=True)
class LogGroup:
    ocid: str
    display_name: str
    retention_days: int
    tags: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Resource:
    ocid: str
    type: str
    display_name: str
    logging_enabled: bool
    log_group_id: str | None = None


@dataclass(frozen=True)
class Snapshot:
    log_groups: tuple
    resources: tuple

    def group_by_id(self, ocid: str) -> LogGroup | None:
        for g in self.log_groups:
            if g.ocid == ocid:
                return g
        return None


def load_snapshot(path: str) -> Snapshot:
    with open(path, "r", encoding="utf-8") as fh:
        try:
            raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise SnapshotError(f"{path}: not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise SnapshotError(f"{path}: top level must be an object")
    groups_raw = raw.get("log_groups", [])
    resources_raw = raw.get("resources", [])
    if not isinstance(groups_raw, list) or not isinstance(resources_raw, list):
        raise SnapshotError(f"{path}: 'log_groups' and 'resources' must be lists")
    groups = []
    for i, g in enumerate(groups_raw):
        where = f"log_groups[{i}]"
        for req in ("ocid", "display_name", "retention_days"):
            if req not in g:
                raise SnapshotError(f"{where}: missing required field {req!r}")
        if not isinstance(g["retention_days"], int) or g["retention_days"] < 0:
            raise SnapshotError(f"{where}: retention_days must be a non-negative integer")
        groups.append(
            LogGroup(
                ocid=g["ocid"],
                display_name=g["display_name"],
                retention_days=g["retention_days"],
                tags=g.get("tags", {}) or {},
            )
        )
    resources = []
    for i, r in enumerate(resources_raw):
        where = f"resources[{i}]"
        for req in ("ocid", "type", "display_name", "logging_enabled"):
            if req not in r:
                raise SnapshotError(f"{where}: missing required field {req!r}")
        if r["type"] not in RESOURCE_TYPES:
            raise SnapshotError(f"{where}: unknown type {r['type']!r} (expected one of {RESOURCE_TYPES})")
        resources.append(
            Resource(
                ocid=r["ocid"],
                type=r["type"],
                display_name=r["display_name"],
                logging_enabled=bool(r["logging_enabled"]),
                log_group_id=r.get("log_group_id"),
            )
        )
    return Snapshot(log_groups=tuple(groups), resources=tuple(resources))
