# Decisions: cortex-pilot

Append-only log of the integrated flow. One entry per tool call that produced a candidate, per gate, per assumption made after Gate 2, per validator and equivalence result, per register-access result, and per open item for another maintainer. Written as the flow runs, never from memory afterwards.

Knowledge base commit: `8594fc2fc96dd0e1a4cf3d2a2c09ae9dd2505743` (served by the pilot workstation's checkout at preflight; `main` of cortex-kb is ahead of it, see the open items).

## Format

```
<YYYY-MM-DD> stage 0  readiness: cortex-kb <commit, healthy|degraded>; arch2code <make, compiler, SystemC, Questa|Verilator, Pro present|absent>; lattice-cortex <backend|not needed|unavailable>; lattice-radiant-mcp <Radiant version, licence|not detected>
```

```
<YYYY-MM-DD> stage <n>  <tool>(<arguments that matter>)
  selected  <entry or core> <version>   why: <matched interfaces, maturity, source availability, family>
  rejected  <entry or core>             why: <reason>
  candidate <entry> (draft)             why: <listed only, maturity below reviewed>
```

```
<YYYY-MM-DD> gate 1  approved by <team identifier>; open questions resolved: <list>
<YYYY-MM-DD> gate 2  approved by <team identifier>; edits: <list or none>; unverified registers: <accepted|sourced: list>
<YYYY-MM-DD> gate 3  approved by <team identifier>; device <string>; environment <backend>; lint_constraints <result>
<YYYY-MM-DD> stage <n>  assumption: <what was assumed and why no question was asked>
<YYYY-MM-DD> stage <n>  fix: <error> -> <change>
<YYYY-MM-DD> stage <n>  derived: <record or register> from <source class and pointer>; disagreement: <higher-ranked source wins: detail>
<YYYY-MM-DD> stage 4  validator: validate_topology|validate_merge|advise -> <result or findings>
<YYYY-MM-DD> stage 7  session preview: <queued Tcl, verbatim or path>
<YYYY-MM-DD> stage 7  equivalence: propel_check_session_against_real_sbx -> missing <list or none>, extra <list>; parse_sbx vs SoC table -> <match | differing rows>
<YYYY-MM-DD> stage 8  reg_access_test <block>: <register> <pass | mismatch observed <value> | not run: reason>
<YYYY-MM-DD> stage 10 lever: <name> check_plan <result> verify_non_regression <result>
<YYYY-MM-DD> stage <n>  refused: <tool> <error>; alternative: <what was done>; attempts <n>
<YYYY-MM-DD> open item for <cortex-mcp | lattice-radiant-mcp | cortex-kb | arch2code>: <what, with the design-document section>
```

## Entries

```
2026-10-21 stage 0  readiness (phase P0, pilot workstation, Windows 11):
  cortex-kb            kb_status: healthy, not degraded; served commit 8594fc2fc96d (local checkout, dirty: an untracked .mcp.json); schema 0004 at that commit. cortex-kb main is at beaf5b5f (skills, classification, distribution filter merged after this checkout); the checkout is pulled before stage 3.
  arch2code            submodule a7a1ba1b (cortex-a2c main); toolchain_detect: ready (GNU make ezwinports 4.4.1, MSYS2 clang64 at C:/msys64/clang64, clang, Verilator 5.050, SystemC static, Boost); questa_detect: 2 installations, selected Questa 2025.2 under C:/lscc/propel/2026.1/questasim (C:/lscc/radiant/2025.2.1/questasim also present); list_projects on the pilot: no project of its own yet, 139 example and fixture projects under the submodule. Arch2Code Pro present (pro/ in the checkout; run-tandem deployed).
  lattice-cortex       reachable over stdio from the pilot workstation (python -m lattice_cortex.server in the cortex-mcp checkout's venv): 127 tools, local backend, Propel base C:/lscc/propel; lattice://health not served to this session (the server is registered at user scope for the cortex-mcp checkout), so stage 3 onwards uses the pilot's .mcp.json entry.
  lattice-radiant-mcp  detect_radiant_installations: Radiant 2025.2.1 at C:/lscc/radiant/2025.2.1 (radiantc at bin/nt64); check_environment: ready (Radiant path resolved, remote-execution checks passed); bundle 1.1.0, timing-closure tools enabled as registered. Propel 2026.1 present at C:/lscc/propel/2026.1 (the design document's donor was captured with Propel 2025.1 IP versions: resolve_ip_version at stage 3 decides).
2026-10-21 stage 0  trivial project: the helloWorld example copied in as the phase P0 project (PROJECTNAME helloWorld; setup-project replaces it at stage 5); make db, make gen, the model build and the run pass ("No error" at the testbench's end of test); agents-setup deployed 30 skills to .claude/skills (CLAUDE.md -> AGENTS.md with the pilot routing appended). Phase P0 readiness complete. cortex-a2c PR #13 merged (24646386): the submodule pin moved there and agents-setup redeployed 31 skills (design-from-intent, implement-from-handoff among them) with the "Server precedence" section in AGENTS.md.
2026-10-21 stage 0  ip_check_compatibility(family LFCPNX, device LFCPNX-100-9LFG672I) over lattice-cortex (ip_search scope local, Propel 2026.1 library; OI-8): compatible, toolchain 2026.1 compatible: apb_interconnect 1.5.0, axi2apb_bridge 1.5.1, axi_interconnect 2.3.0, gpio 1.8.1, i2c_controller 2.4.1, lscc_reset 1.1.0, pll 1.9.1, riscv_rtos 2.8.1, system_memory 2.6.0, uart 1.6.0 (the installed versions are newer than the donor's captured 2025.1 versions: resolve_ip_version at stage 3 decides per core; device_compatible is null for every core, the IP metadata lists families only). Not installed locally, the IP server was not consulted: axis_fifo, fpga_config, memory_controller, octal_spi_controller, sgdma, tse_mac, gp_timer (gap: install from the IP server before stage 7; the pilot's custom block does not depend on gp_timer).
2026-10-21 stage 0  open item for the pilot environment: the five servers are registered on the Windows workstation only; the LSF gateway registration and the bundle's trivial Radiant build on LSF (P0 exit criterion) are not done from this session (no gateway access here); the Windows build stands in.
2026-10-21 stage 0  fix: make agents-setup failed on Windows ("flock: 9: Bad file descriptor": the recipe locked the repository directory) -> lock on .agents-setup.lock, continue without a lock when flock refuses (cortex-a2c PR #13); the deployment takes several minutes on Windows (one process per deployed file).
2026-10-21 stage 0  assumption: the pilot's custom-logic bus is APB through the bridge find_protocol_bridge names (no AHB-Lite interface in arch2code yet); the register-access test is a SystemC test under run_cosim; register evidence lives in the YAML keys evidence and unverified (plans/integrated-flow.md, section 5).
2026-10-21 stage 1  intake: design/intent.yaml drafted from decision D14 and the knowledge-base task var_gsrd_add_gpio_timer (entry mode propel_soc_extension, donor cpnx_gsrd, custom block userTimer, end point hardware); the four assumptions in the record are the Gate 1 questions. Gate 1 not yet approved: stages 4 onwards wait.
2026-10-21 stage 3  knowledge search (cortex-kb served from the registers-knowledge branch, commit abd31692, schema 0007, 179 entries, 24 read-only tools):
  kb_get_entry(cpnx_gsrd)        0.1.0, experimental, internal, top soc_primary_gsrd; RISC-V RX, AXI4 interconnect, LPDDR4, TSE MAC + SGDMA, octal SPI, APB fabric with UART, GPIO, I2C, boot memory; dual-boot config glue; thirteen-group asynchronous clock plan.
  kb_get_hierarchy(cpnx_gsrd, 2) axi4_to_apb_bridge_inst (the bridge the custom window hangs from), per-domain reset synchronizers, dual_boot_fpga_config_inst, eth_i2c_inst, eth_sgdma_inst, ...; ipgen leaf modules unresolved (encrypted cores).
  kb_get_constraints(cpnx_gsrd)  generated clocks axi_clk (PLL CLKOS2), cpu_clk (PLL CLKOP), lpddr4_eclk, lpddr4_sclk, ... from constraints/constraints.sdc; periods not captured (null): the APB clock value is read from the PLL configuration at stage 4 (gap).
  kb_get_flow(cpnx_gsrd)         Radiant 2025.1 resources LUT 35465, FF 26091, EBR 80, DSP 4; no timing results captured (gap: the baseline Fmax for resource_ratio and timing comparison is recorded by the engineer).
  kb_get_registers(cpnx_gsrd)    5 blocks, 190 registers from IP-XACT: eth_i2c, eth_sgdma, eth_tse_mac, system_gpio, system_uart; the system_gpio map is the evidence source for userTimer's GPIO registers (block filter "gpio" returned 0: the filter was exact; made a substring match, cortex-kb PR #10).
  kb_get_entry(certuspro_nx_evaluation_board)  board entry present (pin map, reference clocks, bank voltages, derived, completeness 65); no JTAG or programming facts (OI-13 stands).
  kb_find_ips(gpio)              selected gpio 1.8.1 (server, reviewed, APB + interrupt; 1.8.0 in the donor) as the register-layout reference; kb_find_ips(gp_timer) selected gp_timer 1.5.0 (reviewed, APB/AHB-Lite + interrupt; not installed locally) as the timer-layout reference. Neither core is instantiated: the custom block is arch2code RTL (intent assumption 1).
  kb_find_skills                 no recorded procedure for registers, APB, timers or GPIO (none captured yet).
  kb_device_notes(certuspro_nx)  style-guide sections only; no family notes.
2026-10-21 open item for cortex-mcp: refresh the README and the lattice-cortex skill to the registered domain specifications (OI-9, phase P0 action, design document 14.3).
2026-10-21 open item for cortex-mcp: cross-reference the construction workflow's top-level port export in the lattice-cortex skill (OI-3, 14.3).
2026-10-21 open item for cortex-mcp: mark the reveal domain deprecated in favour of the bundle's RevealAI; keep the io domain behind its feature flag (OI-11, 14.3).
2026-10-21 open item for cortex-mcp: phase P5 tools propel_replay_manifest, the parse_sbx-based table comparison, a manifest-aware validate_build_schema (OI-2, 14.3).
2026-10-21 open item for lattice-radiant-mcp: document the tool deferral between the bundle and the Cortex MCP in the installer (14.4).
2026-10-21 open item for cortex-kb: JTAG chain and cable parameters of the CertusPro-NX evaluation board (device name, IDCODE, cable type and port, with their source) for program_device (OI-13, phase P3); the engineer names the document.
2026-10-21 open item for cortex-kb: register knowledge (knowledge/registers.yaml, kb_get_registers) and the pilot evaluation task with the rubric additions (14.2; phases P1 and P4).
2026-10-21 open item for arch2code: phase P1 generator work (APB bus-master transactor stub, register evidence keys, reg_access_test); phase P5 manifest generator (14.1).
```
