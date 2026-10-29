Bundles of the Lattice architecture tooling: `cortex-a2c` (the arch2code
generator with its MCP server, Questa lint, SystemC and Verilator flow),
`cortex-kb` (the knowledge base of verified designs, IP Catalog cores,
patterns and boards with its MCP server) and `cortex-mcp` (the
`lattice-cortex` server: Propel SoC sessions, IP facts, firmware, validators,
SoC manifest replay), with a private Python 3.12 and every package they need.
A user's own Python, if any, plays no part. The Radiant server
`lattice-radiant-mcp` (cortex-bridge) ships with its own installer and is
registered beside these.

## Assets

- `lattice-prompt-<version>-win64.zip`: Windows x64; includes Git and GNU make.
- `lattice-prompt-<version>-linux-x86_64.tar.gz`: Linux x86_64, glibc 2.17 or
  newer; uses the distribution's `git` and `make`.
- `.sha256` files for both.

`VERSION.json` inside each bundle names the component commits and the
runtime and tool versions that were bundled. The knowledge base inside a
bundle is a filtered checkout: entries classified above `internal` and
export-controlled entries are removed, and vendored sources are withheld
(those designs are carried as derived knowledge only). `VERSION.json`
records the filter, the removed entries and the knowledge-base commit the
bundle was filtered from.

## Third-party notices

`THIRD_PARTY_NOTICES.md` at the bundle root lists every redistributed
package with its licence and licence text, the bundled CPython, and on
Windows Git for Windows (GPL-2.0) and GNU make (GPL-3.0) with the locations
of their source code. The build enforces a permissive-licence policy
(`lock/licenses.json`) on the Python packages.

## Install

Windows: unzip anywhere, run `install.cmd`. Linux: `tar xzf` anywhere, run
`./install.sh`. Either registers the `arch2code`, `cortex-kb` and
`lattice-cortex` MCP servers with Claude Code (`~/.claude.json`) and Claude
Desktop, backing the files up. Entries are recognised by what they run: the
cortex-mcp installer's `lattice-prompt` entry, a development checkout under any
name or an older bundle's launcher is removed as a duplicate and its `env`
block (Propel and Radiant locations) carried over, so each server starts once;
`--keep-duplicates` leaves them, `--uninstall` removes the bundle entries. The
knowledge-base server is registered
with its authoring tools by default, so Claude can add to the knowledge base
as a design progresses (the tools write only to the local checkout until a
pull request); `--read-only` registers it without them for a shared machine.
The knowledge base's reviewed design skills are served, not copied:
every reviewed skill is an MCP prompt of the knowledge-base server (invoked by
name from Claude Code, Cursor and the other MCP clients, always the current
version), and a project deploys them into every tool's skills folder with
`bin/a2c-make agents-setup` (through `bin/kb-skills export-dir`). `bin/kb-skills
list` shows them; `bin/kb-skills install --all` remains as a fallback copy for
a session without a project. `python smoke.py` with the bundled interpreter
reruns the release checks.

## Starting a project

`bin/new-project <directory>` (`bin\new-project.cmd` on Windows) creates an
arch2code project of the integrated design flow from `templates/project`:
Makefiles that build with the bundle's arch2code (or with `--submodule`, a
pinned cortex-a2c inside the project), the agent-rules appendix with the flow
routing and the knowledge-base rules, an empty `design/` for the flow's records
(intent, decomposition, decisions, IP bindings, gaps, hand-off), and
`.mcp.json.example` to pin the bundle's servers per project and to add the
Radiant server. Then `bin/a2c-make agents-setup`
in the project (it also exports and deploys the knowledge-base skills of the
designs the project names) and open it in Claude Code; the `design-from-intent`
skill runs the intake. `docs/integrated_flow_overview.pptx` in the repository presents
the flow.

## New in this release

- cortex-kb: performance knowledge with `kb_get_performance` and the two
  accelerator patterns of the algorithm-to-SoC entry mode (phase Q2); the
  benchmark plan for that entry mode; the reference design corpus registry
  lists the 119 repositories of the internal Reference-Design group as
  pending, and the registry writer keeps the file's comments; refreshed
  GitHub upstream status.
- cortex-mcp (`lattice-cortex`): Propel refreshes an interconnect's decode
  after address segments are assigned and checks it before compile (a
  headless SoC no longer faults on its first data access); `radiant_program`
  matches the project's Radiant console, uses an absolute chain path and
  surfaces the programmer log; `decode_sge` derives the ISA from the CPU's
  extension parameters; algorithm-to-SoC firmware support (portability scan,
  profiling harness, UART capture and profile parser; generated accelerator
  drivers join the device table, the self-test and the coverage check;
  `firmware_run_iss` runs the firmware on Renode with a platform derived from
  the SGE).

### Earlier releases (0.2.2, 0.2.1, 0.2.0)

- cortex-kb: the `cortex-kb` server answers the MCP handshake in under 3 s
  through `bin/kb-mcp` (0.2.1 took about 30 s, which tripped Claude Code's
  start-up timeout and made `claude mcp list` report the server as timed
  out). The server is created before its index build starts, and a
  `--skip-unresolved` build whose pinned sources are not in the cache (the
  bundle's offline default) is now cached and reused instead of being rebuilt
  on every start (cortex-kb pull request #15).

- Installer: duplicate entries that run the same server under another key
  (the cortex-mcp installer's `lattice-prompt`, development checkouts) are
  removed and their environment carried over; Claude Code no longer loads the
  lattice-cortex tool set twice. The project template's `.mcp.json.example`
  bundle paths are escaped correctly (0.2.0 carried control characters).

- `cortex-mcp` joins the bundle as the `lattice-cortex` server
  (`bin/lattice-cortex`); the installer registers it with `arch2code` and
  `cortex-kb`, and the project template's `.mcp.json.example` points the three
  entries at the bundle (the Radiant server keeps its own installer).
- arch2code: the SoC manifest generator (phase P5 of the integrated flow):
  `socProjects`, `socInstances`, `socInterconnections`, `socNets`,
  `socAddresses`, `socPorts`, `socConstants` and `socGlue` sections of the
  architecture YAML, `make soc-manifest`, the `soc_manifest` driver function
  and MCP tool, and `examples/socManifest`.
- cortex-mcp (`flow_integration` branch): `propel_replay_manifest` rebuilds a
  Propel SoC from an arch2code manifest (plan or execute), and
  `propel_compare_sbx_manifest` reports the deviations of an existing `.sbx`;
  `validate_build_schema` accepts a manifest.
- cortex-kb: the size policy that keeps a local installation compact
  (vendored-source and raw-report caps, the `entry_size` validation rule,
  cache pruning after a build and `cortex-kb cache-prune`, partial clones of
  the sources, `export-bundle --design/--family` selectors used by the
  bundle's `--kb-design/--kb-family` options).
- The third-party notices and the permissive-licence check cover the added
  server (first-party package `lattice-prompt-mcp-server`); `mcp` moves to
  1.29.1 for it.

## Native simulation (optional, not bundled)

Building a SystemC model or running the Verilator co-simulation needs a C++
toolchain, SystemC, Boost and Verilator on the machine.

- Windows: `winget install --id MSYS2.MSYS2`; in the clang64 shell install
  the `mingw-w64-clang-x86_64-{clang,lld,make,cmake,ninja,boost,fmt,verilator}`
  packages and `perl` (Verilator 5.050 or newer); then run
  `components/cortex-a2c/scripts/windows/setup-systemc-msys2.sh` from that
  shell. No environment variables are needed afterwards.
- Linux: clang++ (or `A2C_CLANG`), Boost `program_options`, Verilator 5.x and
  SystemC 2.3.4 or 3.0; export `SYSTEMC_INCLUDE`, `SYSTEMC_LIBDIR`,
  `BOOST_INCLUDE` and `LD_BOOST`.
- Verify with `bin/a2c-make -C components/cortex-a2c/examples/helloWorld/rundir all`
  then `... run` (ends with `No error`), or the `toolchain_detect` tool of
  the `arch2code` server in Claude.

The README in the bundle has the exact commands for both platforms.
