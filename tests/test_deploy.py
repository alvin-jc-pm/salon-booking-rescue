"""BEFORE.md rows 1 and 3, on the real host: Railway must reach the app on
the port it chooses and wait for /health before sending it traffic."""
import json
import os

from tests.helpers import ROOT


def test_railway_builds_the_dockerfile_and_checks_health():
    config = json.load(open(os.path.join(ROOT, "railway.json"), encoding="utf-8"))
    assert config["build"]["builder"] == "DOCKERFILE"
    assert config["deploy"]["healthcheckPath"] == "/health"
    assert config["deploy"]["restartPolicyType"] == "ON_FAILURE"


def test_recorded_run_against_the_live_deployment_passed():
    results = open(os.path.join(ROOT, "evidence", "after_results.txt"), encoding="utf-8").read()
    assert "railway.app" in results
    assert "[FAIL]" not in results
    assert "16 of 16 checks passed." in results
