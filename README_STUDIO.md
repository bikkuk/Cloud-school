# AI Agent Studio (Local-First, Windows + Python)

AI Agent Studio is a desktop Tkinter app for running multiple local agents with Ollama.
No cloud APIs, no telemetry, and no internet needed after one-time setup.

## Features (MVP)
- Tkinter desktop UI with:
  - Left: project + agent list
  - Center: brief editor, plan generation, run/stop, lock switches
  - Right: logs + files generated
  - Top: model, temperature, context preset, Ollama check
  - Bottom: status bar
- Project folders under `studio_projects/<project_name>/` (including top-level `project_brief.md`, `plan.md`, `run_log.txt`, `changes.patch`, and `outputs/`)
- Built-in agents: Planner, Builder, Reviewer, Runner
- Reproducible run artifacts in `agent_runs/<timestamp>/`:
  - `plan.md`
  - `changes_summary.md`
  - `run_log.txt`
  - `changes.patch` (when output changed)
- Attachment copying into each project's `attachments/`
- Lock enforcement:
  - UX lock
  - Function lock
  - Page lock
- Safe command execution with allowlist in `agent_studio/config/allowed_commands.json`

## One-time setup (Windows)
1. Install Python 3.10+.
2. Install Ollama and start it.
3. Run:
   ```bat
   install.bat
   ```

## Start
Double-click:
```bat
start_studio.bat
```

## Existing AI for Seniors module
This repo keeps the original web module intact.
To run it directly:
```bat
start.bat
```

## Notes / limitations
- Runner defaults to `python -m pytest` and logs output (or missing tests errors).
- Lock checks are keyword-based in MVP (clear explanation is written if blocked).
- Builder writes project output files only; it does not edit arbitrary repository files.
- Ollama must be reachable at `http://127.0.0.1:11434`.
