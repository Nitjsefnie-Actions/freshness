"""CI wiring of the freshness check: the actionlint job runs it, and the audit reads the action.

The step's own run-block text is executed against the real action.yml with
nothing faked: the wrapper the actionlint job generates is derived from the
shipped action, never retyped.
"""
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _workflow(name):
    path = ROOT / '.github/workflows' / name
    assert path.is_file(), f'missing workflow: {name}'
    return yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader)


def _shipped_action_pin(action):
    """Return the one revision every shipped workflow pins ``action`` at.

    The workflows are the source of truth for which release is in use, so a
    dependency upgrade edits YAML only; these tests check that the pins agree
    and are immutable, not which commit they name.
    """
    pins = set()
    for path in sorted((ROOT / '.github/workflows').glob('*.yml')):
        for job in _workflow(path.name)['jobs'].values():
            for step in job.get('steps', []):
                if step.get('uses', '').startswith(action + '@'):
                    pins.add(step['uses'].split('@', 1)[1])
    assert len(pins) == 1, (
        f'{action} must be pinned at exactly one revision across the '
        f'workflows, not {sorted(pins)}')
    return pins.pop()


def _named_run(steps, name):
    runs = [step['run'] for step in steps if step.get('name') == name]
    assert len(runs) == 1, f'expected exactly one step named {name!r}'
    return runs[0]


def test_workflow_audit_includes_composite_metadata(tmp):
    del tmp
    workflow = _workflow('actionlint.yml')
    assert workflow['permissions'] == {'contents': 'read'}
    assert workflow['on']['push'] == {'branches': ['main']}
    steps = workflow['jobs']['actionlint']['steps']
    # The ported checks follow setup-python directly, on the interpreter it
    # put on PATH; a stale, mis-scoped head never pays for the installs.
    setup = next(index for index, step in enumerate(steps)
                 if step.get('uses', '').startswith('actions/setup-python@'))
    checks = ['Check no tracked file carries a merge-conflict marker',
              "Require this head to carry main's gate-defining commits"]
    ported = steps[setup + 1:setup + 3]
    assert [step.get('name') for step in ported] == checks, 'must follow setup-python directly'
    assert [set(s) for s in ported] == [{'name', 'run'}, {'name', 'env', 'run'}]
    marker = ported[0]['run']
    assert "git grep -nI -E '^(<{7}( |$)|>{7}( |$)|={7}$)' -- ." in marker
    assert '${{' not in marker
    assert ported[1]['run'].endswith(
        '\nexport FRESHNESS_REQUIRED_CHECKS\npython3 scripts/ci/gate_base_freshness.py\n')

    def _run_of(name):
        return next(step['run'] for step in steps if step.get('name') == name)

    actionlint_run = _run_of('actionlint')
    assert ('./actionlint -color .github/workflows/*.yml '
            '"$RUNNER_TEMP/freshness-action-workflow.yml"') in actionlint_run, (
        'the audit must read the generated wrapper, not only the workflows')
    assert "python - <<'PYTHON'" in actionlint_run, (
        'the wrapper is generated in the step, never a committed copy')
    assert 'zizmor --no-progress action.yml .github/workflows/' in _run_of('zizmor')


# The actionlint step derives its lint input from action.yml, never a
# hand-kept copy: the step's own generation code is executed against the
# real action.yml and the wrapper it writes is pinned here.
def test_the_generated_wrapper_mirrors_the_composite_action(tmp):
    step = _named_run(_workflow('actionlint.yml')['jobs']['actionlint']['steps'],
                      'actionlint')
    heredoc = step.split("python - <<'PYTHON'\n", 1)[1].split('\nPYTHON\n', 1)[0]
    staging = Path(tmp) / 'stage'
    staging.mkdir()
    (staging / 'action.yml').write_text(
        (ROOT / 'action.yml').read_text(encoding='utf-8'), encoding='utf-8')
    wrapper_dir = Path(tmp) / 'runner-temp'
    wrapper_dir.mkdir()
    environment = dict(os.environ)
    environment['RUNNER_TEMP'] = str(wrapper_dir)
    subprocess.run([sys.executable, '-c', heredoc], cwd=staging,
                   env=environment, check=True, capture_output=True, text=True)
    loader = yaml.BaseLoader
    action = yaml.load((staging / 'action.yml').read_text(encoding='utf-8'),
                       Loader=loader)
    wrapper = yaml.load(
        (wrapper_dir / 'freshness-action-workflow.yml').read_text(encoding='utf-8'),
        Loader=loader)
    inputs = {name: {'description': spec['description'], 'type': 'string'}
              for name, spec in action['inputs'].items()}
    assert wrapper['on'] == {'workflow_dispatch': {'inputs': inputs}}
    assert wrapper['permissions'] == {}
    assert wrapper['jobs']['action']['runs-on'] == 'ubuntu-latest'
    steps = wrapper['jobs']['action']['steps']
    assert steps[0] == {'uses': './'}
    assert steps[1:] == action['runs']['steps'], (
        'the wrapper carries the composite steps verbatim so actionlint '
        'reads the action, not a retyped copy')


def test_the_freshness_files_are_shipped():
    required = [
        'action.yml', 'SECURITY.md', '.github/workflows/actionlint.yml',
        '.github/workflows/pr-gate.yml', '.gitleaks.toml', 'requirements-actionlint.txt',
        'scripts/ci/gate_base_freshness.py', 'scripts/ci/freshness_reach.py',
        'scripts/ci/freshness_workflows.py', 'tests/test_gate_base_freshness.py',
        'tests/test_freshness_reach.py', 'tests/test_freshness_required_checks.py']
    ignore = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
    assert ignore[0] == '*'
    for name in required:
        assert (ROOT / name).is_file(), f'missing repository policy: {name}'
        assert f'!{name}' in ignore, f'{name} must be shipped'
    security = (ROOT / 'SECURITY.md').read_text(encoding='utf-8')
    assert 'https://github.com/Nitjsefnie-Actions/freshness/security/advisories/new' in security
    assert '[SECURITY.md](SECURITY.md)' in (ROOT / 'README.md').read_text(encoding='utf-8')
