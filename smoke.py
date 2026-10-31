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
                'mcp', 'arch2code_mcp', 'kbtools', 'sqlalchemy', 'alembic', 'pydantic', 'click',
                'lattice_prompt', 'radiant_mcp', 'serial', 'cryptography', 'jwt'):
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
    a2c = os.path.join(ROOT, 'bin', 'lattice-arch2code-mcp' + EXT)
    try:
        names, text = asyncio.run(mcp_session(a2c, ('toolchain_detect', {})))
        check(len(names) >= 20 and 'generate' in names, f'lattice-arch2code-mcp: {len(names)} tools')
        check('"make"' in text, 'lattice-arch2code-mcp: toolchain_detect answers')
    except Exception as exc:  # noqa: BLE001
        check(False, f'lattice-arch2code-mcp: {exc}')
    kb = os.path.join(ROOT, 'bin', 'lattice-knowledge-db' + EXT)
    try:
        names, text, status = asyncio.run(kb_status_when_built(kb))
        check('kb_find_ips' in names, f'lattice-knowledge-db: {len(names)} tools')
        check(isinstance(status, dict) and status and not status.get('building') and 'error' not in status,
              f'lattice-knowledge-db: kb_status answers ({str(text)[:80]})')
    except Exception as exc:  # noqa: BLE001
        check(False, f'lattice-knowledge-db: {exc}')
    propel = os.path.join(ROOT, 'bin', 'lattice-propel-mcp' + EXT)
    try:
        names, text = asyncio.run(mcp_session(propel, ('propel_compare_sbx_manifest', {'sbx_path': 'nowhere.sbx', 'manifest_path': 'nowhere.json'})))
        check(len(names) >= 80 and 'propel_replay_manifest' in names, f'lattice-propel-mcp: {len(names)} tools')
        check('error' in text, 'lattice-propel-mcp: propel_compare_sbx_manifest answers with a structured error for missing files')
    except Exception as exc:  # noqa: BLE001
        check(False, f'lattice-propel-mcp: {exc}')
    # No Radiant is needed: without confirm=True, program_device refuses before it looks for one.
    radiant = os.path.join(ROOT, 'bin', 'lattice-radiant-mcp' + EXT)
    try:
        names, text = asyncio.run(mcp_session(radiant, ('program_device', {'work_dir': 'nowhere'})))
        check(len(names) >= 50 and {'program_device', 'list_cables', 'add_compilation_job'} <= set(names)
              and not [n for n in names if n.startswith('reveal_')], f'lattice-radiant-mcp: {len(names)} tools')
        check('PROGRAM_CONFIRM_REQUIRED' in text, 'lattice-radiant-mcp: program_device refuses a live run without confirm')
    except Exception as exc:  # noqa: BLE001
        check(False, f'lattice-radiant-mcp: {exc}')
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
    first_party = {'arch2code-mcp', 'arch2code_mcp', 'cortex-kb', 'cortex_kb', 'pip', 'lattice-prompt-mcp-server', 'lattice_prompt_mcp_server',
                   'lattice-radiant-mcp', 'lattice_radiant_mcp'}
    import re
    norm = lambda s: re.sub(r'[-_.]+', '-', s).lower()  # noqa: E731 - PEP 503 name normalisation
    listed = {norm(m.group(1)) for m in re.finditer(r'^\| ([^|]+?) \|', text, re.M)}
    missing = []
    for d in os.listdir(sp):
        if d.endswith('.dist-info'):
            name = d[:-len('.dist-info')].rsplit('-', 1)[0]
            if norm(name) in {norm(f) for f in first_party}:
                continue
            if norm(name) not in listed:
                missing.append(name)
    check(not missing, 'THIRD_PARTY_NOTICES.md lists every bundled package' + (f' (missing: {", ".join(missing)})' if missing else ''))
    check('## Licence texts' in text, 'THIRD_PARTY_NOTICES.md carries the licence texts')


def check_template():
    """The project template's .mcp.json.example parses and every command is a clean path (a
    backslash that escaped as \b or \a once turned the bundle paths into control characters)."""
    path = os.path.join(ROOT, 'templates', 'project', '.mcp.json.example')
    try:
        with open(path, encoding='utf-8') as fh:
            servers = json.load(fh)['mcpServers']
        bad = [name for name, entry in servers.items() if any(ord(ch) < 32 for ch in entry.get('command', ''))]
        check(not bad, 'template .mcp.json.example: commands are clean paths' + (f' (control characters in {bad})' if bad else ''))
        check(set(servers) == set(BUNDLE_SERVERS), 'template .mcp.json.example: the four bundle servers are listed, under their names')
    except Exception as exc:  # noqa: BLE001
        check(False, f'template .mcp.json.example: {exc}')


BUNDLE_SERVERS = ('lattice-arch2code-mcp', 'lattice-knowledge-db', 'lattice-propel-mcp', 'lattice-radiant-mcp')


def check_installer():
    """install.py against a fabricated home: every old entry of a bundle server is replaced by the
    entry under its new name -- the old bundle keys (arch2code, cortex-kb, lattice-cortex), the
    cortex-mcp installer's lattice-prompt entry, the Radiant installer's radiant and
    lattice-radiant-mcp entries, a development checkout under another key, and a project-scope
    entry -- env blocks are carried over, unrelated entries stay, and --uninstall removes the
    bundle entries under their new and old names."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as home:
        cfg = os.path.join(home, '.claude.json')
        before = {'mcpServers': {
            'lattice-prompt': {'command': 'C:/venv/python.exe', 'args': ['-m', 'lattice_prompt.server'],
                               'env': {'LATTICE_PROPEL_BASE': 'C:/lscc/propel/2025.1'}},
            'lattice-cortex': {'command': 'C:/old-bundle/bin/lattice-cortex.cmd', 'args': []},
            'arch2code': {'command': 'C:/old-bundle/bin/a2c-mcp.cmd', 'args': []},
            'a2c-dev': {'command': '/work/cortex-a2c/.venv/bin/python', 'args': ['-m', 'arch2code_mcp']},
            'cortex-kb': {'command': 'cortex-kb', 'args': ['serve']},
            'radiant': {'command': 'python', 'args': ['-m', 'radiant_mcp'], 'env': {'RADIANT_EXE': 'C:/r/radiantc.exe'}},
            'lattice-radiant-mcp': {'command': 'C:/rmcp/.venv/Scripts/python.exe', 'args': ['-m', 'radiant_mcp'],
                                    'env': {'TIMING_CLOSURE_MERGE_ENABLED': '1',
                                            'CORTEX_TIMING_CLOSURE_MCP_ENABLED_TOOLS': 'perceive_timing'}},
            'unrelated': {'command': 'node', 'args': ['server.js']},
        }, 'projects': {'C:/proj': {'mcpServers': {
            'cortex-kb': {'command': 'python', 'args': ['-m', 'kbtools.cli', 'serve']},
            'mine': {'command': 'node', 'args': ['mine.js']}}}}, 'other': True}
        with open(cfg, 'w', encoding='utf-8') as fh:
            json.dump(before, fh)
        env = dict(os.environ, HOME=home, USERPROFILE=home, APPDATA=os.path.join(home, 'appdata'),
                   XDG_CONFIG_HOME=os.path.join(home, 'config'))
        r = subprocess.run([PY, os.path.join(ROOT, 'install.py')], capture_output=True, text=True, env=env, cwd=home)
        check_run(r, 'install.py runs against a fabricated home')
        with open(cfg, encoding='utf-8') as fh:
            after = json.load(fh)
        servers = after.get('mcpServers', {})
        check(set(servers) == set(BUNDLE_SERVERS) | {'unrelated'},
              f'installer: old entries of the bundle servers removed, unrelated entries kept ({sorted(servers)})')
        check(servers.get('lattice-propel-mcp', {}).get('env', {}).get('LATTICE_PROPEL_BASE') == 'C:/lscc/propel/2025.1',
              'installer: env block of the replaced lattice-prompt entry carried over')
        renv = servers.get('lattice-radiant-mcp', {}).get('env', {})
        check(renv.get('RADIANT_EXE') == 'C:/r/radiantc.exe' and 'TIMING_CLOSURE_MERGE_ENABLED' not in renv
              and not any(k.startswith('CORTEX_TIMING_CLOSURE_MCP_') for k in renv),
              'installer: Radiant settings carried over, the timing-closure merge settings dropped')
        check(all(os.path.basename(servers.get(n, {}).get('command', '')).startswith(n) for n in BUNDLE_SERVERS),
              'installer: every bundle server points at its bundle launcher')
        project = after.get('projects', {}).get('C:/proj', {}).get('mcpServers', {})
        check(set(project) == {'mine'}, f'installer: project-scope entry of a bundle server removed ({sorted(project)})')
        check(after.get('other') is True, 'installer: other settings untouched')
        after['mcpServers']['arch2code'] = {'command': 'C:/old-bundle/bin/a2c-mcp.cmd', 'args': []}
        with open(cfg, 'w', encoding='utf-8') as fh:
            json.dump(after, fh)
        r = subprocess.run([PY, os.path.join(ROOT, 'install.py'), '--uninstall'], capture_output=True, text=True, env=env, cwd=home)
        with open(cfg, encoding='utf-8') as fh:
            servers = json.load(fh).get('mcpServers', {})
        check(r.returncode == 0 and set(servers) == {'unrelated'},
              f'installer: --uninstall removes the bundle entries under new and old names only ({sorted(servers)})')


def check_profile():
    """VERSION.json names the profile; a customer bundle carries no knowledge-base
    entry above public (the distribution record says the limit applied, and every
    metadata file in the bundled knowledge base agrees)."""
    path = os.path.join(ROOT, 'VERSION.json')
    try:
        with open(path, encoding='utf-8') as fh:
            version = json.load(fh)
    except (OSError, ValueError) as exc:
        check(False, f'VERSION.json readable: {exc}')
        return
    profile = version.get('profile')
    check(profile in ('internal', 'customer'), f'VERSION.json names the bundle profile ({profile})')
    if profile != 'customer':
        return
    rec = (version.get('components') or {}).get('cortex-kb', {}).get('filter') or {}
    check(rec.get('max_classification') == 'public',
          f"customer profile: the knowledge base was filtered at public (record says {rec.get('max_classification')})")
    above = []
    scanned = 0
    for kind in ('designs', 'patterns', 'anti_patterns', 'boards', 'ip_catalog', 'device_notes'):
        base = os.path.join(KB, kind)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            if 'metadata.yaml' not in files:
                continue
            scanned += 1
            with open(os.path.join(root, 'metadata.yaml'), encoding='utf-8', errors='replace') as fh:
                for line in fh:
                    stripped = line.strip()
                    if stripped.startswith('classification:'):
                        value = stripped.split(':', 1)[1].split('#', 1)[0].strip().strip('"\'')
                        if value and value != 'public':
                            above.append(f'{os.path.relpath(root, KB)} ({value})')
                        break
    check(not above, f'customer profile: no entry above public among {scanned} metadata file(s)'
          + (f' (found: {", ".join(above[:5])})' if above else ''))


# Imports that are allowed not to resolve inside the bundle, each with the reason. Everything
# else a bundled server imports -- at module level or inside a function -- must be importable
# by the bundled Python, so no feature needs a separate pip install.
OPTIONAL_IMPORTS = {
    'timing_closure': "lattice-radiant-mcp's timing-closure merge, off in the bundle (needs cortex-agent-impl)",
    'anthropic': 'cortex-kb draft-metadata command only (Claude API); no MCP tool uses it',
    'cocotb': "cortex-a2c socket examples, optional import for cocotb-driven co-simulation",
    'setuptools': 'cortex-a2c pysrc/table_format/setup.py, a packaging script, not imported at run time',
    'table_format': 'cortex-a2c pysrc/table_format demo and its own test',
    'pysrc': "cortex-a2c's own modules, imported with the checkout on sys.path",
}


def check_bundled_imports():
    """Every top-level module the four servers import (module level and inside functions,
    tests excluded) is importable by the bundled Python, unless OPTIONAL_IMPORTS names it."""
    import ast
    import importlib.util
    roots = [os.path.join(A2C, 'mcp', 'src', 'arch2code_mcp'), os.path.join(A2C, 'pysrc'),
             os.path.join(KB, 'kbtools'),
             os.path.join(ROOT, 'components', 'cortex-mcp', 'src', 'lattice_prompt'),
             os.path.join(ROOT, 'components', 'cortex-bridge', 'src', 'radiant_mcp')]
    own = {'arch2code_mcp', 'kbtools', 'lattice_prompt', 'radiant_mcp', '__future__'}
    stdlib = set(sys.stdlib_module_names)
    where = {}
    for root in roots:
        for dirpath, _, files in os.walk(root):
            if '__pycache__' in dirpath or os.sep + 'tests' in dirpath:
                continue
            for f in files:
                if not f.endswith('.py'):
                    continue
                path = os.path.join(dirpath, f)
                try:
                    tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        names = [a.name for a in node.names]
                    elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                        names = [node.module]
                    else:
                        continue
                    for name in names:
                        top = name.split('.')[0]
                        if top not in stdlib and top not in own:
                            where.setdefault(top, (os.path.relpath(path, ROOT), name))
    missing = []
    for top, (path, full) in sorted(where.items()):
        if top in OPTIONAL_IMPORTS:
            continue
        found = False
        for candidate in (top, full):           # a namespace package (ruamel) resolves by its full name
            try:
                found = found or importlib.util.find_spec(candidate) is not None
            except (ImportError, ValueError):
                pass
        if not found:
            missing.append(f'{top} ({path})')
    check(not missing, f'every import of the bundled servers resolves in the bundle ({len(where)} third-party modules)'
          + (f'; missing: {", ".join(missing)}' if missing else ''))


def main() -> int:
    check_runtime()
    check_generator()
    check_servers()
    check_bundled_imports()
    check_notices()
    check_template()
    check_installer()
    check_profile()
    print(f'{len(failures)} check(s) failed' if failures else 'ALL CHECKS PASSED')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
