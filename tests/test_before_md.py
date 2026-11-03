"""Every failure in BEFORE.md, replayed against a real server process
started the way a host starts it, with PORT set."""
import os
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

from tests.helpers import ROOT

sys.path.insert(0, os.path.join(ROOT, "evidence"))
import after_check  # noqa: E402


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def base_url(tmp_path_factory):
    port = free_port()
    env = dict(os.environ, PORT=str(port), HOST="127.0.0.1")
    server = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "main.py")],
        cwd=tmp_path_factory.mktemp("server"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            urllib.request.urlopen(base + "/health", timeout=2)
            break
        except OSError:
            time.sleep(0.3)
    yield base
    server.terminate()
    server.wait(timeout=10)


@pytest.fixture(scope="module")
def results(base_url):
    return after_check.run(base_url, os.environ["ADMIN_API_KEY"])


def test_every_before_md_failure_is_fixed(results):
    text, ok = after_check.report(results)
    assert ok, text


def test_every_before_md_row_is_covered(results):
    labels = " ".join(r[0] for r in results)
    for row in ("1.", "3.", "5.", "8.", "9.", "10.", "11.", "12.", "13.", "14."):
        assert row in labels
