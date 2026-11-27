"""Locate the Bash that GitHub Actions runs `shell: bash` steps with."""
import os
import shutil
from pathlib import Path


def _action_bash(*, windows=None, environment=None):
    environment = os.environ if environment is None else environment
    windows = os.name == 'nt' if windows is None else windows
    path = environment.get('PATH', '')
    if not windows:
        bash = shutil.which('bash', path=path)
        if bash is None:
            raise RuntimeError('Bash was not found on PATH for action tests')
        return bash

    # Actions uses Git for Windows for `shell: bash`. A plain Windows PATH
    # lookup can instead select System32's WSL shim, which is a different shell.
    roots = []
    git = shutil.which('git.exe', path=path)
    if git is not None:
        directory = Path(git).resolve().parent
        if directory.name.casefold() in ('cmd', 'bin'):
            root = directory.parent
            if root.name.casefold() in ('mingw32', 'mingw64'):
                root = root.parent
            roots.append(root)
    for key in ('ProgramFiles', 'ProgramW6432', 'ProgramFiles(x86)'):
        if environment.get(key):
            roots.append(Path(environment[key]) / 'Git')
    if environment.get('LOCALAPPDATA'):
        roots.append(Path(environment['LOCALAPPDATA']) / 'Programs' / 'Git')
    for root in roots:
        for relative in ('bin/bash.exe', 'usr/bin/bash.exe'):
            bash = root / relative
            if bash.is_file():
                return str(bash)
    raise RuntimeError('Git for Windows Bash was not found; '
                       'install Git for Windows for action tests')
