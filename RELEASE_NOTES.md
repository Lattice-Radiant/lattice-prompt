Bundles of the Lattice architecture tooling: `cortex-a2c` (the arch2code
generator with its MCP server, Questa lint, SystemC and Verilator flow) and
`cortex-kb` (the knowledge base of verified designs, IP Catalog cores,
patterns and boards with its MCP server), with a private Python 3.12 and
every package they need. A user's own Python, if any, plays no part.

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

## Install

Windows: unzip anywhere, run `install.cmd`. Linux: `tar xzf` anywhere, run
`./install.sh`. Either registers the `arch2code` and `cortex-kb` MCP servers
with Claude Code (`~/.claude.json`) and Claude Desktop, backing the files up;
`--uninstall` removes the entries. The knowledge-base server is registered
with its authoring tools by default, so Claude can add to the knowledge base
as a design progresses (the tools write only to the local checkout until a
pull request); `--read-only` registers it without them for a shared machine.
The installer then offers the knowledge base's reviewed
design skills (procedures for changing a design, Claude Code skill format):
all, a selection, or none, into the user's Claude Code skills folder
(`--skills all|select|none` without the dialogue; `bin/kb-skills` later).
`python smoke.py` with the bundled interpreter reruns the release checks.

## Starting a project

`bin/new-project <directory>` (`bin\new-project.cmd` on Windows) creates an
arch2code project of the integrated design flow from `templates/project`:
Makefiles that build with the bundle's arch2code (or with `--submodule`, a
pinned cortex-a2c inside the project), the agent-rules appendix with the flow
routing and the knowledge-base rules, an empty `design/` for the flow's records
(intent, decomposition, decisions, IP bindings, gaps, hand-off), and
`.mcp.json.example` for the remaining servers. Then `bin/a2c-make agents-setup`
in the project and open it in Claude Code; the `design-from-intent` skill runs
the intake. `docs/integrated_flow_overview.pptx` in the repository presents
the flow.

## New in this release

- arch2code: the `design-from-intent` and `implement-from-handoff` skills of
  the integrated flow with the design record templates; the register-access
  test (`regAccess: true` on an APB master stub, `reg_access_plan` and
  `reg_access_test` tools) and the `evidence` and `unverified` register keys;
  server precedence in the generated AGENTS.md.
- cortex-kb: register knowledge from IP-XACT memory maps and C headers
  (`kb_get_registers`, each register cited to file and line); the pilot
  evaluation task and the integrated-flow scorer measures; corpus pull
  requests with derived-only changes merge automatically.

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
