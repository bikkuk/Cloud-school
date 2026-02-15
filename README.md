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
