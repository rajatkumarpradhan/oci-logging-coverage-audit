import unittest

from logging_audit.model import LogGroup, Resource, Snapshot
from logging_audit.rules import (
    exit_code,
    rule_default_group,
    rule_logging_disabled,
    rule_short_retention,
    rule_unowned_group,
    run_all,
)


def group(name="app-logs", retention=90, tags=None, ocid="lg1"):
    return LogGroup(ocid=ocid, display_name=name, retention_days=retention, tags={"owner": "team"} if tags is None else tags)


def resource(name="r1", enabled=True, group_id="lg1", rtype="vcn"):
    return Resource(ocid="oc1.x." + name, type=rtype, display_name=name,
                    logging_enabled=enabled, log_group_id=group_id)


class TestLog001Disabled(unittest.TestCase):
    def test_fires_on_disabled(self):
        snap = Snapshot(log_groups=(), resources=(resource(enabled=False),))
        out = rule_logging_disabled(snap)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "HIGH")

    def test_quiet_when_enabled(self):
        snap = Snapshot(log_groups=(group(),), resources=(resource(),))
        self.assertEqual(rule_logging_disabled(snap), [])


class TestLog002Retention(unittest.TestCase):
    def test_fires_under_30(self):
        snap = Snapshot(log_groups=(group(retention=7),), resources=())
        out = rule_short_retention(snap)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_boundary_30_is_ok(self):
        snap = Snapshot(log_groups=(group(retention=30),), resources=())
        self.assertEqual(rule_short_retention(snap), [])


class TestLog003DefaultGroup(unittest.TestCase):
    def test_fires_on_default_group(self):
        snap = Snapshot(
            log_groups=(group(name="Default Log Group"),),
            resources=(resource(),),
        )
        out = rule_default_group(snap)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_case_insensitive_name_match(self):
        snap = Snapshot(
            log_groups=(group(name="DEFAULT LOG GROUP"),),
            resources=(resource(),),
        )
        self.assertEqual(len(rule_default_group(snap)), 1)

    def test_skips_unknown_group_reference(self):
        snap = Snapshot(log_groups=(), resources=(resource(group_id="lg-missing"),))
        self.assertEqual(rule_default_group(snap), [])

    def test_skips_disabled_resource(self):
        snap = Snapshot(
            log_groups=(group(name="Default Log Group"),),
            resources=(resource(enabled=False),),
        )
        self.assertEqual(rule_default_group(snap), [])


class TestLog004Unowned(unittest.TestCase):
    def test_fires_without_owner(self):
        snap = Snapshot(log_groups=(group(tags={}),), resources=())
        self.assertEqual(len(rule_unowned_group(snap)), 1)

    def test_blank_owner_counts_as_missing(self):
        snap = Snapshot(log_groups=(group(tags={"owner": "  "}),), resources=())
        self.assertEqual(len(rule_unowned_group(snap)), 1)


class TestAggregation(unittest.TestCase):
    def test_exit_code_2_on_high(self):
        snap = Snapshot(log_groups=(), resources=(resource(enabled=False),))
        self.assertEqual(exit_code(run_all(snap)), 2)

    def test_exit_code_1_on_medium_only(self):
        snap = Snapshot(log_groups=(group(retention=7),), resources=())
        self.assertEqual(exit_code(run_all(snap)), 1)

    def test_exit_code_0_when_clean(self):
        snap = Snapshot(log_groups=(group(),), resources=(resource(),))
        self.assertEqual(exit_code(run_all(snap)), 0)

    def test_sorted_high_first(self):
        snap = Snapshot(
            log_groups=(group(name="Default Log Group", retention=7, tags={}),),
            resources=(resource(enabled=False),),
        )
        findings = run_all(snap)
        self.assertEqual(findings[0].severity, "HIGH")
        self.assertEqual(findings[-1].severity, "LOW")


if __name__ == "__main__":
    unittest.main()
