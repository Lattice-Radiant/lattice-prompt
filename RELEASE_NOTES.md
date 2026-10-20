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
runtime and tool versions that were bundled.

## Install

Windows: unzip anywhere, run `install.cmd`. Linux: `tar xzf` anywhere, run
`./install.sh`. Either registers the `arch2code` and `cortex-kb` MCP servers
with Claude Code (`~/.claude.json`) and Claude Desktop, backing the files up;
`--uninstall` removes the entries. `python smoke.py` with the bundled
interpreter reruns the release checks.

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
