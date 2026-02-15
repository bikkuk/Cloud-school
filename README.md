# AI for Seniors (Offline + Local)

This module runs fully offline after one-time setup.

## What it includes
- Local web app with large text and high contrast
- 8 beginner-friendly lessons in `/lessons`
- Local assistant restricted to:
  - AI basics
  - AI safety
  - privacy
  - scams
  - risks
- Safety guardrails that refuse:
  - medical advice
  - legal advice
  - financial advice
  - harmful or illegal instructions

## Requirements (Windows)
1. Python 3.10+
2. Ollama installed
3. Local model: `qwen2.5:7b`

## One-time install
1. Open Command Prompt in this project folder.
2. Run:
   ```bat
   install.bat
   ```
3. If prompted, run once:
   ```bat
   ollama pull qwen2.5:7b
   ```

After model download, normal use is fully offline.

## Start the app
1. Make sure Ollama is running.
2. Run:
   ```bat
   start.bat
   ```
3. Browser opens at `http://127.0.0.1:5000`.

## Project structure
- `/lessons` - 8 markdown lesson files
- `/server` - Flask backend and Ollama integration
- `/web` - local browser UI
- `install.bat` - setup checks and dependency install
- `start.bat` - launches local app

## Notes
- The assistant never asks the learner to go online.
- Out-of-scope questions are refused and redirected to lessons.

---

## AI Agent Studio (Desktop)

A new local-first desktop Studio is available under `agent_studio/`.

### Start Studio
```bat
start_studio.bat
```

### Studio highlights
- Tkinter desktop UI (no Electron, no cloud APIs)
- Exactly 4 internal agents: Planner, Reviewer, Builder, Runner
- Ollama local integration via `http://127.0.0.1:11434`
- Project-scoped artifacts stored under `studio_projects/<project>/`

For detailed setup and usage, see `README_STUDIO.md`.
