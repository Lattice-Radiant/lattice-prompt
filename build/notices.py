"""Third-party notices and licence check for a lattice-prompt bundle.

Reads every installed distribution of the bundle's Python (``*.dist-info`` under its
site-packages), the bundled CPython, and on Windows the bundled Git and GNU make, and writes
``THIRD_PARTY_NOTICES.md`` at the bundle root: a summary table (package, version, licence,
where its text is) followed by the full licence texts shipped with each package, and the
source offers for the GPL tools. The policy in ``lock/licenses.json`` names the licences a
Python package may carry; a package with a copyleft or unknown licence fails the build unless
the policy lists an override for it (with a reason).

Usage from build.py: ``generate(bundle_dir, python_exe, platform, third)``.
Standalone check of any interpreter: ``python build/notices.py --python <exe> [--out FILE]``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(ROOT, 'lock', 'licenses.json')
NOTICES = 'THIRD_PARTY_NOTICES.md'

# Classifier text -> SPDX-like identifier
CLASSIFIERS = {
    'MIT License': 'MIT', 'BSD License': 'BSD', 'Apache Software License': 'Apache-2.0',
    'ISC License (ISCL)': 'ISC', 'Python Software Foundation License': 'PSF-2.0',
    'Mozilla Public License 2.0 (MPL 2.0)': 'MPL-2.0', 'The Unlicense (Unlicense)': 'Unlicense',
    'zlib/libpng License': 'Zlib', 'GNU General Public License v2 (GPLv2)': 'GPL-2.0',
    'GNU General Public License v3 (GPLv3)': 'GPL-3.0', 'GNU Lesser General Public License v2 (LGPLv2)': 'LGPL-2.0',
    'GNU Lesser General Public License v3 (LGPLv3)': 'LGPL-3.0', 'GNU Affero General Public License v3': 'AGPL-3.0',
    'GNU Library or Lesser General Public License (LGPL)': 'LGPL', 'GNU General Public License (GPL)': 'GPL',
}


def load_policy() -> dict:
    with open(POLICY, encoding='utf-8') as fh:
        return json.load(fh)


def normalise(expr: str) -> str:
    """A short licence identifier from a License-Expression, a License field or a classifier."""
    e = (expr or '').strip()
    if not e:
        return ''
    e = e.replace('Licence', 'License')
    low = e.lower()
    if len(e) > 60:                      # a whole licence text in the License field
        if 'permission is hereby granted' in low and 'mit' in low[:200]:
            return 'MIT'
        if 'redistribution and use in source and binary forms' in low:
            return 'BSD'
        if 'apache license' in low:
            return 'Apache-2.0'
        return 'TEXT'
    table = {
        'mit': 'MIT', 'mit license': 'MIT', 'bsd': 'BSD', 'bsd license': 'BSD', 'bsd-3-clause': 'BSD-3-Clause',
        'bsd-2-clause': 'BSD-2-Clause', 'new bsd': 'BSD-3-Clause', 'apache 2.0': 'Apache-2.0', 'apache-2.0': 'Apache-2.0',
        'apache license 2.0': 'Apache-2.0', 'apache software license': 'Apache-2.0', 'isc': 'ISC', 'psf': 'PSF-2.0',
        'psfl': 'PSF-2.0', 'psf-2.0': 'PSF-2.0', 'python software foundation license': 'PSF-2.0', 'mpl-2.0': 'MPL-2.0',
        'mpl 2.0': 'MPL-2.0', 'unlicense': 'Unlicense', 'zlib': 'Zlib', '0bsd': '0BSD', 'python-2.0': 'Python-2.0',
        '3-clause bsd license': 'BSD-3-Clause', '2-clause bsd license': 'BSD-2-Clause', 'bsd 3-clause': 'BSD-3-Clause',
        'bsd-3-clause license': 'BSD-3-Clause', 'apache': 'Apache-2.0', 'apache license': 'Apache-2.0',
        'apache license, version 2.0': 'Apache-2.0', 'mit-0': 'MIT-0', 'mit-cmu': 'MIT-CMU', 'cc0-1.0': 'CC0-1.0',
        'historical permission notice and disclaimer (hpnd)': 'HPND',
    }
    if low in table:
        return table[low]
    if low in {c.lower() for c in CLASSIFIERS}:
        return CLASSIFIERS[[c for c in CLASSIFIERS if c.lower() == low][0]]
    return e


def read_metadata(dist_info: str) -> dict:
    meta = {'license_expression': '', 'license': '', 'classifiers': [], 'name': '', 'version': '', 'home': ''}
    path = os.path.join(dist_info, 'METADATA')
    if not os.path.isfile(path):
        return meta
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            if not line.strip():
                break               # end of headers
            key, _, value = line.partition(':')
            key, value = key.strip().lower(), value.strip()
            if key == 'name':
                meta['name'] = value
            elif key == 'version':
                meta['version'] = value
            elif key == 'license-expression':
                meta['license_expression'] = value
            elif key == 'license' and not meta['license']:
                meta['license'] = value
            elif key == 'classifier' and value.startswith('License ::'):
                meta['classifiers'].append(value.split('::')[-1].strip())
            elif key in ('home-page',) and not meta['home']:
                meta['home'] = value
            elif key == 'project-url' and 'homepage' in value.lower() and not meta['home']:
                meta['home'] = value.split(',', 1)[-1].strip()
    return meta


def license_files(dist_info: str) -> list[str]:
    out = []
    lic_dir = os.path.join(dist_info, 'licenses')
    if os.path.isdir(lic_dir):
        for base, _, files in os.walk(lic_dir):
            out += [os.path.join(base, f) for f in sorted(files)]
    for f in sorted(os.listdir(dist_info)):
        if re.match(r'^(LICEN[CS]E|COPYING|NOTICE|AUTHORS)', f, re.I) and os.path.isfile(os.path.join(dist_info, f)):
            out.append(os.path.join(dist_info, f))
    return out


def site_packages(python_exe: str) -> list[str]:
    """Every directory the interpreter installs distributions into (purelib, platlib and the
    site directories, which differ when a venv sees its base environment)."""
    code = ('import json, site, sysconfig; d = [sysconfig.get_paths()["purelib"], sysconfig.get_paths()["platlib"]]\n'
            'd += getattr(site, "getsitepackages", lambda: [])()\n'
            'print(json.dumps(list(dict.fromkeys(x for x in d if x))))')
    out = subprocess.run([python_exe, '-c', code], capture_output=True, text=True, check=True).stdout.strip()
    return [p for p in json.loads(out) if os.path.isdir(p)]


def collect_packages(sp: str | list[str], policy: dict, skip: set[str]) -> tuple[list[dict], list[str]]:
    """Every installed distribution with its licence identifier, its files and its verdict."""
    allowed = {a.lower() for a in policy['allowed']}
    overrides = {k.lower(): v for k, v in policy.get('overrides', {}).items()}
    rows, problems = [], []
    dirs = [sp] if isinstance(sp, str) else list(sp)
    entries = []
    for base in dirs:
        entries += [(d, os.path.join(base, d)) for d in os.listdir(base) if d.endswith('.dist-info')]
    seen = set()
    for d, info in sorted(entries, key=lambda e: e[0].lower()):
        if d.lower() in seen:
            continue
        seen.add(d.lower())
        meta = read_metadata(info)
        name = meta['name'] or d.split('-')[0]
        if name.lower() in skip:
            continue
        ident = normalise(meta['license_expression']) or ''
        if not ident or ident == 'TEXT':
            ids = [normalise(c) for c in meta['classifiers']]
            ident = ' OR '.join(dict.fromkeys(i for i in ids if i)) or ident
        if (not ident or ident == 'TEXT') and meta['license']:
            ident = normalise(meta['license'])
        files = license_files(info)
        parts = [p.strip() for p in re.split(r'\bOR\b|\bAND\b|/', ident) if p.strip()] if ident else []
        verdict = 'allowed' if parts and all(p.lower() in allowed for p in parts) else ('unknown' if not parts or ident == 'TEXT' else 'disallowed')
        reason = ''
        if verdict != 'allowed' and name.lower() in overrides:
            o = overrides[name.lower()]
            ident = o.get('license', ident)
            reason = o.get('reason', '')
            verdict = 'allowed (override)'
        if verdict in ('unknown', 'disallowed'):
            problems.append(f"{name} {meta['version']}: licence {ident or 'not declared'} ({verdict})")
        rows.append({'name': name, 'version': meta['version'], 'license': ident or 'not declared', 'verdict': verdict,
                     'reason': reason, 'home': meta['home'], 'files': files})
    return rows, problems


def tool_notices(bundle: str, platform: str, third: dict, policy: dict) -> list[dict]:
    """The bundled runtime and tools: licence text from the bundle, source offer from the policy."""
    out = []
    py_dir = os.path.join(bundle, 'python')
    py_lic = [p for p in (os.path.join(py_dir, 'LICENSE.txt'), os.path.join(py_dir, 'LICENSE')) if os.path.isfile(p)]
    t = policy['tools']['python']
    out.append({'name': 'CPython (python-build-standalone)', 'version': third['python'][platform]['name'], 'license': t['license'],
                'files': py_lic, 'source': t['source'].replace('{archive}', third['python'][platform]['url']), 'note': t['note']})
    if platform == 'win64':
        git_lic = [p for p in (os.path.join(bundle, 'git', 'LICENSE.txt'),) if os.path.isfile(p)]
        t = policy['tools']['git']
        out.append({'name': 'Git for Windows (MinGit)', 'version': third['git'][platform]['name'], 'license': t['license'],
                    'files': git_lic, 'source': t['source'].replace('{url}', third['git'][platform]['url']), 'note': t['note']})
        t = policy['tools']['make']
        out.append({'name': 'GNU make', 'version': third['make'][platform].get('version', ''), 'license': t['license'],
                    'files': [], 'source': t['source'], 'note': t['note']})
    return out


def render(rows: list[dict], tools: list[dict], bundle_name: str) -> str:
    lines = [f'# Third-party notices for {bundle_name}', '',
             'This bundle redistributes the open-source software listed below. Each entry names the licence '
             'under which it is used; the licence texts shipped with the packages follow the tables. The '
             'bundle links nothing against the tools in the second table; they are separate programs invoked '
             'as commands, and their source code is available at the locations given.', '',
             '## Python packages', '', '| Package | Version | Licence | Licence files |', '| --- | --- | --- | --- |']
    for r in rows:
        files = ', '.join(os.path.basename(f) for f in r['files']) or 'none shipped (see the project page)'
        extra = f" ({r['reason']})" if r['reason'] else ''
        lines.append(f"| {r['name']} | {r['version']} | {r['license']}{extra} | {files} |")
    lines += ['', '## Runtime and tools', '', '| Component | Archive or version | Licence | Source |', '| --- | --- | --- | --- |']
    for t in tools:
        lines.append(f"| {t['name']} | {t['version']} | {t['license']} | {t['source']} |")
    lines += ['']
    for t in tools:
        if t['note']:
            lines.append(f"- {t['name']}: {t['note']}")
    lines += ['', '## Licence texts', '']
    for t in tools:
        for f in t['files']:
            lines += [f"### {t['name']}: {os.path.basename(f)}", '', '```', read(f), '```', '']
    for r in rows:
        for f in r['files']:
            lines += [f"### {r['name']} {r['version']}: {os.path.relpath(f, os.path.dirname(os.path.dirname(f))).replace(os.sep, '/')}", '', '```', read(f), '```', '']
    return '\n'.join(lines) + '\n'


def read(path: str) -> str:
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read().rstrip()


def generate(bundle: str, python_exe: str, platform: str, third: dict, skip: set[str] | None = None) -> dict:
    """Write THIRD_PARTY_NOTICES.md into the bundle and return the summary; raise SystemExit on a
    package whose licence the policy does not allow."""
    policy = load_policy()
    sp = site_packages(python_exe)
    rows, problems = collect_packages(sp, policy, {s.lower() for s in (skip or set(policy.get('first_party', [])))})
    if problems:
        raise SystemExit('licence check failed:\n  ' + '\n  '.join(problems)
                         + f'\nAllowed: {", ".join(policy["allowed"])}. Add an override with a reason to {POLICY} only after legal review.')
    tools = tool_notices(bundle, platform, third, policy)
    text = render(rows, tools, os.path.basename(bundle.rstrip(os.sep)))
    out = os.path.join(bundle, NOTICES)
    with open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    licenses = sorted({r['license'] for r in rows})
    return {'file': NOTICES, 'packages': len(rows), 'licenses': licenses,
            'overrides': [r['name'] for r in rows if r['verdict'] == 'allowed (override)'],
            'tools': [{'name': t['name'], 'license': t['license']} for t in tools]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='licence check and third-party notices for an interpreter')
    ap.add_argument('--python', default=sys.executable)
    ap.add_argument('--out', default=None, help='write the notices here (default: report only)')
    ap.add_argument('--platform', default='linux-x86_64')
    args = ap.parse_args(argv)
    policy = load_policy()
    rows, problems = collect_packages(site_packages(args.python), policy, {s.lower() for s in policy.get('first_party', [])})
    for r in rows:
        print(f"{r['name']:32} {r['version']:14} {r['license']:28} {r['verdict']}")
    print(f'{len(rows)} packages; {len(problems)} problem(s)')
    for p in problems:
        print('  ' + p)
    if args.out:
        with open(os.path.join(ROOT, 'lock', 'third-party.json'), encoding='utf-8') as fh:
            third = json.load(fh)
        tools = [] if args.platform not in third['python'] else tool_notices(os.path.dirname(args.out), args.platform, third, policy)
        with open(args.out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(render(rows, tools, os.path.basename(os.path.dirname(os.path.abspath(args.out)))))
        print('wrote', args.out)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
