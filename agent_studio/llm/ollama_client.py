import json
from urllib import error, request


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _post_json(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _get_json(self, path: str) -> dict:
        req = request.Request(f"{self.base_url}{path}", method="GET")
        with request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def list_models(self) -> list[str]:
        tags = self._get_json("/api/tags")
        models = [m.get("name", "").strip() for m in tags.get("models", [])]
        return sorted([m for m in models if m])

    def check_connection(self) -> tuple[bool, str]:
        try:
            self.list_models()
            return True, "Ollama is reachable."
        except Exception as exc:
            return False, f"Cannot reach Ollama at {self.base_url}: {exc}"

    def model_exists(self, model: str) -> tuple[bool, str]:
        try:
            names = set(self.list_models())
            if model in names:
                return True, f"Model '{model}' is installed."
            return False, f"Model '{model}' not found. Run: ollama pull {model}"
        except error.URLError as exc:
            return False, f"Ollama unavailable: {exc}"

    def generate(self, model: str, prompt: str, temperature: float = 0.2, num_ctx: int = 4096) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": num_ctx,
            },
        }
        result = self._post_json("/api/generate", payload)
        return result.get("response", "").strip()
