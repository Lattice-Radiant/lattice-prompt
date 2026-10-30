# @PROJECT@

An arch2code project of the integrated FPGA design flow, created from the lattice-prompt bundle's
project template.

## Layout

```
include/make/shared.mk  where arch2code is (A2C_ROOT from the bundle launchers, or a submodule at arch2code/) and the kb-skills launcher
.kb/                    knowledge-base skills exported for agents-setup (generated, ignored)
Makefile                agents-setup, preflight, and the arch2code targets once the YAML exists
rundir/Makefile         model build and run
AGENTS.append.md        appended to AGENTS.md by `make agents-setup`: flow routing, knowledge-base rules, execution rules
rules/                  project-local skills (optional)
design/                 the design records written by the flow (see design/README.md)
.mcp.json.example       template of the workstation-specific server registration
```

## Starting a session

1. `bin/a2c-make agents-setup` (from the bundle; `make agents-setup` with a development checkout, `A2C_ROOT` and `KB_SKILLS` set): exports the knowledge base's reviewed skills for the designs `design/intent.yaml` names into `.kb/rules`, then writes `AGENTS.md` and `CLAUDE.md` and deploys the arch2code and knowledge-base skills under `.claude/skills/`, `.cursor/`, `.gemini/`, `.opencode/` and `.agents/`. Rerun after a bundle or knowledge-base update. The same skills are MCP prompts of the lattice-knowledge-db server (`/mcp__lattice-knowledge-db__<design>-<skill>` in Claude Code).
2. The bundle installer has registered the four servers (`lattice-arch2code-mcp`, `lattice-knowledge-db`, `lattice-propel-mcp`, `lattice-radiant-mcp`) for Claude Code. Copy `.mcp.json.example` to `.mcp.json` only to pin another bundle for this project.
3. Open the directory in Claude Code and say what the design must do; the `design-from-intent` skill asks the intake questions and writes `design/intent.yaml` for Gate 1.
