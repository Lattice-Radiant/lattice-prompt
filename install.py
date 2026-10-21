"""Register the bundled MCP servers with Claude Code and Claude Desktop, and install skills.

Run with the bundled Python (install.cmd or install.sh does): it writes an `arch2code` and a
`cortex-kb` entry, each pointing at a launcher in this bundle's bin
directory, into ~/.claude.json (Claude Code, user scope) and into the Claude
Desktop configuration, backing both files up first. --uninstall removes the
two entries and the skills a previous run installed. --authoring registers
cortex-kb with its authoring tools (kb_author_*), so Claude can add designs
to the knowledge base from a session; without it the server is read-only.

Skills: the knowledge base carries reviewed procedures for changing its
designs (design skills) in the Claude Code skill format. --skills all|select|none
installs them into ~/.claude/skills as <design>-<skill>/; without the option,
on a console, the installer lists them and asks. Nothing else on the machine
is touched.
"""

import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WINDOWS = sys.platform == 'win32'
EXT = '.cmd' if WINDOWS else ''          # Linux launchers are shell scripts without a suffix
SERVERS = {
    'arch2code': os.path.join(HERE, 'bin', 'a2c-mcp' + EXT),
    'cortex-kb': os.path.join(HERE, 'bin', 'kb-mcp' + EXT),
}
KB_REPO = os.path.join(HERE, 'components', 'cortex-kb')
SKILLS_LAUNCHER = 'bin\\kb-skills' if WINDOWS else 'bin/kb-skills'


def config_files(desktop: bool):
    files = [os.path.join(os.path.expanduser('~'), '.claude.json')]
    if desktop:
        if WINDOWS:
            appdata = os.environ.get('APPDATA')
            if appdata:
                files.append(os.path.join(appdata, 'Claude', 'claude_desktop_config.json'))
        else:
            config_home = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
            files.append(os.path.join(config_home, 'Claude', 'claude_desktop_config.json'))
    return files


def load(path):
    if not os.path.isfile(path):
        return {}
    with open(path, encoding='utf-8') as fh:
        text = fh.read()
    return json.loads(text) if text.strip() else {}


def save(path, data):
    if os.path.isfile(path):
        shutil.copy2(path, f'{path}.bak-{time.strftime("%Y%m%d-%H%M%S")}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)
        fh.write('\n')


def _kb_skills():
    """The knowledge base's skill helpers, from the bundled packages; None when unavailable."""
    try:
        from kbtools import skills  # noqa: PLC0415 - the bundled interpreter has it
    except ImportError:
        return None
    return skills


def skills_prompt(available, ask=input):
    """Console dialogue: all, a selection (numbers or design/skill names), or none."""
    print('Claude Code skills in the knowledge base (procedures for changing its designs):')
    for i, s in enumerate(available, 1):
        print(f'  {i:2d}. {s["key"]}: {s["description"][:90]}')
    while True:
        answer = ask('Install skills? [a]ll / [s]elect / [n]one: ').strip().lower()
        if answer in ('a', 'all'):
            return [s['key'] for s in available]
        if answer in ('n', 'none', ''):
            return []
        if answer in ('s', 'select'):
            raw = ask('Numbers or design/skill names, comma-separated: ')
            chosen = []
            bad = []
            for item in (x.strip() for x in raw.split(',') if x.strip()):
                if item.isdigit() and 1 <= int(item) <= len(available):
                    chosen.append(available[int(item) - 1]['key'])
                elif any(item == s['key'] for s in available):
                    chosen.append(item)
                else:
                    bad.append(item)
            if bad:
                print(f'unknown: {", ".join(bad)}')
                continue
            return chosen
        print('answer a, s or n')


def install_selected(mode, select, interactive, ask=input):
    skills = _kb_skills()
    if skills is None:
        print(f'skills: the knowledge base package is not importable here; run {SKILLS_LAUNCHER} install later', file=sys.stderr)
        return 0
    available = skills.installable_skills(KB_REPO)
    if not available:
        print('skills: the knowledge base carries no reviewed skills yet')
        return 0
    if mode is None:
        if not interactive:
            print(f'skills: {len(available)} available; none installed (no console). Later: {SKILLS_LAUNCHER} list, {SKILLS_LAUNCHER} install --all')
            return 0
        keys = skills_prompt(available, ask)
    elif mode == 'all':
        keys = [s['key'] for s in available]
    elif mode == 'select':
        keys = [x.strip() for x in (select or '').split(',') if x.strip()]
        if not keys:
            print('--skills select needs --skills-select design/skill[,design/skill...]', file=sys.stderr)
            return 1
    else:
        keys = []
    if not keys:
        print(f'skills: none installed ({len(available)} available; {SKILLS_LAUNCHER} install --all later)')
        return 0
    try:
        out = skills.install_skills(KB_REPO, None, select=keys)
    except ValueError as exc:
        print(f'skills: {exc}', file=sys.stderr)
        return 1
    print(f'skills: installed {len(out["installed"])} into {out["dest"]}: {", ".join(out["installed"])}')
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='register the lattice-prompt MCP servers and install skills')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--no-desktop', action='store_true', help='Claude Code only')
    parser.add_argument('--authoring', action='store_true',
                        help='start the cortex-kb server with its authoring tools (kb_author_*), so Claude can '
                             'add designs to the knowledge base; the default server is read-only')
    parser.add_argument('--skills', choices=['all', 'select', 'none'], default=None,
                        help='install the knowledge base\'s reviewed Claude Code skills: all, a selection '
                             '(--skills-select), or none; without the option a console asks')
    parser.add_argument('--skills-select', default=None, metavar='LIST', help='comma-separated design/skill names for --skills select')
    args = parser.parse_args(argv)
    server_args = {'cortex-kb': ['--authoring'] if args.authoring else []}

    for name, launcher in SERVERS.items():
        if not args.uninstall and not os.path.isfile(launcher):
            print(f'missing launcher {launcher}', file=sys.stderr)
            return 1
    for path in config_files(not args.no_desktop):
        data = load(path)
        servers = data.setdefault('mcpServers', {})
        if args.uninstall:
            removed = [n for n in SERVERS if servers.pop(n, None) is not None]
            if removed:
                save(path, data)
            print(f'{path}: removed {removed or "nothing"}')
            continue
        for name, launcher in SERVERS.items():
            servers[name] = {'command': launcher, 'args': server_args.get(name, [])}
        save(path, data)
        print(f'{path}: registered {list(SERVERS)}' + (' (cortex-kb with authoring tools)' if args.authoring else ''))
    if args.uninstall:
        skills = _kb_skills()
        if skills is not None:
            out = skills.uninstall_skills()
            print(f'skills: removed {len(out["removed"])} from {out["dest"]}')
        return 0
    interactive = sys.stdin is not None and sys.stdin.isatty()
    return install_selected(args.skills, args.skills_select, interactive)


if __name__ == '__main__':
    sys.exit(main())
