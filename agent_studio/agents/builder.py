import json
from pathlib import Path


class BuilderAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def propose_product_files(
        self,
        model: str,
        brief: str,
        plan: str,
        temperature: float,
        num_ctx: int,
        context_notes: str = "",
    ) -> dict:
        prompt = (
            "You are BuilderAgent. Generate a WORKING local product from the user's brief and plan. "
            "Return STRICT JSON only (no markdown) in this schema: "
            '{"summary":"...","files":[{"path":"index.html","content":"..."}]}. '
            "Rules: paths must be relative and represent a runnable artifact (website/app/scripts). "
            "Prefer complete files over stubs."
            "\n\nPlan:\n"
            f"{plan}\n\nBrief:\n{brief}\n"
        )
        if context_notes.strip():
            prompt += "\nProject memory/context from prior iterations:\n" + context_notes + "\n"

        raw = self.llm.generate(model=model, prompt=prompt, temperature=temperature, num_ctx=num_ctx)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and isinstance(parsed.get("files", []), list):
                return parsed
        except json.JSONDecodeError:
            pass
        return {
            "summary": "Builder returned non-JSON content. Saved as fallback markdown output.",
            "files": [{"path": "generated_output.md", "content": raw}],
        }

    def _safe_relative_path(self, rel_path: str) -> str:
        cleaned = rel_path.replace("\\", "/").strip().lstrip("/")
        if not cleaned or cleaned.startswith("../") or "/../" in cleaned:
            raise ValueError(f"Unsafe output path rejected: {rel_path}")
        return cleaned

    def _strip_code_fences(self, content: str) -> str:
        text = content.strip()
        lines = text.splitlines()
        if not lines:
            return text

        first = lines[0].strip().lower()
        last = lines[-1].strip().lower()

        # Markdown fences like ```python ... ``` or ~~~js ... ~~~
        if first.startswith("```") or first.startswith("~~~"):
            lines = lines[1:]
            if lines:
                tail = lines[-1].strip().lower()
                if tail in {"```", "~~~"}:
                    lines = lines[:-1]

        # Some local models return wrappers like "python,,," ... ",,,"
        if lines and lines[0].strip().lower().endswith(",,,"):
            lines = lines[1:]
        if lines and lines[-1].strip() == ",,,":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()
        return cleaned if cleaned else text

    def write_files_with_preview(self, outputs_dir: Path, files: list[dict], confirm_overwrite) -> tuple[list[dict], list[str]]:
        writes = []
        messages = []

        for item in files:
            rel = self._safe_relative_path(str(item.get("path", "")))
            raw_content = str(item.get("content", ""))
            content = self._strip_code_fences(raw_content)
            target = outputs_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)

            if target.exists():
                old = target.read_text(encoding="utf-8")
                preview = (
                    "--- Existing (first 300 chars) ---\n"
                    f"{old[:300]}\n\n"
                    "--- New (first 300 chars) ---\n"
                    f"{content[:300]}"
                )
                if not confirm_overwrite(target.as_posix(), preview):
                    messages.append(f"Overwrite cancelled for {rel}.")
                    continue
            else:
                old = ""

            target.write_text(content, encoding="utf-8")
            writes.append({"path": rel, "old": old, "new": content})
            messages.append(f"Wrote {rel}.")

        return writes, messages
