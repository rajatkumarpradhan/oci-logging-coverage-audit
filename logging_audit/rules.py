"""LOG001-LOG004 rules."""

from __future__ import annotations

from dataclasses import dataclass

from .model import MIN_RETENTION_DAYS, Snapshot

DEFAULT_GROUP_NAME = "default log group"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # HIGH | MEDIUM | LOW
    subject: str   # resource or log group display name
    detail: str


def rule_logging_disabled(snapshot: Snapshot) -> list:
    """LOG001 HIGH: resource that should emit logs has logging disabled."""
    out = []
    for r in snapshot.resources:
        if not r.logging_enabled:
            out.append(
                Finding(
                    rule="LOG001",
                    severity="HIGH",
                    subject=r.display_name,
                    detail=f"{r.type} has logging disabled; there will be nothing to search when it matters",
                )
            )
    return out


def rule_short_retention(snapshot: Snapshot) -> list:
    """LOG002 MEDIUM: log group retention below MIN_RETENTION_DAYS."""
    out = []
    for g in snapshot.log_groups:
        if g.retention_days < MIN_RETENTION_DAYS:
            out.append(
                Finding(
                    rule="LOG002",
                    severity="MEDIUM",
                    subject=g.display_name,
                    detail=f"retention is {g.retention_days} days (< {MIN_RETENTION_DAYS}); older incidents leave no trace",
                )
            )
    return out


def rule_default_group(snapshot: Snapshot) -> list:
    """LOG003 MEDIUM: resource logs into the catch-all default log group."""
    out = []
    for r in snapshot.resources:
        if not r.logging_enabled or not r.log_group_id:
            continue
        g = snapshot.group_by_id(r.log_group_id)
        if g is None:
            continue  # unknown group id is an export gap, not this rule's finding
        if g.display_name.strip().lower() == DEFAULT_GROUP_NAME:
            out.append(
                Finding(
                    rule="LOG003",
                    severity="MEDIUM",
                    subject=r.display_name,
                    detail=(
                        f"logs into {g.display_name!r} instead of a dedicated group; "
                        f"no per-team ownership or retention"
                    ),
                )
            )
    return out


def rule_unowned_group(snapshot: Snapshot) -> list:
    """LOG004 LOW: log group with no owner tag."""
    out = []
    for g in snapshot.log_groups:
        owner = str(g.tags.get("owner", "")).strip()
        if not owner:
            out.append(
                Finding(
                    rule="LOG004",
                    severity="LOW",
                    subject=g.display_name,
                    detail="log group has no 'owner' tag; nobody is accountable for it",
                )
            )
    return out


ALL_RULES = (
    rule_logging_disabled,
    rule_short_retention,
    rule_default_group,
    rule_unowned_group,
)

_SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def run_all(snapshot: Snapshot) -> list:
    findings = []
    for rule in ALL_RULES:
        findings.extend(rule(snapshot))
    findings.sort(key=lambda f: (_SEVERITY_RANK[f.severity], f.rule, f.subject))
    return findings


def exit_code(findings: list) -> int:
    if any(f.severity == "HIGH" for f in findings):
        return 2
    if findings:
        return 1
    return 0
