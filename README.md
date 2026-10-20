# lattice-prompt

Release bundle of the Lattice architecture tooling for Windows: `cortex-a2c`
(the arch2code generator with its MCP server, Questa lint, native SystemC and
Verilator flow) and `cortex-kb` (the knowledge base of verified designs, IP
Catalog cores, patterns and boards with its MCP server), shipped with a
private Python and every package they need, so a user's own Python, if any,
plays no part.

This repository holds no product code. It pins the two components as
submodules, carries the packaging layer (launchers, installer, smoke test,
release workflow) and records, per release, exactly what was bundled.

## Layout of a release

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
  install.py     registers both servers with Claude Code and Claude Desktop
  smoke.py       the checks the release build ran
  VERSION.json   component commits, runtime and tool versions, checksums
```

Every launcher sets `PATH` to the bundle's own `python`, `git` and `tools`
directories and starts the bundled interpreter by absolute path. The bundle
can live in any directory; nothing in it records its install location.

## Install on a user's machine

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

## Build a release

Locally, from a checkout with the submodules initialised:

```
python build/build.py --version <version> [--make-exe <path to make.exe>]
```

The build downloads the runtime and MinGit named in `lock/third-party.json`
(verifying their SHA-256), clones the two components at their pinned commits,
installs the packages from `lock/requirements.lock` into the bundled Python
(or writes that lock on the first build), runs `smoke.py` inside the bundle
and writes `dist/lattice-prompt-<version>-win64.zip` with a checksum file.
Behind a proxy that inspects TLS, pass `--pip-cert <CA bundle>` (or set
`PIP_CERT`). Re-resolving the lock (delete `lock/requirements.lock` first)
honours `lock/constraints.txt`; `--seed-from <python.exe>` additionally
constrains the resolution to the versions installed in that interpreter, so
a network that refuses new downloads can still resolve from pip's cache.

In CI, the `release` workflow does the same on a Windows runner when
dispatched with a version, and attaches the zip to a GitHub release of this
repository. Private submodules need a token with read access to both
component repositories in the `COMPONENTS_TOKEN` secret.

## Updating the pins

```
git -C components/cortex-a2c fetch && git -C components/cortex-a2c checkout <tag or commit>
git -C components/cortex-kb  fetch && git -C components/cortex-kb  checkout <tag or commit>
git add components && git commit -m "Pin cortex-a2c <x>, cortex-kb <y>"
```

A release is a commit of this repository: its tag names the product version,
and `VERSION.json` in the bundle names the component commits.
