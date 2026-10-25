#!/usr/bin/env python3
"""Run focused native-restoration regressions and static audit, not real-game tests.

Requires .NET 9 SDK and Python bridge dependencies. No game or Steam account data
is used. The bridge unit test is isolated from host proxy settings because it uses
fake responses and only constructs (never sends through) a real HTTP client.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', type=Path, default=None)
    parser.add_argument('--log-dir', type=Path, default=None)
    args = parser.parse_args()
    dotnet = args.dotnet or shutil.which('dotnet')
    if not dotnet:
        parser.error('Put the .NET 9 SDK on PATH or supply --dotnet')
    dotnet = Path(dotnet).resolve()
    if not dotnet.is_file():
        parser.error(f'No executable file at {dotnet}')
    repo = Path(__file__).resolve().parents[1]
    logs = args.log_dir or Path(tempfile.mkdtemp(prefix='sts-native-checks-'))
    logs.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, DOTNET=str(dotnet))
    env['PATH'] = str(dotnet.parent) + os.pathsep + env.get('PATH', '')
    failures = []
    tests = sorted((repo / 'scripts').glob('test_*.py'))
    for test in tests:
        options = []
        if test.name == 'test_save_context.py':
            options = ['--dotnet-root', str(dotnet.parent)]
        elif test.name == 'test_missing_actions.py':
            options = ['--dotnet', str(dotnet), '--verify-origin']
        elif test.name in {'test_card_metadata.py', 'test_formatting_metadata.py', 'test_noncombat_markdown.py'}:
            options = ['--mutations']
        test_env = dict(env)
        if test.name == 'test_mcp_server.py':
            for key in list(test_env):
                if key.lower() in {'http_proxy', 'https_proxy', 'all_proxy'}:
                    test_env.pop(key)
        result = subprocess.run([sys.executable, str(test), *options], cwd=repo,
                                env=test_env, capture_output=True, text=True)
        (logs / (test.name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            failures.append(test.name)
        print(('FAIL' if result.returncode else 'PASS') + ' ' + test.name, flush=True)
    audit = subprocess.run([sys.executable, str(repo / 'scripts/audit_endpoints.py'), '--skip-live'],
                           cwd=repo, env=env, capture_output=True, text=True)
    (logs / 'audit_endpoints.log').write_text(audit.stdout + audit.stderr)
    if audit.returncode:
        failures.append('audit_endpoints.py --skip-live')
    print(('FAIL' if audit.returncode else 'PASS') + ' static endpoint audit')
    print(f'Logs: {logs}')
    print('Real-game build/runtime validation: NOT RUN by this suite.')
    if failures:
        print('Failed: ' + ', '.join(failures))
    return int(bool(failures))


if __name__ == '__main__':
    raise SystemExit(main())
