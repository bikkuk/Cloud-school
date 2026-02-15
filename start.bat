@echo off
setlocal

echo Starting AI for Seniors local server...
start "" http://127.0.0.1:5000
python server\app.py

endlocal
