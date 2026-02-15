from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

import requests
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
LESSONS_DIR = BASE_DIR / "lessons"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

ALLOWED_TOPICS = {
    "ai", "artificial intelligence", "model", "prompt", "llm", "chatbot",
    "safety", "safe", "privacy", "private", "data", "scam", "fraud", "phishing",
    "deepfake", "risk", "risks", "misinformation", "security", "online fraud",
}

DISALLOWED_AREAS = {
    "medical", "doctor", "diagnosis", "treatment", "medicine",
    "legal", "lawyer", "lawsuit", "court", "contract",
    "financial", "investment", "stock", "crypto", "tax", "loan",
}

HARMFUL_KEYWORDS = {
    "hack", "bypass", "weapon", "bomb", "poison", "steal", "malware", "exploit",
}

LESSON_REDIRECT = "Please choose a lesson on the left to continue learning safely."

SYSTEM_PROMPT = """You are a local offline teaching assistant for seniors.
Rules you must always follow:
1) Only discuss AI basics, AI safety, privacy, scams, misinformation, and risks.
2) If user asks outside scope, politely refuse and direct them to lessons.
3) Refuse any medical, legal, or financial advice.
4) Refuse harmful, illegal, or unsafe instructions.
5) If the user request is unclear, ask exactly ONE clarifying question.
6) Use plain language, short sentences, and supportive tone for seniors.
7) Never tell the user to go online.
"""

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def is_unclear(text: str) -> bool:
    words = text.split()
    if len(words) < 4:
        return True
    vague = {"help", "explain", "tell me", "question", "what about"}
    return text in vague


def local_filter(user_input: str) -> Optional[str]:
    text = normalize_text(user_input)

    if contains_any(text, HARMFUL_KEYWORDS):
        return (
            "I can’t help with harmful or illegal instructions. "
            f"{LESSON_REDIRECT}"
        )

    if contains_any(text, DISALLOWED_AREAS):
        return (
            "I can’t provide medical, legal, or financial advice. "
            "I can explain AI safety topics instead. "
            f"{LESSON_REDIRECT}"
        )

    if not contains_any(text, ALLOWED_TOPICS):
        return (
            "I’m limited to AI basics, safety, privacy, scams, and risks. "
            f"{LESSON_REDIRECT}"
        )

    if is_unclear(text):
        return "Could you clarify what AI safety topic you want: basics, privacy, scams, or risks?"

    return None


def ask_ollama(user_input: str) -> str:
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{SYSTEM_PROMPT}\nUser question: {user_input}\nAssistant:",
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "I could not generate a response right now.").strip()


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/lessons")
def list_lessons():
    lessons = sorted(path.name for path in LESSONS_DIR.glob("*.md"))
    return jsonify({"lessons": lessons})


@app.get("/api/lessons/<path:lesson_name>")
def get_lesson(lesson_name: str):
    safe_name = Path(lesson_name).name
    return send_from_directory(LESSONS_DIR, safe_name)


@app.post("/api/ask")
def ask():
    payload = request.get_json(silent=True) or {}
    user_input = str(payload.get("question", "")).strip()

    if not user_input:
        return jsonify({"answer": "Please type a question about AI safety, privacy, scams, or risks."})

    blocked = local_filter(user_input)
    if blocked:
        return jsonify({"answer": blocked})

    try:
        answer = ask_ollama(user_input)
    except requests.RequestException:
        answer = (
            "The local AI model is unavailable. Please start Ollama and ensure model "
            f"'{MODEL_NAME}' is installed."
        )

    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
