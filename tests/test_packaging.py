"""BEFORE.md, problems in the code: unpinned dependencies, and no
Dockerfile, .env.example or README."""
import os
import re

import pytest

from tests.helpers import ROOT


def read(name):
    return open(os.path.join(ROOT, name), encoding="utf-8").read()


@pytest.mark.parametrize("name", ["requirements.txt", "requirements-dev.txt"])
def test_every_dependency_is_pinned_to_an_exact_version(name):
    for line in read(name).splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-r "):
            continue
        assert re.match(r"^[A-Za-z0-9_.-]+==[0-9][^ ;]*(\s*;.*)?$", line), f"not pinned: {line}"


def test_runtime_dependencies_do_not_include_test_tools():
    runtime = read("requirements.txt").lower()
    assert "pytest" not in runtime
    assert "httpx" not in runtime


def test_dockerfile_runs_migrations_then_the_app_as_a_normal_user():
    dockerfile = read("Dockerfile")
    assert re.search(r"^USER (?!root)\w+", dockerfile, re.M)
    assert "alembic upgrade head && exec python main.py" in dockerfile


@pytest.mark.parametrize("name", ["README.md", ".env.example", "Dockerfile", ".dockerignore"])
def test_project_files_exist(name):
    assert os.path.isfile(os.path.join(ROOT, name))


def test_secrets_and_local_files_stay_out_of_the_image():
    ignored = read(".dockerignore").split()
    for name in (".env", ".venv", ".git", "*.db"):
        assert name in ignored
