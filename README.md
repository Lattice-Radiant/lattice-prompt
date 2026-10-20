# lattice-prompt

Release bundles of the Lattice architecture tooling for Windows and Linux:
`cortex-a2c` (the arch2code generator with its MCP server, Questa lint, native
SystemC and Verilator flow) and `cortex-kb` (the knowledge base of verified
designs, IP Catalog cores, patterns and boards with its MCP server), shipped
with a private Python and every package they need, so a user's own Python, if
any, plays no part.

This repository holds no product code. It pins the two components as
submodules, carries the packaging layer (launchers, installer, smoke test,
release workflow) and records, per release, exactly what was bundled.

## Layout of a release

Windows (`lattice-prompt-<version>-win64.zip`):

```
lattice-prompt-<version>-win64/
  python/        CPython 3.12 (python-build-standalone, relocatable) with
                 every package pre-installed; never on the user's PATH
  git/           MinGit (the makefiles and the knowledge base call git)
  tools/         GNU make
  components/
    cortex-a2c/  git checkout at the pinned commit
    cortex-kb/   git checkout at the pinned commit (its sources cache is
                 created on first start under %LOCALAPPDATA%\lattice-prompt)
  bin/
    a2c-mcp.cmd      the arch2code MCP server (stdio)
    kb-mcp.cmd       the cortex-kb MCP server (stdio)
    a2c-make.cmd     make with the bundle's tools on PATH
    a2c-shell.cmd    a command prompt with the bundle's tools on PATH
  install.cmd    registers both servers with Claude Code and Claude Desktop
  smoke.py       the checks the release build ran
  VERSION.json   component commits, runtime and tool versions, checksums
```

Linux x86_64 (`lattice-prompt-<version>-linux-x86_64.tar.gz`, glibc 2.17 or
newer, so any distribution from 2014 on):

```
lattice-prompt-<version>-linux-x86_64/
  python/        CPython 3.12 (python-build-standalone, relocatable) with
                 every package pre-installed; bin/python3
  components/    as on Windows (the knowledge base cache goes under
                 $XDG_CACHE_HOME/lattice-prompt, default ~/.cache)
  bin/
    a2c-mcp, kb-mcp, a2c-make, a2c-shell   POSIX sh launchers
  install.sh     registers both servers with Claude Code and Claude Desktop
  smoke.py, VERSION.json
```

The Linux bundle does not carry git or make: every distribution provides
them (`git`, `make` packages), and the native simulation flow needs the
distribution's C++ toolchain, SystemC and Verilator in any case.

Every launcher puts the bundle's own `python` (and, on Windows, `git` and
`tools`) first on `PATH` and starts the bundled interpreter by absolute path.
The bundle can live in any directory; nothing in it records its install
location.

## Install on a user's machine

Windows:

1. Unzip `lattice-prompt-<version>-win64.zip` anywhere (no administrator rights).
2. Run `install.cmd` (it runs `install.py` with the bundled Python). It registers
   `arch2code` and `cortex-kb` in `~/.claude.json` (Claude Code) and in the
   Claude Desktop configuration, backing both files up. `install.cmd --uninstall`
   removes them.
3. Optional, for native simulation: install the MSYS2 clang64 toolchain as
   described in `components/cortex-a2c/document/source/modules/ROOT/pages/runOnWindows.adoc`
   (`winget install MSYS2.MSYS2`, the pacman packages, then
   `scripts/windows/setup-systemc-msys2.sh`). Questa is found automatically
   under `C:\lscc` when Radiant is installed. Neither is part of the bundle.

Linux:

1. `tar xzf lattice-prompt-<version>-linux-x86_64.tar.gz` anywhere; make sure
   `git` and `make` are installed (`apt install git make` or the equivalent).
2. Run `./install.sh` from the extracted directory. It registers the same two
   servers in `~/.claude.json` and in `$XDG_CONFIG_HOME/Claude/claude_desktop_config.json`
   (default `~/.config`). `./install.sh --uninstall` removes them.
3. Optional, for native simulation: a C++ compiler, SystemC and Verilator as
   described in the cortex-a2c documentation; Questa from the Radiant install.

On either platform `python smoke.py` (with the bundled interpreter) reruns
the checks the release build ran.

## Build a release

A bundle is built on its own platform, because the packages are installed by
running the bundled interpreter. Locally, from a checkout with the
submodules initialised:

```
python build/build.py --version <version> [--platform win64|linux-x86_64] [--make-exe <path to make.exe>]
```

`--platform` defaults to the host. The build downloads the runtime (and, on
Windows, MinGit) named in `lock/third-party.json` (verifying their SHA-256),
clones the two components at their pinned commits, installs the packages from
`lock/requirements.lock` into the bundled Python (or writes that lock on the
first build), runs `smoke.py` inside the bundle and writes the archive with a
checksum file: `dist/lattice-prompt-<version>-win64.zip` or
`dist/lattice-prompt-<version>-linux-x86_64.tar.gz`.
Behind a proxy that inspects TLS, pass `--pip-cert <CA bundle>` (or set
`PIP_CERT`). Re-resolving the lock (delete `lock/requirements.lock` first)
honours `lock/constraints.txt`; `--seed-from <python>` additionally
constrains the resolution to the versions installed in that interpreter, so
a network that refuses new downloads can still resolve from pip's cache. The
lock is shared by both platforms: it pins versions, and pip picks each
platform's wheel.

In CI, the `release` workflow builds both bundles (a Windows and a Linux
runner) when dispatched with a version, and with `publish` attaches both
archives to a GitHub release of this repository. Private submodules need a
token with read access to both component repositories in the
`COMPONENTS_TOKEN` secret.

## Updating the pins

```
git -C components/cortex-a2c fetch && git -C components/cortex-a2c checkout <tag or commit>
git -C components/cortex-kb  fetch && git -C components/cortex-kb  checkout <tag or commit>
git add components && git commit -m "Pin cortex-a2c <x>, cortex-kb <y>"
```

A release is a commit of this repository: its tag names the product version,
and `VERSION.json` in the bundle names the component commits.
