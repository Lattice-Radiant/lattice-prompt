"""Register the bundled MCP servers with Claude Code and Claude Desktop.

Run with the bundled Python (install.cmd or install.sh does): it writes the
four entries `lattice-arch2code-mcp`, `lattice-knowledge-db`,
`lattice-propel-mcp` and `lattice-radiant-mcp`, each pointing at a launcher in
this bundle's bin directory, into ~/.claude.json (Claude Code, user scope) and
into the Claude Desktop configuration, backing both files up first.

The servers were renamed on 2026-10-30 (arch2code, cortex-kb, lattice-cortex,
and radiant or lattice-radiant-mcp from its own installer). An entry is
recognised by what it runs, not by its key: any existing entry that starts one
of these servers (an older bundle's `arch2code`, `cortex-kb` or
`lattice-cortex` entry, the cortex-mcp installer's `lattice-prompt` entry
running `-m lattice_prompt.server`, a `radiant` or `lattice-radiant-mcp` entry
from the Radiant installer running `-m radiant_mcp`, a development checkout
under any name) is an old entry of the bundle server and is removed, so Claude
Code starts each server once, under its new name. The old entry's `env` block
(the cortex-mcp installer keeps LATTICE_PROPEL_BASE and LATTICE_RADIANT there,
the Radiant installer RADIANT_* and the timing-closure settings) is carried
over to the new entry. Project-scope entries in ~/.claude.json
(projects.<path>.mcpServers) that run a bundle server are removed as well, since
Claude Code would start them beside the user-scope entries. --keep-duplicates
leaves all of those alone; --uninstall removes the bundle entries, under their
new and old names.

The knowledge base server is registered with its authoring tools (kb_author_*)
by default, so Claude can add to the knowledge base as a design progresses; the
tools write only to the local checkout until a pull request. --read-only
registers the server without them (a shared machine or a server other people
call).

The knowledge base's reviewed design skills are not copied anywhere: every
reviewed skill is an MCP prompt of the lattice-knowledge-db server, and a
project gets them deployed into every tool's skills folder by
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
    'lattice-arch2code-mcp': os.path.join(HERE, 'bin', 'lattice-arch2code-mcp' + EXT),
    'lattice-knowledge-db': os.path.join(HERE, 'bin', 'lattice-knowledge-db' + EXT),
    'lattice-propel-mcp': os.path.join(HERE, 'bin', 'lattice-propel-mcp' + EXT),
    'lattice-radiant-mcp': os.path.join(HERE, 'bin', 'lattice-radiant-mcp' + EXT),
}

# The keys the same servers were registered under before the rename (by an
# older bundle, the cortex-mcp installer and the Radiant installer).
OLD_KEYS = {
    'lattice-arch2code-mcp': ('arch2code',),
    'lattice-knowledge-db': ('cortex-kb',),
    'lattice-propel-mcp': ('lattice-cortex', 'lattice-prompt'),
    'lattice-radiant-mcp': ('radiant',),
}

# What each server runs, under any key and from any installation: the module
# behind `-m`, the console script, or a bundle launcher (the current one and the
# one an older bundle shipped). A token of an entry's command or arguments that
# matches one of these names identifies the server.
SIGNATURES = {
    'lattice-arch2code-mcp': {'arch2code_mcp', 'arch2code_mcp.server', 'arch2code-mcp', 'a2c-mcp',
                              'lattice-arch2code-mcp'},
    'lattice-knowledge-db': {'kbtools.mcp_server', 'kbtools.cli', 'cortex-kb', 'kb-mcp', 'lattice-knowledge-db'},
    'lattice-propel-mcp': {'lattice_prompt.server', 'lattice_cortex.server', 'lattice-prompt-mcp', 'lattice-cortex',
                           'lattice-propel-mcp'},
    'lattice-radiant-mcp': {'radiant_mcp', 'radiant_mcp.server', 'radiant-mcp', 'lattice-radiant-mcp'},
}
MODULES_IN_SNIPPETS = ('kbtools.cli', 'kbtools.mcp_server', 'lattice_prompt.server', 'lattice_cortex.server',
                       'arch2code_mcp', 'radiant_mcp')
KB = 'lattice-knowledge-db'

# Settings that are never carried over to the bundle entry. The Radiant installer's
# timing-closure merge (TIMING_CLOSURE_MERGE_ENABLED and the CORTEX_TIMING_CLOSURE_MCP_*
# allowlist) needs packages the bundle does not ship (cortex-agent-impl and
# cortex-framework); carried over, the server would try to load them at every start.
DROPPED_ENV = ('TIMING_CLOSURE_MERGE_ENABLED',)
DROPPED_ENV_PREFIXES = ('CORTEX_TIMING_CLOSURE_MCP_',)


def _kept(var):
    return var not in DROPPED_ENV and not var.startswith(DROPPED_ENV_PREFIXES)


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


def _tokens(entry):
    """The names an entry can be recognised by: the basename of its command without
    extension and every argument, plus each argument's basename; a `-c` snippet
    (python -c "from kbtools.cli import main; main()") is searched for module names."""
    out = set()
    values = [str(entry.get('command', ''))] + [str(a) for a in (entry.get('args') or [])]
    for value in values:
        out.add(value.lower())
        base = os.path.basename(value.replace('\\', '/'))
        out.add(base.lower())
        out.add(os.path.splitext(base)[0].lower())
        if 'import' in value:
            out.update(m for m in MODULES_IN_SNIPPETS if m in value)
    return out


def identify(entry):
    """The bundle server this entry runs, or None."""
    if not isinstance(entry, dict):
        return None
    tokens = _tokens(entry)
    for name, names in SIGNATURES.items():
        if tokens & names:
            return name
    return None


def duplicates(servers):
    """{bundle server: [keys of other entries running it]}: old keys and any other key."""
    found = {name: [] for name in SERVERS}
    for key, entry in servers.items():
        name = identify(entry)
        if name and key != name:
            found[name].append(key)
    return found


def register(servers, server_args, keep_duplicates=False):
    """Write the bundle entries into one mcpServers table. Returns (removed, migrated)."""
    removed, migrated = [], []
    dups = duplicates(servers)
    for name, launcher in SERVERS.items():
        entry = {'command': launcher, 'args': server_args.get(name, [])}
        env = {}
        previous = servers.get(name) or {}
        if isinstance(previous.get('env'), dict):      # an earlier run, or another install under the new key
            env.update({k: v for k, v in previous['env'].items() if _kept(k)})
        if not keep_duplicates:
            for key in dups[name]:
                old = servers.pop(key)
                removed.append(key)
                if isinstance(old.get('env'), dict) and old['env']:
                    for var, value in old['env'].items():
                        if _kept(var):
                            env.setdefault(var, value)  # the entry already under the new key wins
                    migrated.append(f'{key}.env -> {name}')
        if env:
            entry['env'] = env
        servers[name] = entry
    return removed, migrated


def unregister(servers):
    """Remove the bundle entries under their new keys, and the old keys when they run a bundle server."""
    removed = []
    for name in SERVERS:
        if servers.pop(name, None) is not None:
            removed.append(name)
        for key in OLD_KEYS[name]:
            if key in servers and identify(servers[key]) == name:
                servers.pop(key)
                removed.append(key)
    return removed


def prune_projects(data):
    """Remove project-scope entries (~/.claude.json projects.<path>.mcpServers) that run a bundle
    server: Claude Code starts those beside the user-scope entries. Returns ['<path>: <key>', ...]."""
    removed = []
    for path, project in (data.get('projects') or {}).items():
        servers = project.get('mcpServers') if isinstance(project, dict) else None
        if not isinstance(servers, dict):
            continue
        for key in [k for k, entry in servers.items() if identify(entry)]:
            servers.pop(key)
            removed.append(f'{path}: {key}')
    return removed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='register the lattice-prompt MCP servers')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--no-desktop', action='store_true', help='Claude Code only')
    parser.add_argument('--authoring', action='store_true', default=True,
                        help='start the lattice-knowledge-db server with its authoring tools (kb_author_*), so '
                             'Claude can add to the knowledge base as the design progresses (the default for a '
                             'personal session; the tools write only to the local checkout until a pull request)')
    parser.add_argument('--read-only', dest='authoring', action='store_false',
                        help='register the lattice-knowledge-db server without the authoring tools (a shared '
                             'machine or server)')
    parser.add_argument('--keep-duplicates', action='store_true',
                        help='leave other entries that run the same servers in place (old keys such as arch2code, '
                             'cortex-kb, lattice-cortex, lattice-prompt and radiant, development checkouts, '
                             'project-scope entries); by default they are removed and their env block is carried '
                             'over, so each server starts once, under its new name')
    args = parser.parse_args(argv)
    server_args = {KB: ['--authoring'] if args.authoring else []}

    for name, launcher in SERVERS.items():
        if not args.uninstall and not os.path.isfile(launcher):
            print(f'missing launcher {launcher}', file=sys.stderr)
            return 1

    user_config = os.path.join(os.path.expanduser('~'), '.claude.json')
    for path in config_files(not args.no_desktop):
        data = load(path)
        servers = data.setdefault('mcpServers', {})
        if args.uninstall:
            removed = unregister(servers)
            if removed:
                save(path, data)
            print(f'{path}: removed {removed or "nothing"}')
            continue
        left = [k for keys in duplicates(servers).values() for k in keys] if args.keep_duplicates else []
        removed, migrated = register(servers, server_args, args.keep_duplicates)
        projects = prune_projects(data) if path == user_config and not args.keep_duplicates else []
        save(path, data)
        print(f'{path}: registered {list(SERVERS)}' + (f' ({KB} with authoring tools)' if args.authoring
                                                       else f' ({KB} read-only)'))
        if removed:
            print(f'{path}: removed old entries running the same servers: {removed}')
        if projects:
            print(f'{path}: removed project-scope entries running the same servers: {projects}')
        if migrated:
            print(f'{path}: carried over environment: {migrated}')
        if left:
            print(f'{path}: duplicates left in place (--keep-duplicates): {left}')

    if not args.uninstall:
        project = os.path.join(os.getcwd(), '.mcp.json')
        if os.path.isfile(project):
            try:
                extra = [k for keys in duplicates(load(project).get('mcpServers', {})).values() for k in keys]
            except (OSError, ValueError):
                extra = []
            if extra:
                print(f'note: {project} also registers {extra} for this project; Claude Code starts those '
                      'beside the user-scope entries. Remove them or point them at this bundle.')
        print(f'skills: reviewed design skills are served by the {KB} server as prompts; '
              'a project deploys them with bin/kb-skills export-dir and make agents-setup (see README)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
