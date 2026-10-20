"""Register the bundled MCP servers with Claude Code and Claude Desktop.

Run with the bundled Python (install.cmd does): it writes an `arch2code` and a
`cortex-kb` entry, each pointing at a launcher in this bundle's bin
directory, into ~/.claude.json (Claude Code, user scope) and into the Claude
Desktop configuration, backing both files up first. --uninstall removes the
two entries. Nothing else on the machine is touched.
"""

import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVERS = {
    'arch2code': os.path.join(HERE, 'bin', 'a2c-mcp.cmd'),
    'cortex-kb': os.path.join(HERE, 'bin', 'kb-mcp.cmd'),
}


def config_files(desktop: bool):
    files = [os.path.join(os.path.expanduser('~'), '.claude.json')]
    if desktop:
        appdata = os.environ.get('APPDATA')
        if appdata:
            files.append(os.path.join(appdata, 'Claude', 'claude_desktop_config.json'))
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
    args = parser.parse_args(argv)

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
            servers[name] = {'command': launcher, 'args': []}
        save(path, data)
        print(f'{path}: registered {list(SERVERS)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
