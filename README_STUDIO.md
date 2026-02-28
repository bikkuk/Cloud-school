# AI Agent Studio Desktop (Local-First, Windows + Python)

AI Agent Studio is a **desktop Tkinter GUI** (no browser window required) for running a local multi-agent workflow with Ollama.
Core operation is local-only: Python + local files + local Ollama.

## What this version now provides
- Native desktop GUI (`python agent_studio/app.py`) with pipeline controls.
- Step-gated pipeline execution:
  - Plan → Patch → Build → Test → Review → Approve → Package
- Mandatory artifact writing to project-local `.agentstudio/` folders.
- Scoped patch application only to editable roots (`src/`, `tests/`, `docs/`).
- File-change cap per iteration (default `N=6`) to avoid destructive rewrites.
- Gate status panel in the GUI showing PASS/FAIL with reason per gate.

## Desktop UI layout
- **Left:** projects + agent list + file attachments
- **Center:** task brief, plan generation, run/stop, lock toggles, plan preview
- **Right:** logs, gate status, project files
- **Top:** model, temperature, context preset, Ollama connectivity check
- **Bottom:** status bar

## Required project template (auto-created)
Each project in `studio_projects/<name>/` includes:
- `src/`, `tests/`, `docs/`
- `.agentstudio/tasks`
- `.agentstudio/plans`
- `.agentstudio/locks`
- `.agentstudio/patches`
- `.agentstudio/reports`
- `.agentstudio/logs`
- `.agentstudio/decisions`
- `.agentstudio/releases`

## Artifacts generated per run
- `.agentstudio/tasks/task_card.json`
- `.agentstudio/plans/plan_v1.md` and `plan_v1.json`
- `.agentstudio/patches/iter_1_plan.json` and `iter_1.diff`
- `.agentstudio/reports/iter_1_patch_summary.json`
- `.agentstudio/reports/iter_1_build.json`
- `.agentstudio/reports/iter_1_test_results.json`
- `.agentstudio/reports/iter_1_review_code.json`
- `.agentstudio/reports/iter_1_review_security.json`
- `.agentstudio/reports/iter_1_review_ux.json`
- `.agentstudio/decisions/iter_1_approval.json`
- `.agentstudio/releases/release_001/manifest.json`

## Lock controls in GUI
- **UX lock:** blocks UI/style-targeting change intents.
- **Function lock:** blocks API/signature/breaking-behavior intents.
- **Page lock:** blocks page/web file edits.

## Safety behavior
- Uses patch-plan application, not random full-project rewrites.
- Rejects out-of-scope file paths.
- Stores unified diffs for rollback/audit.
- Runs build/test checks and records logs.

## Setup (Windows)
1. Install Python 3.10+.
2. Install and start Ollama.
3. Run:
   ```bat
   install.bat
   ```

## Start the desktop app (no browser)
Double-click:
```bat
start.bat
```
(or `start_studio.bat`)

