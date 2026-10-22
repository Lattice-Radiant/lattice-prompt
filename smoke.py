"""Smoke test of an assembled bundle, run with the bundle's own Python from
the bundle root (build/build.py runs it; a user can rerun it any time):

- the interpreter and every package the two components import;
- git and make: from the bundle on Windows, from the system on Linux;
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
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
WINDOWS = sys.platform == 'win32'
EXT = '.cmd' if WINDOWS else ''
PY = os.path.join(ROOT, 'python', 'python.exe') if WINDOWS else os.path.join(ROOT, 'python', 'bin', 'python3')
# git and make ship in the Windows bundle; on Linux the distribution's are used.
BUNDLED_TOOLS = WINDOWS
A2C = os.path.join(ROOT, 'components', 'cortex-a2c')
KB = os.path.join(ROOT, 'components', 'cortex-kb')
failures = []


def check(ok, message):
    print(f"{'PASS' if ok else 'FAIL'}: {message}")
    if not ok:
        failures.append(message)


def check_run(r, message, tail=40):
    """check() on a completed process; on failure, show the end of its output
    so a CI log says why."""
    check(r.returncode == 0, f'{message} (rc {r.returncode})')
    if r.returncode != 0:
        for stream, text in (('stdout', r.stdout), ('stderr', r.stderr)):
            lines = (text or '').splitlines()
            if lines:
                print(f'--- {message}: last {min(tail, len(lines))} lines of {stream} ---')
                print('\n'.join(lines[-tail:]))


def env():
    e = dict(os.environ)
    if WINDOWS:
        first = [os.path.join(ROOT, 'python'), os.path.join(ROOT, 'python', 'Scripts'),
                 os.path.join(ROOT, 'git', 'cmd'), os.path.join(ROOT, 'git', 'usr', 'bin'),
                 os.path.join(ROOT, 'tools')]
    else:
        first = [os.path.join(ROOT, 'python', 'bin')]
    e['PATH'] = os.pathsep.join(first + [e.get('PATH', '')])
    e['A2C_ROOT'] = A2C
    e['PYTHON'] = PY.replace('\\', '/')
    e.setdefault('CORTEX_KB_CACHE', os.path.join(tempfile.gettempdir(), 'lattice-prompt-smoke-kb'))
    e['PYTHONNOUSERSITE'] = '1'
    return e


def run(cmd, cwd=None, timeout=900):
    # CreateProcess searches the parent's PATH, not the child's, so resolve
    # the executable against the bundle PATH explicitly.
    exe = shutil.which(cmd[0], path=env()['PATH'])
    cmd = [exe or cmd[0]] + list(cmd[1:])
    return subprocess.run(cmd, cwd=cwd, env=env(), capture_output=True, text=True,
                          encoding='utf-8', errors='replace', timeout=timeout)


def check_runtime():
    os.environ.update(env())   # the launchers set these; the bare imports need A2C_ROOT
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
        if BUNDLED_TOOLS:
            check(exe and os.path.normcase(exe).startswith(os.path.normcase(ROOT)), f'{tool} comes from the bundle ({exe})')
        else:
            check(bool(exe), f'{tool} found on the system ({exe})')


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
        check_run(r, 'make db on a copy of examples/simple')
        r = run(['make', '-C', proj, '-j4', 'gen'])
        check_run(r, 'make gen on the copy')
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


async def kb_status_when_built(command, timeout_s=900):
    """kb_status while the server is still building its session index returns
    {"building": true}; on a fresh cache (CI, first start) that takes a while.
    Keep one session open and ask again until the index is ready."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    params = StdioServerParameters(command=command, args=[], env=env())
    deadline = time.monotonic() + timeout_s
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await asyncio.wait_for(s.initialize(), timeout=120)
            tools = await asyncio.wait_for(s.list_tools(), timeout=60)
            names = sorted(t.name for t in tools.tools)
            while True:
                result = await asyncio.wait_for(s.call_tool('kb_status', {}), timeout=300)
                text = result.content[0].text if result.content else ''
                status = json.loads(text) if text.strip().startswith('{') else {}
                if not (isinstance(status, dict) and status.get('building')) or time.monotonic() > deadline:
                    return names, text, status
                await asyncio.sleep(10)


def check_servers():
    a2c = os.path.join(ROOT, 'bin', 'a2c-mcp' + EXT)
    try:
        names, text = asyncio.run(mcp_session(a2c, ('toolchain_detect', {})))
        check(len(names) >= 20 and 'generate' in names, f'arch2code MCP: {len(names)} tools')
        check('"make"' in text, 'arch2code MCP: toolchain_detect answers')
    except Exception as exc:  # noqa: BLE001
        check(False, f'arch2code MCP: {exc}')
    kb = os.path.join(ROOT, 'bin', 'kb-mcp' + EXT)
    try:
        names, text, status = asyncio.run(kb_status_when_built(kb))
        check('kb_find_ips' in names, f'cortex-kb MCP: {len(names)} tools')
        check(isinstance(status, dict) and status and not status.get('building') and 'error' not in status,
              f'cortex-kb MCP: kb_status answers ({str(text)[:80]})')
    except Exception as exc:  # noqa: BLE001
        check(False, f'cortex-kb MCP: {exc}')
    # the skills launcher lists the knowledge base's reviewed skills (design skills)
    r = run([os.path.join(ROOT, 'bin', 'kb-skills' + EXT), 'list', '--json'])
    ok = r.returncode == 0 and r.stdout.strip().startswith(('[', '{'))
    try:
        count = len(json.loads(r.stdout)) if ok else 0
    except json.JSONDecodeError:
        ok, count = False, 0
    check(ok, f'kb-skills list answers ({count} reviewed skill(s))')


def check_notices():
    """THIRD_PARTY_NOTICES.md exists and names every distribution the bundled Python carries."""
    path = os.path.join(ROOT, 'THIRD_PARTY_NOTICES.md')
    if not os.path.isfile(path):
        check(False, 'THIRD_PARTY_NOTICES.md present')
        return
    text = open(path, encoding='utf-8', errors='replace').read()
    import sysconfig
    sp = sysconfig.get_paths()['purelib']
    first_party = {'arch2code-mcp', 'arch2code_mcp', 'cortex-kb', 'cortex_kb', 'pip'}
    missing = []
    for d in os.listdir(sp):
        if d.endswith('.dist-info'):
            name = d.split('-')[0]
            if name.lower() in first_party:
                continue
            if f'| {name} |' not in text and f'| {name.replace("_", "-")} |' not in text and f'| {name.replace("-", "_")} |' not in text:
                missing.append(name)
    check(not missing, 'THIRD_PARTY_NOTICES.md lists every bundled package' + (f' (missing: {", ".join(missing)})' if missing else ''))
    check('## Licence texts' in text, 'THIRD_PARTY_NOTICES.md carries the licence texts')


def main() -> int:
    check_runtime()
    check_generator()
    check_servers()
    check_notices()
    print(f'{len(failures)} check(s) failed' if failures else 'ALL CHECKS PASSED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
