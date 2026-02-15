from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path

from core import (
    BASE_DIR,
    SUPPORTED_LANGUAGES,
    answer_question,
    list_lessons,
    make_anchor_script,
    ollama_health,
)

WEB_DIR = BASE_DIR / "web"
LESSONS_DIR = BASE_DIR / "lessons"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/health")
def health():
    return jsonify(ollama_health())


@app.get("/api/languages")
def languages_api():
    return jsonify({"languages": list(SUPPORTED_LANGUAGES.keys())})


@app.get("/api/lessons")
def lessons_api():
    return jsonify({"lessons": list_lessons()})


@app.get("/api/lessons/<path:lesson_name>")
def lesson_file(lesson_name: str):
    return send_from_directory(LESSONS_DIR, Path(lesson_name).name)


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    user_input = str(payload.get("question", "")).strip()
    language = str(payload.get("language", "English")).strip()
    return jsonify({"answer": answer_question(user_input, language)})


@app.post("/api/anchor")
def anchor():
    payload = request.get_json(silent=True) or {}
    topic = str(payload.get("topic", "")).strip()
    language = str(payload.get("language", "English")).strip()
    return jsonify({"script": make_anchor_script(topic, language)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
