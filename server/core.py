from __future__ import annotations

from pathlib import Path
import re
from typing import Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
LESSONS_DIR = BASE_DIR / "lessons"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = "qwen2.5:7b"

SUPPORTED_LANGUAGES = {
    "English": "English",
    "Español": "Spanish",
    "Français": "French",
    "Deutsch": "German",
    "Português": "Portuguese",
    "العربية": "Arabic",
    "हिन्दी": "Hindi",
    "中文": "Chinese",
}

ALLOWED_TOPICS = {
    "ai", "artificial", "intelligence", "model", "llm", "chatbot", "prompt",
    "safety", "safe", "privacy", "private", "data", "scam", "fraud", "phishing",
    "deepfake", "risk", "risks", "misinformation", "security", "identity", "fake",
    "senior", "elder", "message", "call", "voice", "video",
    "seguridad", "privacidad", "estafa", "fraude", "riesgo", "ancianos",
    "sécurité", "confidentialité", "arnaque", "risque", "personnes", "âgées",
    "sicherheit", "datenschutz", "betrug", "risiko", "senioren",
    "segurança", "golpe", "idosos", "risco", "privacidade",
    "سلامة", "خصوصية", "احتيال", "مخاطر",
    "सुरक्षा", "गोपनीयता", "धोखा", "जोखिम",
    "安全", "隐私", "诈骗", "风险",
}

DISALLOWED_AREAS = {
    "medical", "doctor", "diagnosis", "treatment", "medicine", "prescription",
    "legal", "lawyer", "lawsuit", "court", "contract", "attorney",
    "financial", "investment", "stock", "crypto", "tax", "loan", "trading",
    "médico", "médica", "legal", "financiero", "financiera",
    "médical", "juridique", "financier", "financière",
    "medizin", "rechtlich", "finanziell",
    "طبي", "قانوني", "مالي",
    "चिकित्सा", "कानूनी", "वित्तीय",
    "医疗", "法律", "金融",
}

HARMFUL_KEYWORDS = {
    "hack", "bypass", "weapon", "bomb", "poison", "steal", "malware", "exploit",
    "phish", "ransomware", "counterfeit", "arma", "bomba", "veneno", "pirater",
    "waffe", "bombe", "gift", "سلاح", "قنبلة", "سم", "हथियार", "बम", "जहर",
    "武器", "炸弹", "毒",
}

LESSON_REDIRECT = "Please choose a lesson from the left panel so we can stay on safe AI learning topics."

BASE_SYSTEM_PROMPT = """You are an offline AI teacher for seniors.
Follow these rules every time:
- Scope: only AI basics, AI safety, privacy, scams, misinformation, and AI risks.
- Refuse anything outside scope and redirect to lessons.
- Refuse medical, legal, or financial advice.
- Refuse harmful, illegal, deceptive, or exploitative instructions.
- If the user is unclear, ask exactly ONE clarifying question.
- Use clear, calm language, short paragraphs, and practical examples.
- Never ask the learner to go online.
"""

BASE_ANCHOR_PROMPT = """You are an AI video anchor for seniors, running fully local.
Create a short presenter's script in plain language.
Rules:
- Only cover AI basics, safety, privacy, scams, misinformation, and risks.
- Refuse medical/legal/financial advice and harmful instructions.
- If unclear, ask one clarifying question.
- Never tell the user to go online.
- Keep it friendly and confident, like a TV explainer.
Format:
1) Headline (1 line)
2) Script (5-8 short lines)
3) Safety takeaway (1 line)
"""


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower(), flags=re.UNICODE))


def contains_phrase(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def topic_score(text: str) -> int:
    words = tokens(text)
    return sum(1 for term in ALLOWED_TOPICS if term in words or term in text)


def is_unclear(text: str) -> bool:
    plain = normalize_text(text)
    if len(plain.split()) < 4:
        return True
    return plain in {"help", "explain", "question", "what about", "tell me", "ayuda", "aide"}


def normalize_language(language: str) -> str:
    language = (language or "").strip()
    return language if language in SUPPORTED_LANGUAGES else "English"


def language_instruction(language: str) -> str:
    normalized = normalize_language(language)
    return f"Respond in {SUPPORTED_LANGUAGES[normalized]} language unless the user explicitly requests another language."


def local_filter(user_input: str) -> Optional[str]:
    text = normalize_text(user_input)

    if contains_phrase(text, HARMFUL_KEYWORDS):
        return f"I can’t help with harmful or illegal instructions. {LESSON_REDIRECT}"

    if contains_phrase(text, DISALLOWED_AREAS):
        return (
            "I can’t provide medical, legal, or financial advice. "
            f"I can help with AI safety learning instead. {LESSON_REDIRECT}"
        )

    if topic_score(text) == 0:
        return f"I’m limited to AI basics, safety, privacy, scams, and risks. {LESSON_REDIRECT}"

    if is_unclear(text):
        return "Could you clarify your topic: AI basics, privacy, scams, or risks?"

    return None


def blocked_or_none(user_input: str) -> Optional[str]:
    if not user_input.strip():
        return "Please type a question about AI safety, privacy, scams, or risks."
    return local_filter(user_input)


def call_ollama(user_prompt: str, system_prompt: str, language: str = "English") -> str:
    prompt = f"{system_prompt}\n- {language_instruction(language)}"
    payload = {
        "model": MODEL_NAME,
        "prompt": f"{prompt}\n\nUser: {user_prompt}\nAssistant:",
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "I could not generate a response right now.").strip()


def ollama_health() -> dict:
    try:
        response = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        response.raise_for_status()
        tags = response.json().get("models", [])
        has_model = any(model.get("name", "").startswith(MODEL_NAME) for model in tags)
        return {"ollama": "ok", "model_ready": has_model, "model": MODEL_NAME}
    except requests.RequestException:
        return {"ollama": "down", "model_ready": False, "model": MODEL_NAME}


def list_lessons() -> list[str]:
    return sorted(path.name for path in LESSONS_DIR.glob("*.md"))


def read_lesson(name: str) -> str:
    return (LESSONS_DIR / Path(name).name).read_text(encoding="utf-8")


def answer_question(user_input: str, language: str = "English") -> str:
    blocked = blocked_or_none(user_input)
    if blocked:
        return blocked
    try:
        return call_ollama(user_input, BASE_SYSTEM_PROMPT, language)
    except requests.RequestException:
        return "Local model unavailable. Please start Ollama and confirm qwen2.5:7b is installed."


def make_anchor_script(topic: str, language: str = "English") -> str:
    blocked = blocked_or_none(topic)
    if blocked:
        return blocked
    try:
        return call_ollama(topic, BASE_ANCHOR_PROMPT, language)
    except requests.RequestException:
        return "Anchor mode is unavailable because Ollama is not reachable. Start Ollama and try again."
