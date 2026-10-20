"""Assemble a lattice-prompt release bundle.

    python build/build.py --version <version> [--make-exe <path>] [--pip-cert <pem>]
                          [--skip-smoke] [--no-zip]

Steps, each idempotent on a clean dist directory:

1. Fetch the runtime inputs named in lock/third-party.json into build/cache
   (verifying SHA-256; a cached file with the right digest is reused).
2. Lay out dist/lattice-prompt-<version>-win64: python/ (the relocatable
   CPython), git/ (MinGit), tools/make.exe, bin/, install.py, install.cmd,
   smoke.py.
3. Clone the two components from the submodule checkouts at their pinned
   commits (single-branch, depth 1; the generator's makefiles and the
   knowledge base need a git checkout, not an export).
4. Install the packages into the bundled Python: from lock/requirements.lock
   when it exists (exact versions, no resolution), else resolve from the
   components' requirements and write the lock for the next build.
5. Write VERSION.json, run smoke.py with the bundled interpreter, zip.

Downloads go through Python's TLS stack; --pip-cert (or the PIP_CERT
environment variable) names a CA bundle for a TLS-inspecting proxy, used for
both the downloads and pip.
"""

import argparse
import hashlib
import json
import os
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
}
LOCK_DIR = os.path.join(ROOT, 'lock')
REQ_LOCK = os.path.join(LOCK_DIR, 'requirements.lock')


def log(msg):
    print(f'[build] {msg}', flush=True)


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
    subprocess.run(['git', 'clone', '--quiet', '--no-local', '--no-checkout', src, dest], check=True)
    subprocess.run(['git', 'checkout', '--quiet', '--detach', commit], cwd=dest, check=True)
    remote = git(['config', '--get', 'remote.origin.url'], cwd=src)
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote], cwd=dest, check=True)
    assert component_commit(dest) == commit
    return commit


def pip(py, args, cert):
    cmd = [py, '-m', 'pip', '--disable-pip-version-check', '--no-warn-script-location']
    if cert:
        cmd += ['--cert', cert]
    log('pip ' + ' '.join(args[:3]) + (' ...' if len(args) > 3 else ''))
    subprocess.run(cmd + args, check=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='assemble a lattice-prompt bundle')
    parser.add_argument('--version', required=True)
    parser.add_argument('--make-exe', default=shutil.which('make'))
    parser.add_argument('--pip-cert', default=os.environ.get('PIP_CERT'))
    parser.add_argument('--skip-smoke', action='store_true')
    parser.add_argument('--no-zip', action='store_true')
    args = parser.parse_args(argv)

    with open(os.path.join(LOCK_DIR, 'third-party.json'), encoding='utf-8') as fh:
        third = json.load(fh)
    name = f'lattice-prompt-{args.version}-win64'
    dist = os.path.join(ROOT, 'dist')
    bundle = os.path.join(dist, name)
    if os.path.isdir(bundle):
        log(f'removing {bundle}')
        shutil.rmtree(bundle)
    os.makedirs(bundle)

    # 1 + 2: runtime and tools
    py_archive = fetch(third['python'], args.pip_cert)
    log('extracting the Python runtime')
    with tarfile.open(py_archive) as tf:
        tf.extractall(bundle, filter='data')          # yields bundle/python
    py = os.path.join(bundle, 'python', 'python.exe')
    assert os.path.isfile(py), py
    git_archive = fetch(third['git'], args.pip_cert)
    log('extracting MinGit')
    with zipfile.ZipFile(git_archive) as zf:
        zf.extractall(os.path.join(bundle, 'git'))
    if not args.make_exe or not os.path.isfile(args.make_exe):
        raise SystemExit('GNU make not found: pass --make-exe (see lock/third-party.json)')
    os.makedirs(os.path.join(bundle, 'tools'))
    shutil.copy2(args.make_exe, os.path.join(bundle, 'tools', 'make.exe'))
    for rel in ('bin', 'install.py', 'install.cmd', 'smoke.py'):
        src = os.path.join(ROOT, rel)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(bundle, rel))
        else:
            shutil.copy2(src, os.path.join(bundle, rel))

    # 3: components
    commits = {}
    os.makedirs(os.path.join(bundle, 'components'))
    for cname, src in COMPONENTS.items():
        commits[cname] = clone_component(cname, src, os.path.join(bundle, 'components', cname))

    # 4: packages
    a2c = os.path.join(bundle, 'components', 'cortex-a2c')
    kb = os.path.join(bundle, 'components', 'cortex-kb')
    if os.path.isfile(REQ_LOCK):
        pip(py, ['install', '--no-deps', '-r', REQ_LOCK], args.pip_cert)
        pip(py, ['install', '--no-deps', '--no-build-isolation', os.path.join(a2c, 'mcp'), kb], args.pip_cert)
    else:
        pip(py, ['install', '-r', os.path.join(a2c, 'requirements.txt'), os.path.join(a2c, 'mcp'), f'{kb}[mcp]'], args.pip_cert)
        frozen = subprocess.run([py, '-m', 'pip', 'freeze', '--exclude-editable'], capture_output=True,
                                text=True, check=True).stdout
        lines = [l for l in frozen.splitlines()
                 if l and not l.startswith(('arch2code-mcp', 'arch2code_mcp', 'cortex-kb', 'cortex_kb')) and '@' not in l]
        os.makedirs(LOCK_DIR, exist_ok=True)
        with open(REQ_LOCK, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write('# Written by build/build.py from the first resolution; later builds install exactly these.\n')
            fh.write('\n'.join(lines) + '\n')
        log(f'wrote {REQ_LOCK} ({len(lines)} packages)')
    # pip itself stays, but its own console scripts carry an absolute path; the
    # launchers call python -m, so nothing in Scripts/ is relied on.

    # 5: version record, smoke, zip
    def tool_version(cmd, cwd=None):
        try:
            return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=60).stdout.strip().splitlines()[0]
        except Exception:  # noqa: BLE001
            return 'unknown'
    version = {
        'name': name,
        'version': args.version,
        'built': time.strftime('%Y-%m-%dT%H:%M:%S'),
        'components': commits,
        'runtime': {'python': tool_version([py, '--version']), 'archive': third['python']['name'],
                    'sha256': third['python']['sha256']},
        'tools': {'git': tool_version([os.path.join(bundle, 'git', 'cmd', 'git.exe'), '--version']),
                  'git_archive': third['git']['name'], 'git_sha256': third['git']['sha256'],
                  'make': tool_version([os.path.join(bundle, 'tools', 'make.exe'), '--version']),
                  'make_provenance': third['make']['provenance']},
        'requirements_lock': os.path.basename(REQ_LOCK),
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
        out = os.path.join(dist, name + '.zip')
        log(f'zipping {out}')
        if os.path.exists(out):
            os.remove(out)
        shutil.make_archive(os.path.join(dist, name), 'zip', dist, name)
        with open(out + '.sha256', 'w', encoding='utf-8') as fh:
            fh.write(f'{sha256(out)}  {name}.zip\n')
        log(f'{name}.zip {os.path.getsize(out) // (1 << 20)} MB, sha256 in {name}.zip.sha256')
    return 0


if __name__ == '__main__':
    sys.exit(main())
