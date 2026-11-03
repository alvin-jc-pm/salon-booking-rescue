"""BEFORE.md rows 1 and 3: a host could not reach the app or check its health."""
import os
import socket
import subprocess
import sys
import time
import urllib.request

from fastapi.testclient import TestClient

import main

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_health_check_returns_ok():
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_listens_on_all_interfaces_by_default():
    host, port = main.server_options({})
    assert host == "0.0.0.0"
    assert port == 8000


def test_reads_host_and_port_from_environment():
    assert main.server_options({"HOST": "127.0.0.1", "PORT": "8080"}) == ("127.0.0.1", 8080)


def test_server_started_like_a_host_answers_on_the_given_port(tmp_path):
    port = free_port()
    env = dict(os.environ, HOST="127.0.0.1", PORT=str(port))
    server = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "main.py")],
        cwd=tmp_path,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        status = None
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as r:
                    status = r.status
                    break
            except OSError:
                time.sleep(0.3)
        assert status == 200
    finally:
        server.terminate()
        server.wait(timeout=10)
