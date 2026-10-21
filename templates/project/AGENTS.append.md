## @PROJECT@: the integrated flow

This project follows the integrated FPGA design flow (the "Agentic FPGA System Design Architecture" document, version 1.2): arch2code is the single source of truth, the knowledge base (cortex-kb) and lattice-cortex supply the evidence and the Propel and firmware runners, and Radiant is reached only through the bundle's tools. The flow, its thirteen stages, its three gates and the server precedence are in arch2code's `plans/integrated-flow.md`; the skills are `design-from-intent` (phases A and B) and `implement-from-handoff` (phases C to E). The records under `design/` are the single source of truth together with the project YAML; every session starts from them, never from memory.

| User intent | Skill |
| :--- | :--- |
| Start a design from an intent, or enter an existing design (extend an arch2code project, vary a captured design, extend a Propel SoC, debug) | `design-from-intent.md` |
| Realise the SoC, implement RTL, write constraints, pass Gate 3, build with Radiant, build firmware, bring up the board, capture | `implement-from-handoff.md` from `design/handoff.md` |
| Tandem verification of a hand-written leaf block | `run-tandem.md` (Pro) |
| Radiant automation, timing closure, Reveal | the bundle's `lattice-radiant-automation`, `lattice-radiant-webdocs`, `reveal-debug` skills |
| Propel SoC session, firmware | the `lattice-cortex` skill (cortex-mcp) |

## Cortex KB usage rules

Standing instructions for the `cortex-kb` MCP server, copied from that repository's `CLAUDE.md`. Lint and the model simulation run through the arch2code MCP first; the Radiant steps are stages 9 to 12 of `implement-from-handoff`.

- Call `kb_status` first. If the KB is degraded, stop and report the error.
- Before proposing architecture or writing RTL, call `kb_find_designs`, `kb_find_modules`, and `kb_find_patterns` with the requirement. Use `min_maturity=reviewed` unless told otherwise.
- Prefer reusing a whole design entry when it fits. Reuse an individual module only when it is marked reusable; call `kb_get_module` and read its file and line range before adapting it. Keep the parent design's attribution, including upstream repository or origin, pinned commit or tree hash, and version, in the generated code header.
- If a result says `source_available` is false, obtain the sources from the recorded origin location before adapting anything; never reconstruct a module from its port list alone.
- Call `kb_get_flow` and `kb_get_constraints` before reusing a design on a new device or at a new clock frequency; state the tool version it was verified with. Use `kb_get_versions` when a design's history matters and `kb_find_ips` to check IP Catalog core versions.
- Use `kb_get_hierarchy` to understand a design's structure before modifying or extending it; `kb_get_registers` for the register maps it declares.
- For every reused entry: call `kb_get_entry`, then `kb_read_file` on its README and top-level RTL. Do not reuse an entry from its summary alone.
- State which entries were selected, which were rejected, and why.
- Call `kb_check_antipatterns` for any CDC, reset, FIFO, or handshake logic.
- Consult `kb_device_notes` before using any vendor primitive or attribute. Never invent primitives.
- Generate new modules from `kb_get_template` scaffolds and follow the style guide resource (`kb://style_guide`).
- Every new module requires a self-checking testbench.
- Run lint, simulation, and synthesis through the tools before reporting completion; include resource and timing results.
- If no suitable entry exists, say so explicitly rather than forcing a fit.
- For any function a Lattice IP core provides (Ethernet, MIPI, memory controllers, bus bridges, PLL, FIFO, DSP), call `kb_find_ips` before writing RTL; prefer a catalog core over new logic. Call `kb_get_ip` for the chosen version with the target device and parameters, keep the returned parameter set and constraint template, and generate the instance with the returned `ipgen` command through the Radiant tooling. Never reconstruct, adapt, or paraphrase an IP core from its port list; the core is instantiate-only.
- State the IP version and the minimum Radiant version in the design header, and cite the user-guide locator the catalog returns.
- Before writing pin constraints for an evaluation board, call `kb_find_boards` and `kb_get_board`; take sites, I/O types, reference clocks and bank voltages from the board entry and cite the source file of every pin you use. A site the board entry does not list, or a polarity or pull setting it does not state, is a gap to record, not a guess to silently make.
- Before changing an existing design, call `kb_find_skills(design=<name>)`; when a skill matches, read it with `kb_get_skill`, follow its steps, run its checks and say which skill was used.

## Execution rules of the flow

- Never run `arch2code.py` directly after project creation; use the arch2code MCP tools or the make targets.
- Never run `propelbldc`, `propelbldmainc` or the RISC-V toolchain directly; use the lattice-cortex runners.
- Never run `radiantc`, `pnmainc`, Questa, backanno or the programmer directly; use the bundle's tools.
- Never hand-edit a Propel- or Radiant-generated file, and never edit between generated-code markers.
- Never reconstruct an IP core or a module from its port list.
- Never set maturity, licence, provenance, export control, classification or owner team; ask the engineer.
- Cap self-diagnosis of a failing tool at three attempts or ten minutes, then report with the error, the backend and a recommendation.
- Record every external fact in `design/gaps.yaml` with its source and locator; record every tool call that produced a candidate, every gate, every validator and equivalence result in `design/decisions.md`.
- Three gates: intent (Gate 1), decomposition (Gate 2), implementation review before the Radiant build (Gate 3). After Gate 2 nothing stops for a question except Gate 3.
