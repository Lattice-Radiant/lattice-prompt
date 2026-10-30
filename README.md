# lattice-prompt

Release bundles of the Lattice architecture tooling for Windows and Linux:
`cortex-a2c` (the arch2code generator with its MCP server, Questa lint, native
SystemC and Verilator flow), `cortex-kb` (the knowledge base of verified
designs, IP Catalog cores, patterns and boards with its MCP server) and
`cortex-mcp` (the `lattice-cortex` server: Propel SoC sessions, IP facts,
firmware, validators and the replay of an arch2code SoC manifest), shipped
with a private Python and every package they need, so a user's own Python, if
any, plays no part. The fourth server of the integrated flow, the Radiant
server `lattice-radiant-mcp` (cortex-bridge), ships with its own installer and
is registered beside these (see the project template's `.mcp.json.example`).

This repository holds no product code. It pins the three components as
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
    cortex-kb/   git checkout at the pinned commit, filtered for distribution
                 (entries above the policy's classification limit and
                 export-controlled ones removed, vendored sources withheld;
                 see VERSION.json and the checkout's distribution.json); its
                 sources cache is created on first start under
                 %LOCALAPPDATA%\lattice-prompt
    cortex-mcp/  git checkout at the pinned commit (package lattice_prompt)
  bin/
    a2c-mcp.cmd      the arch2code MCP server (stdio)
    kb-mcp.cmd       the cortex-kb MCP server (stdio)
    lattice-cortex.cmd   the lattice-cortex MCP server (stdio)
    kb-skills.cmd    list, install and remove the knowledge base's design skills
    a2c-make.cmd     make with the bundle's tools on PATH
    a2c-shell.cmd    a command prompt with the bundle's tools on PATH
  install.cmd    registers the three servers with Claude Code and Claude Desktop
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
    a2c-mcp, kb-mcp, lattice-cortex, kb-skills, a2c-make, a2c-shell,
    new-project                                       POSIX sh launchers
  install.sh     registers the three servers with Claude Code and Claude Desktop
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
   `arch2code`, `cortex-kb` and `lattice-cortex` in `~/.claude.json`
   (Claude Code) and in the Claude Desktop configuration,
   backing both files up. An entry is recognised by what it runs, not by its
   key: the cortex-mcp installer's `lattice-prompt` entry, a development
   checkout under any name or an older bundle's launcher is a duplicate of the
   bundle server and is removed, with its `env` block (the Propel and Radiant
   locations) carried over, so Claude Code starts each server once;
   `--keep-duplicates` leaves them. `install.cmd --uninstall` removes the three
   bundle entries only. The knowledge-base server is registered with its authoring
   tools (`kb_author_*`) by default, so Claude can add to the knowledge base as
   a design progresses; those tools write only to the local checkout until a
   pull request is opened. `install.cmd --read-only` registers it without them
   (a shared machine, or a server other people call).
   The knowledge base's reviewed **design skills** (procedures for changing a
   design) are not copied by the installer: every reviewed skill is an MCP
   prompt of the knowledge-base server (`/mcp__cortex-kb__<design>-<skill>` in
   Claude Code, listed the same way by Cursor and the other MCP clients, always
   the current version), and a project gets them deployed into every tool's
   skills folder by `bin\a2c-make agents-setup` (see "Start a project").
   `bin\kb-skills list` shows them; `bin\kb-skills install --all` remains as a
   fallback copy into `%USERPROFILE%\.claude\skills` for a session without a
   project.
3. Start a project: `bin\new-project.cmd <directory>` copies the project
   template (`templates\project`: Makefiles, the agent-rules appendix with the
   flow routing and knowledge-base rules, an empty `design\` for the flow's
   records, `.mcp.json.example`), names the project after the directory and
   initialises Git; `--submodule` pins cortex-a2c inside the project instead of
   building with the bundle's copy. Then `bin\a2c-make agents-setup` in the
   project: it exports the knowledge base's reviewed skills for the designs the
   project's `design\intent.yaml` names into `.kb\rules` and deploys them with
   the arch2code skills into `.claude\skills`, `.cursor`, `.gemini`, `.opencode`
   and `.agents`; rerun it after a knowledge-base update. Then open the project
   in Claude Code.
4. Optional, for native simulation (SystemC model and Verilator
   co-simulation): see [Native simulation](#native-simulation) below.
   Questa lint is found automatically under `C:\lscc` when Radiant is
   installed. Neither is part of the bundle.

Linux:

1. `tar xzf lattice-prompt-<version>-linux-x86_64.tar.gz` anywhere; make sure
   `git` and `make` are installed (`apt install git make` or the equivalent).
2. Run `./install.sh` from the extracted directory. It registers the same three
   servers in `~/.claude.json` and in `$XDG_CONFIG_HOME/Claude/claude_desktop_config.json`
   (default `~/.config`). `./install.sh --uninstall` removes them;
   `./install.sh --read-only` leaves out the knowledge-base authoring tools as above.
   Design skills are served as above (`bin/kb-skills list`, MCP prompts, and
   `bin/a2c-make agents-setup` in a project).
3. Start a project: `bin/new-project <directory>` (as above), then
   `bin/a2c-make agents-setup` in the project.
4. Optional, for native simulation: see [Native simulation](#native-simulation)
   below. Questa from the Radiant install.

On either platform `python smoke.py` (with the bundled interpreter) reruns
the checks the release build ran.

## Bundle size

The components are cloned shallow (the pinned commit only; the knowledge
base's version history is in its metadata, not in git), the knowledge base is
filtered through `export-bundle` (confidential and export-controlled entries
removed, vendored sources withheld), and `build/build.py --kb-design NAME` or
`--kb-family FAMILY` (repeatable; the release workflow's `kb_family` input)
produce a bundle that carries one team's designs, boards and device notes
only. `VERSION.json` records the selectors. Inside a bundle the knowledge
base's own size policy applies (its README, "Keeping the knowledge base
compact"): raw reports capped, an entry size budget, one session database.

## Third-party notices and licence policy

Every bundle carries `THIRD_PARTY_NOTICES.md` at its root: the Python packages
with their licences and licence texts, the bundled CPython, and on Windows Git
and GNU make (GPL programs invoked as separate commands, with the source
locations the licence requires). The build generates it (`build/notices.py`)
from the installed package metadata and refuses to build when a package
carries a licence outside the policy in `lock/licenses.json` (permissive
licences only: MIT, BSD, Apache-2.0, ISC, PSF, MPL-2.0 and the like); an
override there needs a reason and legal review. `python build/notices.py
--python <interpreter>` runs the check on any environment. The smoke test
confirms the notices file names every bundled package. Distribution outside
Lattice remains subject to legal and export-control review of the knowledge
base content; the classification filter is the mechanism, not the approval.

## Native simulation

The generator, the three MCP servers, Questa lint and everything the smoke test
covers work with the bundle alone. Building and running a SystemC model, or
the Verilator co-simulation of a block (`make -C rundir run VL_DUT=1`), also
needs a C++ toolchain, SystemC, Boost and Verilator. They are not bundled:
on Windows they come from MSYS2, on Linux from the distribution or a site
install. One-time setup per machine, in the bundle's directory
(`<bundle>` below):

### Windows (MSYS2 clang64)

1. Install MSYS2 and the toolchain packages. In a command prompt:

   ```
   winget install --id MSYS2.MSYS2
   ```

   then in the MSYS2 clang64 shell (`C:\msys64\clang64.exe`):

   ```
   pacman -Syu --needed mingw-w64-clang-x86_64-clang mingw-w64-clang-x86_64-lld \
       mingw-w64-clang-x86_64-make mingw-w64-clang-x86_64-cmake \
       mingw-w64-clang-x86_64-ninja mingw-w64-clang-x86_64-boost \
       mingw-w64-clang-x86_64-fmt mingw-w64-clang-x86_64-verilator perl
   ```

   Verilator 5.050 or newer is required (older releases do not compile as
   C++23 under libc++); `pacman -Syu` first if the mirror offers an older one.

2. Install SystemC and finish the Verilator setup. In the same clang64 shell,
   with the bundle at `C:\lattice-prompt` for example:

   ```
   /c/lattice-prompt/components/cortex-a2c/scripts/windows/setup-systemc-msys2.sh
   ```

   The script installs MSYS2's SystemC 3.0 package, repacks it into a static
   library the model links without a DLL, checks the Verilator version and
   raises the stack reserve of `verilator_bin.exe` (its default 1 MB
   overflows on real designs). Rerun it after a Verilator package update.

3. Verify. In a command prompt, from the bundle directory:

   ```
   bin\a2c-make -C components\cortex-a2c\examples\helloWorld\rundir -j4 all
   bin\a2c-make -C components\cortex-a2c\examples\helloWorld\rundir run
   ```

   The run ends with `No error`. In Claude, the `toolchain_detect` tool of the
   `arch2code` server reports the same toolchain state.

The makefiles find MSYS2 under `C:\msys64` (`A2C_MSYS2_ROOT` overrides the
location) and set `SYSTEMC_INCLUDE`, `SYSTEMC_LIBDIR`, `BOOST_INCLUDE`,
`BOOST_LIBS` and `VERILATOR_ROOT` from it, so no environment variables are
needed. Behind a TLS-inspecting proxy, `pacman` needs the proxy's CA chain
in `/etc/pki/ca-trust/source/anchors/` followed by `update-ca-trust`.

### Linux

1. Install a C++ compiler (clang++ is the default; `A2C_CLANG` names another
   compiler), Boost with `program_options`, Verilator 5.x and SystemC 2.3.4
   or 3.0 from the distribution or a site install. On Ubuntu 24.04 the
   distribution packages are `clang`, `libboost-program-options-dev`,
   `verilator` and `libsystemc-dev`.
2. Export where they are; the makefiles stop with a message naming the
   variable if one is missing:

   ```
   export SYSTEMC_INCLUDE=/usr/include
   export SYSTEMC_LIBDIR=/usr/lib
   export BOOST_INCLUDE=/usr/include/boost
   export LD_BOOST=/usr/lib/x86_64-linux-gnu
   ```

   (These are the values of the arch2code development image; a site install
   under another prefix uses its `include` and `lib` directories.)
3. Verify, from the bundle directory:

   ```
   bin/a2c-make -C components/cortex-a2c/examples/helloWorld/rundir -j4 all
   bin/a2c-make -C components/cortex-a2c/examples/helloWorld/rundir run
   ```

The full reference is `components/cortex-a2c/document/source/modules/ROOT/pages/runOnWindows.adoc`
(Windows) and the arch2code documentation under `components/cortex-a2c/document`.

## Build a release

A bundle is built on its own platform, because the packages are installed by
running the bundled interpreter. Locally, from a checkout with the
submodules initialised:

```
python build/build.py --version <version> [--platform win64|linux-x86_64] [--make-exe <path to make.exe>]
```

`--platform` defaults to the host. The build downloads the runtime (and, on
Windows, MinGit) named in `lock/third-party.json` (verifying their SHA-256),
clones the three components at their pinned commits (cortex-mcp from its
`flow_integration` branch until that branch is merged), installs the packages from
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

## Bundle profiles

`--profile internal` (the default) filters the bundled knowledge base at the
classification limit of its policy (`seed/policy.yaml`,
`distribution.max_classification`). `--profile customer` is the bundle a
customer runs in the algorithm-to-SoC flow (decision 3 and section 8.3 of
`plans/algorithm-to-soc-flow.md` in cortex-a2c): the knowledge base is filtered
at `public`, the archive is named `lattice-prompt-<version>-customer-<platform>`,
`VERSION.json` records `"profile": "customer"` and the limit applied, and
`smoke.py` fails the build when any bundled entry declares a classification
above public. The `release` workflow takes the profile as an input.

## Updating the pins

```
git -C components/cortex-a2c fetch && git -C components/cortex-a2c checkout <tag or commit>
git -C components/cortex-kb  fetch && git -C components/cortex-kb  checkout <tag or commit>
git add components && git commit -m "Pin cortex-a2c <x>, cortex-kb <y>"
```

A release is a commit of this repository: its tag names the product version,
and `VERSION.json` in the bundle names the component commits.
