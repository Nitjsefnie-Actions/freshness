"""The branch checks' inputs from the calling step: required checks and the default branch."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_required_check_is_a_refusal(monkeypatch):
    monkeypatch.setenv('FRESHNESS_REQUIRED_CHECKS', ' \n')
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    done = subprocess.run([sys.executable, str(ROOT / 'scripts/ci/gate_base_freshness.py')],
                          capture_output=True, text=True, check=False)
    assert done.returncode != 0
    assert 'names no required check' in done.stdout + done.stderr


def test_the_calling_step_names_the_default_branch(monkeypatch):
    import importlib.util
    monkeypatch.setenv('FRESHNESS_DEFAULT_BRANCH', 'master')
    spec = importlib.util.spec_from_file_location(
        'gate_base_freshness', ROOT / 'scripts/ci/gate_base_freshness.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.BASE_BRANCH == 'master'
