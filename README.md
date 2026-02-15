# AI for Seniors (Offline + Local + USB Ready)

This project now runs as a **desktop GUI wrapper** on Windows (no browser required).

## Features
- Native desktop interface (Tkinter) with large text + high contrast
- 8 lessons in `/lessons`
- Local Ollama integration (`http://127.0.0.1:11434`, model `qwen2.5:7b`)
- Two local LLM modes:
  - **Teacher mode** (Q&A)
  - **AI Video Anchor mode** (anchor-style script + local voice playback)
- Strict safety scope:
  - Only AI basics, AI safety, privacy, scams, misinformation, and risks
  - Refuses medical/legal/financial advice
  - Refuses harmful/illegal instructions
  - Redirects out-of-scope questions to lessons
  - Never asks learners to go online

## Windows requirements
1. Python 3.10+ (with Tkinter included)
2. Ollama installed
3. Local model downloaded once: `qwen2.5:7b`

## One-time install
1. Open Command Prompt in this project folder.
2. Run:
   ```bat
   install.bat
   ```
3. If prompted, run once (internet only for this first model download):
   ```bat
   ollama pull qwen2.5:7b
   ```

After model download, day-to-day use is fully offline.

## Start the app (desktop GUI)
1. Run:
   ```bat
   start.bat
   ```
2. The desktop GUI opens directly (no browser tab).

## How seniors use it
- Left: choose lessons
- Center: read lesson content and print it
- Right: ask questions and use helper buttons
- AI Video Anchor: generate presenter script and play local voice

## Project structure
- `/lessons` - lesson markdown files
- `/server/core.py` - shared guardrails + Ollama logic
- `/server/desktop_app.py` - desktop GUI wrapper
- `/server/app.py` - optional local web API/UI compatibility
- `/web` - optional browser UI (not required for normal desktop use)
- `install.bat` - setup checks + `.venv` + dependency install
- `start.bat` - launches desktop GUI and ensures Ollama service
