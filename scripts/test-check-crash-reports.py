#!/usr/bin/env python3
"""Exercise scripts/check-crash-reports.py on fixture .ips reports."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parent / "check-crash-reports.py"
UDID = "6794F75B-E14F-4B4C-9DC7-E9822B90EB61"


def report(name: str, *, simulated: bool, udid: str = UDID,
           bundle: str = "com.example.app.Widgets") -> tuple[str, str]:
    """An .ips file's name and text: a one-line JSON header, then the body."""
    header = {"bundleID": bundle, "bug_type": "309", "name": name}
    if simulated:
        header["is_simulated"] = 1
    body = {
        "coalitionName": f"com.apple.CoreSimulator.SimDevice.{udid}",
        "exception": {"type": "EXC_GUARD", "subtype": "GUARD_TYPE_USER"},
        "faultingThread": 0,
        "threads": [{"frames": [{"imageIndex": 0, "symbol": "_XPC_MISUSE_FAULT"}]}],
        "usedImages": [{"name": "libxpc.dylib"}],
    }
    return f"{name}.ips", json.dumps(header) + "\n" + json.dumps(body)


class CrashReportCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory(prefix="simslot-crash-reports-")
        self.addCleanup(directory.cleanup)
        self.reports = Path(directory.name)

    def write(self, name: str, text: str) -> None:
        (self.reports / name).write_text(text)

    def check(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--since", "0", "--udid", UDID,
             "--reports-dir", str(self.reports), "--settle", "0", *extra],
            capture_output=True, text=True)

    def test_a_simulated_report_is_a_note_not_a_failure(self) -> None:
        self.write(*report("ExcUserFault_ExampleWidgets-2026-11-04-093717", simulated=True))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No crash reports from this run.", result.stdout)
        self.assertIn("ExcUserFault_ExampleWidgets-2026-11-04-093717.ips", result.stderr)
        self.assertIn("simulated report", result.stderr)

    def test_a_real_crash_still_fails_beside_a_simulated_one(self) -> None:
        self.write(*report("ExcUserFault_ExampleWidgets-2026-11-04-093717", simulated=True))
        self.write(*report("ExampleWidgets-2026-11-04-093730", simulated=False))
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("1 crash report(s)", result.stdout)
        self.assertIn("ExampleWidgets-2026-11-04-093730.ips", result.stdout)
        self.assertNotIn("ExcUserFault", result.stdout)

    def test_another_simulators_report_is_ignored(self) -> None:
        self.write(*report("ExampleWidgets-elsewhere", simulated=False,
                           udid="00000000-0000-0000-0000-000000000000"))
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, "")

    def test_a_bundle_prefix_ignores_other_apps(self) -> None:
        self.write(*report("Other-2026-11-04-093730", simulated=False, bundle="com.other.app"))
        self.assertEqual(self.check().returncode, 1)
        result = self.check("--bundle-prefix", "com.example.")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("No crash reports from this run.", result.stdout)


if __name__ == "__main__":
    unittest.main()
