# oci-logging-coverage-audit

**Category: custom portfolio tool.** Pure Python command-line auditor. It does **not** wire any
built-in OCI services together - it is the *custom* project in its daily pair (the built-in
services project is `oci-ootb-dns-failover-policy-check`).

## The problem

When something breaks (or someone breaks in), the first question is "what do the logs say?" - and
too often the answer is "nothing, logging was never turned on for that VCN / load balancer /
bucket." In OCI, flow logs, access logs and audit-adjacent service logs all live in **OCI Logging**
log groups with their own retention settings, and coverage gaps stay invisible until the day you
need the data. This tool audits an **offline inventory snapshot** of resources and their logging
configuration and flags exactly where visibility is missing or weak.

## What it does

Reads a JSON snapshot (schema below, synthetic samples included) and applies four rules:

| Rule | Severity | Fires when |
| ---- | -------- | ---------- |
| LOG001 | HIGH | A resource that should emit logs (VCN flow logs, load balancer access/error logs, bucket access logs) has logging disabled. |
| LOG002 | MEDIUM | A log group's retention is under 30 days - an incident older than a month leaves no trace. |
| LOG003 | MEDIUM | A resource logs into the catch-all `Default Log Group` instead of a dedicated group (no ownership, no per-team retention). |
| LOG004 | LOW | A log group has no `owner` tag - nobody is accountable for it. |

Exit code: `2` if any HIGH finding, `1` if only MEDIUM/LOW, `0` when clean - drops into cron or a
CI gate directly.

## Run it

```bash
python -m logging_audit.cli samples/logging_messy.json   # exits 2, all 4 rules fire
python -m logging_audit.cli samples/logging_clean.json   # exits 0
```

## Test it

```bash
python -m unittest discover -s tests -v   # 18 tests, stdlib only
```

## Snapshot schema

```json
{
  "log_groups": [
    {"ocid": "ocid1.loggroup.oc1..lg1", "display_name": "network-flow-logs",
     "retention_days": 90, "tags": {"owner": "netops"}}
  ],
  "resources": [
    {"ocid": "ocid1.vcn.oc1..v1", "type": "vcn", "display_name": "prod-vcn",
     "logging_enabled": true, "log_group_id": "ocid1.loggroup.oc1..lg1"}
  ]
}
```

`type` is one of `vcn`, `load_balancer`, `object_bucket`.

## Honest limits

- **Offline only**: the snapshot is synthetic and hand-authored. Nothing here calls the OCI
  Logging API or enumerates a tenancy. Wiring a real export is future work; the rule engine would
  not change.
- 30-day retention (LOG002) and the `owner` tag (LOG004) are sensible defaults, not OCI-enforced
  policy; a real review process should make them configurable.
- Coverage is checked per resource *type* with a fixed should-log list (VCN, load balancer,
  bucket). Compute/boot-volume logging and OKE control-plane logs are not modeled.
- LOG001 flags a *candidate* gap: a resource may be intentionally unlogged (throwaway dev VCN) -
  findings are review input, not proof of misconfiguration.

## Project status

Built as a daily portfolio project. 18 unit tests, all green locally and in CI
(`.github/workflows/ci.yml`, Python 3.10/3.11/3.12). No paid services, no live cloud calls.
