# design/

The records of the integrated flow live here, written by the skills as the flow runs:
`intent.yaml` (stage 2, frozen at Gate 1), `decomposition.md` (stage 4, frozen at Gate 2),
`decisions.md` (append-only, every stage), `ip-bindings.yaml`, `gaps.yaml`, `handoff.md` (stage 13).
The templates are arch2code's `templates/design/`; the design-from-intent skill copies them on its
first run. A new session starts from these files, never from memory.
