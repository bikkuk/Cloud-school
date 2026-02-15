from flask import Flask, jsonify, request, send_from_directory
from pathlib import Path

from core import (
    BASE_DIR,
    MODEL_NAME,
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
    return jsonify({"answer": answer_question(user_input)})


@app.post("/api/anchor")
def anchor():
    payload = request.get_json(silent=True) or {}
    topic = str(payload.get("topic", "")).strip()
    return jsonify({"script": make_anchor_script(topic)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
