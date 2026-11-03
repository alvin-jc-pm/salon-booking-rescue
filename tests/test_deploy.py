"""BEFORE.md rows 1 and 3, on the real host. The Railway settings that make
it wait for /health live on the service itself (see HANDOVER.md), so this
checks the recorded run against the live deployment."""
import os

from tests.helpers import ROOT


def test_recorded_run_against_the_live_deployment_passed():
    results = open(os.path.join(ROOT, "evidence", "after_results.txt"), encoding="utf-8").read()
    assert "railway.app" in results
    assert "[FAIL]" not in results
    assert "16 of 16 checks passed." in results
