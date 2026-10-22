"""Assemble a lattice-prompt release bundle.

    python build/build.py --version <version> [--platform win64|linux-x86_64]
                          [--make-exe <path>] [--pip-cert <pem>] [--seed-from <python>]
                          [--skip-smoke] [--no-zip]

A bundle is built on its own platform (the packages are installed by running
the bundled interpreter). Steps, each idempotent on a clean dist directory:

1. Fetch the runtime inputs named in lock/third-party.json into build/cache
   (verifying SHA-256; a cached file with the right digest is reused).
2. Lay out dist/lattice-prompt-<version>-<platform>: python/ (the relocatable
   CPython), on Windows git/ (MinGit) and tools/make.exe, the platform's
   launchers in bin/, install.py with install.cmd or install.sh, smoke.py.
3. Clone the components from the submodule checkouts at their pinned
   commits (single-branch, depth 1; the generator's makefiles and the
   knowledge base need a git checkout, not an export).
4. Install the packages into the bundled Python: from lock/requirements.lock
   when it exists (exact versions, no resolution), else resolve from the
   components' requirements under lock/constraints.txt and write the lock
   for the next build.
5. Write VERSION.json, run smoke.py with the bundled interpreter, archive
   (zip on Windows, tar.gz on Linux so the executable bits survive).

Downloads go through Python's TLS stack; --pip-cert (or the PIP_CERT
environment variable) names a CA bundle for a TLS-inspecting proxy, used for
both the downloads and pip.
"""

import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, 'cache')
COMPONENTS = {
    'cortex-a2c': os.path.join(ROOT, 'components', 'cortex-a2c'),
    'cortex-kb': os.path.join(ROOT, 'components', 'cortex-kb'),
    # the lattice-cortex server (package lattice_prompt, module lattice_prompt.server)
    'cortex-mcp': os.path.join(ROOT, 'components', 'cortex-mcp'),
}
LOCK_DIR = os.path.join(ROOT, 'lock')
REQ_LOCK = os.path.join(LOCK_DIR, 'requirements.lock')
CONSTRAINTS = os.path.join(LOCK_DIR, 'constraints.txt')

# What differs per platform. 'python' is the interpreter's path inside the
# extracted python/ directory; 'bundle_tools' says whether git and make ship in
# the bundle (Windows) or come from the system (Linux).
PLATFORMS = {
    'win64': {
        'python': ('python.exe',),
        'bundle_tools': True,
        'launchers': ('_env.cmd', 'a2c-mcp.cmd', 'kb-mcp.cmd', 'kb-skills.cmd', 'a2c-make.cmd', 'a2c-shell.cmd', 'new-project.cmd', 'lattice-cortex.cmd'),
        'installer': 'install.cmd',
        'archive': '.zip',
    },
    'linux-x86_64': {
        'python': ('bin', 'python3'),
        'bundle_tools': False,
        'launchers': ('_env.sh', 'a2c-mcp', 'kb-mcp', 'kb-skills', 'a2c-make', 'a2c-shell', 'new-project', 'lattice-cortex'),
        'installer': 'install.sh',
        'archive': '.tar.gz',
    },
}


def host_platform():
    if sys.platform == 'win32':
        return 'win64'
    if sys.platform.startswith('linux') and os.uname().machine in ('x86_64', 'amd64'):
        return 'linux-x86_64'
    raise SystemExit(f'no bundle definition for this host ({sys.platform}, {os.uname().machine})')


def log(msg):
    print(f'[build] {msg}', flush=True)


def tool_version(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0]
    except Exception:  # noqa: BLE001
        return 'unknown'


def _writable_then_retry(func, path, exc):
    # Windows refuses to delete read-only files (git's pack files are).
    import stat
    os.chmod(path, os.stat(path).st_mode | stat.S_IWRITE)
    func(path)


def rmtree(path):
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_writable_then_retry)
    else:
        shutil.rmtree(path, onerror=lambda f, p, e: _writable_then_retry(f, p, e[1]))


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch(entry, cert):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, entry['name'])
    if os.path.isfile(path) and sha256(path) == entry['sha256']:
        log(f'cached {entry["name"]}')
        return path
    log(f'downloading {entry["url"]}')
    ctx = ssl.create_default_context(cafile=cert) if cert else ssl.create_default_context()
    req = urllib.request.Request(entry['url'], headers={'User-Agent': 'lattice-prompt-build'})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as r, open(path, 'wb') as fh:
        shutil.copyfileobj(r, fh, 1 << 20)
    digest = sha256(path)
    if digest != entry['sha256']:
        os.remove(path)
        raise SystemExit(f'{entry["name"]}: sha256 {digest} does not match the lock ({entry["sha256"]})')
    return path


def git(args, cwd=None):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True, text=True,
                          encoding='utf-8', errors='replace', check=True).stdout.strip()


def component_commit(path):
    return git(['rev-parse', 'HEAD'], cwd=path)


def clone_component(name, src, dest):
    commit = component_commit(src)
    log(f'cloning {name} at {commit[:12]}')
    # From the local checkout, so no network and the same objects; detached
    # at the pinned commit, with origin pointing at the real remote so the
    # knowledge base can fetch its tracked ref when a network is present.
    # Shallow: the bundle carries the pinned commit only. The components'
    # history (tens of megabytes) serves no one inside a bundle; the knowledge
    # base's version history lives in its metadata, not in git. The local
    # checkout is detached at the pinned commit, so its HEAD is what --depth 1
    # takes; anything else falls back to a full clone of that commit.
    try:
        subprocess.run(['git', 'clone', '--quiet', '--no-local', '--depth', '1', '--no-checkout', src, dest], check=True)
        subprocess.run(['git', 'checkout', '--quiet', '--detach', commit], cwd=dest, check=True)
    except subprocess.CalledProcessError:
        shutil.rmtree(dest, ignore_errors=True)
        subprocess.run(['git', 'clone', '--quiet', '--no-local', '--no-checkout', src, dest], check=True)
        subprocess.run(['git', 'checkout', '--quiet', '--detach', commit], cwd=dest, check=True)
    remote = git(['config', '--get', 'remote.origin.url'], cwd=src)
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote], cwd=dest, check=True)
    assert component_commit(dest) == commit
    return commit


def first_constraints(seed_from, bundle):
    """Constraints for the first resolution: lock/constraints.txt, then (with
    --seed-from) every pinned version of another interpreter that the file
    does not already name, so pip prefers wheels that are already cached."""
    names = set()
    lines = []
    if os.path.isfile(CONSTRAINTS):
        for line in open(CONSTRAINTS, encoding='utf-8'):
            spec = line.split('#', 1)[0].strip()
            if spec:
                lines.append(spec)
                names.add(re.split(r'[<>=!~\[; ]', spec, 1)[0].lower().replace('_', '-'))
    if seed_from:
        frozen = subprocess.run([seed_from, '-m', 'pip', 'freeze', '--exclude-editable'],
                                capture_output=True, text=True, check=True).stdout
        for spec in frozen.splitlines():
            if '==' not in spec or ' @ ' in spec:
                continue
            name = spec.split('==', 1)[0].lower().replace('_', '-')
            if name not in names:
                lines.append(spec)
                names.add(name)
        log(f'seeding the resolution from {seed_from} ({len(lines)} constraints)')
    path = os.path.join(bundle, 'first-constraints.txt')
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(lines) + '\n')
    return path


def pip(py, args, cert):
    cmd = [py, '-m', 'pip', '--disable-pip-version-check']
    if cert:
        cmd += ['--cert', cert]
    if args and args[0] == 'install':
        args = ['install', '--no-warn-script-location'] + args[1:]
    log('pip ' + ' '.join(args[:3]) + (' ...' if len(args) > 3 else ''))
    # A Windows antivirus scan can hold pip's unpack files for a moment
    # ("WinError 32 ... used by another process"); one retry covers it.
    for attempt in (1, 2):
        r = subprocess.run(cmd + args)
        if r.returncode == 0:
            return
        if attempt == 1:
            log('pip failed; retrying once')
            time.sleep(5)
    raise SystemExit('pip failed twice')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='assemble a lattice-prompt bundle')
    parser.add_argument('--version', required=True)
    parser.add_argument('--kb-design', action='append', default=[], metavar='NAME',
                    help='keep only this knowledge-base design in the bundle (repeatable; other kinds untouched)')
    parser.add_argument('--kb-family', action='append', default=[], metavar='FAMILY',
                    help='keep only designs, boards and device notes of this family (repeatable)')
    parser.add_argument('--make-exe', default=shutil.which('make'))
    parser.add_argument('--pip-cert', default=os.environ.get('PIP_CERT'))
    parser.add_argument('--seed-from', metavar='PYTHON',
                        help='interpreter whose installed versions constrain the first resolution '
                             '(its wheels are already in the pip cache on a network that blocks new downloads)')
    parser.add_argument('--platform', choices=sorted(PLATFORMS), default=host_platform(),
                        help='bundle platform (default: the host); the packages are installed by '
                             'running the bundled interpreter, so a bundle is built on its own platform')
    parser.add_argument('--skip-smoke', action='store_true')
    parser.add_argument('--no-zip', action='store_true')
    args = parser.parse_args(argv)
    if args.platform != host_platform():
        raise SystemExit(f'a {args.platform} bundle is built on {args.platform}, not on {host_platform()}')
    plat = PLATFORMS[args.platform]

    with open(os.path.join(LOCK_DIR, 'third-party.json'), encoding='utf-8') as fh:
        third = json.load(fh)
    name = f'lattice-prompt-{args.version}-{args.platform}'
    dist = os.path.join(ROOT, 'dist')
    bundle = os.path.join(dist, name)
    if os.path.isdir(bundle):
        log(f'removing {bundle}')
        rmtree(bundle)
    os.makedirs(bundle)

    # 1 + 2: runtime and tools
    py_archive = fetch(third['python'][args.platform], args.pip_cert)
    log('extracting the Python runtime')
    with tarfile.open(py_archive) as tf:
        tf.extractall(bundle, filter='data')          # yields bundle/python
    py = os.path.join(bundle, 'python', *plat['python'])
    assert os.path.isfile(py), py
    tools = {}
    if plat['bundle_tools']:
        git_archive = fetch(third['git'][args.platform], args.pip_cert)
        log('extracting MinGit')
        with zipfile.ZipFile(git_archive) as zf:
            zf.extractall(os.path.join(bundle, 'git'))
        if not args.make_exe or not os.path.isfile(args.make_exe):
            raise SystemExit('GNU make not found: pass --make-exe (see lock/third-party.json)')
        os.makedirs(os.path.join(bundle, 'tools'))
        shutil.copy2(args.make_exe, os.path.join(bundle, 'tools', 'make.exe'))
        tools = {'git': tool_version([os.path.join(bundle, 'git', 'cmd', 'git.exe'), '--version']),
                 'git_archive': third['git'][args.platform]['name'],
                 'git_sha256': third['git'][args.platform]['sha256'],
                 'make': tool_version([os.path.join(bundle, 'tools', 'make.exe'), '--version']),
                 'make_provenance': third['make'][args.platform]['provenance']}
    else:
        tools = {'note': 'git and make are taken from the system (not bundled on this platform)',
                 'git_on_build_host': tool_version(['git', '--version']),
                 'make_on_build_host': tool_version(['make', '--version'])}
    os.makedirs(os.path.join(bundle, 'bin'))
    for launcher in plat['launchers']:
        shutil.copy2(os.path.join(ROOT, 'bin', launcher), os.path.join(bundle, 'bin', launcher))
    for rel in ('install.py', plat['installer'], 'smoke.py'):
        shutil.copy2(os.path.join(ROOT, rel), os.path.join(bundle, rel))
    # the project template (templates/project) and the script that instantiates it
    shutil.copytree(os.path.join(ROOT, 'templates'), os.path.join(bundle, 'templates'),
                    ignore=shutil.ignore_patterns('__pycache__'))
    if not plat['bundle_tools']:
        # Executable bits for the shell launchers (git keeps them, a Windows
        # checkout does not; the tar archive records them).
        for rel in [os.path.join('bin', l) for l in plat['launchers']] + [plat['installer']]:
            path = os.path.join(bundle, rel)
            os.chmod(path, os.stat(path).st_mode | 0o755)

    # 3: components
    commits = {}
    os.makedirs(os.path.join(bundle, 'components'))
    for cname, src in COMPONENTS.items():
        commits[cname] = clone_component(cname, src, os.path.join(bundle, 'components', cname))

    # 4: packages
    a2c = os.path.join(bundle, 'components', 'cortex-a2c')
    kb = os.path.join(bundle, 'components', 'cortex-kb')
    cmcp = os.path.join(bundle, 'components', 'cortex-mcp')
    local = [os.path.join(a2c, 'mcp'), kb, cmcp]
    if os.path.isfile(REQ_LOCK):
        pip(py, ['install', '--no-deps', '-r', REQ_LOCK], args.pip_cert)
        # Isolated builds, as on the first resolution: the bundled Python ships
        # pip only, not setuptools or hatchling.
        pip(py, ['install', '--no-deps'] + local, args.pip_cert)
    else:
        constrain = ['-c', first_constraints(args.seed_from, bundle)]
        pip(py, ['install'] + constrain + ['-r', os.path.join(a2c, 'requirements.txt'), os.path.join(a2c, 'mcp'), f'{kb}[mcp]', cmcp], args.pip_cert)
        frozen = subprocess.run([py, '-m', 'pip', 'freeze', '--exclude-editable'], capture_output=True,
                                text=True, check=True).stdout
        lines = [l for l in frozen.splitlines()
                 if l and not l.startswith(('arch2code-mcp', 'arch2code_mcp', 'cortex-kb', 'cortex_kb', 'lattice-prompt-mcp-server', 'lattice_prompt_mcp_server')) and '@' not in l]
        os.makedirs(LOCK_DIR, exist_ok=True)
        with open(REQ_LOCK, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('# Written by build/build.py from the first resolution; later builds install exactly these.\n')
            fh.write('\n'.join(lines) + '\n')
        log(f'wrote {REQ_LOCK} ({len(lines)} packages)')
        os.remove(os.path.join(bundle, 'first-constraints.txt'))
    # pip itself stays, but its own console scripts carry an absolute path; the
    # launchers call python -m, so nothing in Scripts/ is relied on.

    # 4b: distribution filter on the bundled knowledge base (section 10 of its
    # design document): entries above the policy's classification limit and
    # export-controlled ones are removed, vendored sources withheld; the clone
    # gets a filter commit so it stays clean for the server, and the record
    # goes into VERSION.json.
    log('filtering the knowledge base for distribution')
    selectors = [a for d in args.kb_design for a in ('--design', d)] + [a for f in args.kb_family for a in ('--family', f)]
    filt = subprocess.run([py, '-c', 'from kbtools.cli import main; main()', '--repo', kb, 'export-bundle', '--json'] + selectors,
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    if filt.returncode != 0:
        raise SystemExit(f'export-bundle failed:\n{filt.stdout}\n{filt.stderr}')
    distribution = json.loads(filt.stdout)
    rec = distribution.get('record', {})
    log(f"knowledge base: {rec.get('kept')} entries kept, {len(rec.get('removed', []))} removed, "
        f"{len(rec.get('stripped', []))} stripped of sources (classification <= {rec.get('max_classification')})")
    commits['cortex-kb'] = {'source': commits['cortex-kb'], 'bundle': distribution.get('committed'),
                            'filter': {k: rec.get(k) for k in ('max_classification', 'include_restricted', 'vendored_sources', 'designs', 'families', 'kept')},
                            'removed': [i['path'] for i in rec.get('removed', [])],
                            'stripped': [i['path'] for i in rec.get('stripped', [])]}

    # 4c: licence check and third-party notices (build/notices.py, policy in
    # lock/licenses.json): every bundled package must carry an allowed licence,
    # and THIRD_PARTY_NOTICES.md at the bundle root reproduces the licence texts
    # and the source offers for the GPL tools. A disallowed or undeclared
    # licence stops the build here.
    log('licence check and third-party notices')
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notices  # noqa: E402
    notice_record = notices.generate(bundle, py, args.platform, third)
    log(f"notices: {notice_record['packages']} packages, licences {', '.join(notice_record['licenses'])}")

    # 5: version record, smoke, archive
    version = {
        'name': name,
        'version': args.version,
        'platform': args.platform,
        'built': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'components': commits,
        'runtime': {'python': tool_version([py, '--version']), 'archive': third['python'][args.platform]['name'],
                    'sha256': third['python'][args.platform]['sha256']},
        'tools': tools,
        'requirements_lock': os.path.basename(REQ_LOCK),
        'notices': notice_record,
    }
    with open(os.path.join(bundle, 'VERSION.json'), 'w', encoding='utf-8') as fh:
        json.dump(version, fh, indent=2)
        fh.write('\n')
    if not args.skip_smoke:
        log('running smoke.py inside the bundle')
        r = subprocess.run([py, os.path.join(bundle, 'smoke.py')], cwd=bundle)
        if r.returncode != 0:
            raise SystemExit('smoke test failed; the bundle is left in dist/ for inspection')
    if not args.no_zip:
        ext = plat['archive']
        out = os.path.join(dist, name + ext)
        log(f'archiving {out}')
        if os.path.exists(out):
            os.remove(out)
        if ext == '.zip':
            shutil.make_archive(os.path.join(dist, name), 'zip', dist, name)
        else:
            # tar keeps the executable bits of the launchers and the interpreter.
            with tarfile.open(out, 'w:gz') as tf:
                tf.add(bundle, arcname=name)
        with open(out + '.sha256', 'w', encoding='utf-8') as fh:
            fh.write(f'{sha256(out)}  {name}{ext}\n')
        log(f'{name}{ext} {os.path.getsize(out) // (1 << 20)} MB, sha256 in {name}{ext}.sha256')
    return 0


if __name__ == '__main__':
    sys.exit(main())
