"""Smoke test of an assembled bundle, run with the bundle's own Python from
the bundle root (build/build.py runs it; a user can rerun it any time):

- the interpreter and every package the two components import;
- git and make from the bundle;
- the arch2code generator on a copy of examples/simple (db, then gen through
  make with the bundle's tools);
- both MCP servers over stdio: initialize, list the tools, call one.

Exit status 0 when every check passed; the report names what failed.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, 'python', 'python.exe')
A2C = os.path.join(ROOT, 'components', 'cortex-a2c')
KB = os.path.join(ROOT, 'components', 'cortex-kb')
failures = []


def check(ok, message):
    print(f"{'PASS' if ok else 'FAIL'}: {message}")
    if not ok:
        failures.append(message)


def env():
    e = dict(os.environ)
    e['PATH'] = os.pathsep.join([os.path.join(ROOT, 'python'), os.path.join(ROOT, 'python', 'Scripts'),
                                 os.path.join(ROOT, 'git', 'cmd'), os.path.join(ROOT, 'git', 'usr', 'bin'),
                                 os.path.join(ROOT, 'tools'), e.get('PATH', '')])
    e['A2C_ROOT'] = A2C
    e['PYTHON'] = PY.replace('\\', '/')
    e.setdefault('CORTEX_KB_CACHE', os.path.join(tempfile.gettempdir(), 'lattice-prompt-smoke-kb'))
    e['PYTHONNOUSERSITE'] = '1'
    return e


def run(cmd, cwd=None, timeout=900):
    return subprocess.run(cmd, cwd=cwd, env=env(), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def check_runtime():
    check(os.path.samefile(sys.executable, PY), f'running the bundled interpreter ({sys.executable})')
    check(sys.version_info[:2] == (3, 12), f'Python {sys.version.split()[0]}')
    for mod in ('yaml', 'jinja2', 'graphviz', 'ruamel.yaml', 'colorama', 'junit_xml',
                'mcp', 'arch2code_mcp', 'kbtools', 'sqlalchemy', 'alembic', 'pydantic', 'click'):
        try:
            __import__(mod)
            check(True, f'import {mod}')
        except Exception as exc:  # noqa: BLE001 - reported
            check(False, f'import {mod}: {exc}')
    for tool, args in (('git', ['--version']), ('make', ['--version'])):
        r = run([tool] + args)
        check(r.returncode == 0, f'{tool}: {(r.stdout or r.stderr).splitlines()[0] if (r.stdout or r.stderr) else "no output"}')
        exe = shutil.which(tool, path=env()['PATH'])
        check(exe and os.path.normcase(exe).startswith(os.path.normcase(ROOT)), f'{tool} comes from the bundle ({exe})')


def check_generator():
    work = tempfile.mkdtemp(prefix='lp_smoke_')
    try:
        proj = os.path.join(work, 'simple')
        shutil.copytree(os.path.join(A2C, 'examples', 'simple'), proj,
                        ignore=shutil.ignore_patterns('build', '.gen', '*.db', '*.db-*'))
        posix = proj.replace('\\', '/')
        for rel in ('Makefile', 'include/make/shared.mk', 'rundir/Makefile', 'rtl/Makefile'):
            path = os.path.join(proj, rel)
            if not os.path.isfile(path):
                continue
            lines = open(path, encoding='utf-8').read().splitlines(keepends=True)
            lines = [f'REPO_ROOT = {posix}\n' if l.startswith('REPO_ROOT = ') else l for l in lines]
            lines = [f'A2C_ROOT = {A2C.replace(chr(92), "/")}\n' if l.startswith('A2C_ROOT = ') else l for l in lines]
            open(path, 'w', encoding='utf-8', newline='\n').write(''.join(lines))
        r = run(['make', '-C', proj, 'db'])
        check(r.returncode == 0, f'make db on a copy of examples/simple (rc {r.returncode})')
        r = run(['make', '-C', proj, '-j4', 'gen'])
        check(r.returncode == 0, f'make gen on the copy (rc {r.returncode})')
        r = run([PY, '-m', 'pysrc.driver', 'status', os.path.join(proj, 'arch', 'yaml', 'project.yaml')], cwd=A2C)
        check(r.returncode == 0 and 'rundir' in r.stdout, 'the driver reads the project')
    finally:
        shutil.rmtree(work, ignore_errors=True)


async def mcp_session(command, call):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=command, args=[], env=env())
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), timeout=120)
            tools = await asyncio.wait_for(s.list_tools(), timeout=60)
            names = sorted(t.name for t in tools.tools)
            result = await asyncio.wait_for(s.call_tool(*call), timeout=300)
            text = result.content[0].text if result.content else ''
            return names, text


def check_servers():
    a2c = os.path.join(ROOT, 'bin', 'a2c-mcp.cmd')
    try:
        names, text = asyncio.run(mcp_session(a2c, ('toolchain_detect', {})))
        check(len(names) >= 20 and 'generate' in names, f'arch2code MCP: {len(names)} tools')
        check('"make"' in text, 'arch2code MCP: toolchain_detect answers')
    except Exception as exc:  # noqa: BLE001
        check(False, f'arch2code MCP: {exc}')
    kb = os.path.join(ROOT, 'bin', 'kb-mcp.cmd')
    try:
        names, text = asyncio.run(mcp_session(kb, ('kb_status', {})))
        check('kb_find_ips' in names, f'cortex-kb MCP: {len(names)} tools')
        status = json.loads(text) if text.strip().startswith('{') else {}
        check(isinstance(status, dict) and status, f'cortex-kb MCP: kb_status answers ({str(text)[:80]})')
    except Exception as exc:  # noqa: BLE001
        check(False, f'cortex-kb MCP: {exc}')


def main() -> int:
    check_runtime()
    check_generator()
    check_servers()
    print(f'{len(failures)} check(s) failed' if failures else 'ALL CHECKS PASSED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
