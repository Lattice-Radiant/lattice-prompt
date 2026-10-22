"""Register the bundled MCP servers with Claude Code and Claude Desktop.

Run with the bundled Python (install.cmd or install.sh does): it writes the
three entries `arch2code`, `cortex-kb` and `lattice-cortex`, each pointing at a
launcher in this bundle's bin directory, into ~/.claude.json (Claude Code, user
scope) and into the Claude Desktop configuration, backing both files up first;
an entry of the same name from a development checkout is replaced. --uninstall
removes the three entries. cortex-kb is registered
with its authoring tools (kb_author_*) by default, so Claude can add to the
knowledge base as a design progresses; the tools write only to the local
checkout until a pull request. --read-only registers the server without them
(a shared machine or a server other people call).

The knowledge base's reviewed design skills are not copied anywhere: every
reviewed skill is an MCP prompt of the cortex-kb server (invoked by name from
Claude Code, Cursor and the other MCP clients, always the current version),
and a project gets them deployed into every tool's skills folder by
`bin/kb-skills export-dir` plus `make agents-setup` (bin/new-project sets this
up). Nothing else on the machine is touched.
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
    'lattice-cortex': os.path.join(HERE, 'bin', 'lattice-cortex' + EXT),
}


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='register the lattice-prompt MCP servers')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--no-desktop', action='store_true', help='Claude Code only')
    parser.add_argument('--authoring', action='store_true', default=True,
                        help='start the cortex-kb server with its authoring tools (kb_author_*), so Claude can '
                             'add to the knowledge base as the design progresses (the default for a personal '
                             'session; the tools write only to the local checkout until a pull request)')
    parser.add_argument('--read-only', dest='authoring', action='store_false',
                        help='register the cortex-kb server without the authoring tools (a shared machine or server)')
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
        print(f'{path}: registered {list(SERVERS)}' + (' (cortex-kb with authoring tools)' if args.authoring else ' (cortex-kb read-only)'))
    if not args.uninstall:
        print('skills: reviewed design skills are served by the cortex-kb server as prompts; '
              'a project deploys them with bin/kb-skills export-dir and make agents-setup (see README)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
