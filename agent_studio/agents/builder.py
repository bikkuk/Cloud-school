import json
import re
from pathlib import Path, PureWindowsPath


class BuilderAgent:
    _WINDOWS_DRIVE_RE = re.compile(r"^[a-zA-Z]:")

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
        candidates = [raw.strip()]
        if "```" in raw:
            for block in raw.split("```"):
                piece = block.strip()
                if piece and (piece.startswith("{") or "{" in piece):
                    candidates.append(piece)

        for candidate in candidates:
            text = candidate
            if "{" in text and not text.strip().startswith("{"):
                text = text[text.find("{"):]
            if "}" in text and not text.strip().endswith("}"):
                text = text[: text.rfind("}") + 1]
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and isinstance(parsed.get("files", []), list):
                    return parsed
            except json.JSONDecodeError:
                continue
        return {
            "summary": "Builder returned non-JSON content. Saved as fallback markdown output.",
            "files": [{"path": "generated_output.md", "content": raw}],
        }

    def _safe_relative_path(self, rel_path: str) -> str:
        candidate = (rel_path or "").strip()
        if not candidate:
            raise ValueError("Unsafe output path rejected: empty path")

        # Windows absolute/UNC/rooted path patterns
        if candidate.startswith("\\\\") or candidate.startswith("//"):
            raise ValueError(f"Unsafe output path rejected: {rel_path}")
        if candidate.startswith("\\") or candidate.startswith("/"):
            raise ValueError(f"Unsafe output path rejected: {rel_path}")
        if self._WINDOWS_DRIVE_RE.match(candidate):
            raise ValueError(f"Unsafe output path rejected: {rel_path}")

        win_path = PureWindowsPath(candidate)
        if win_path.is_absolute() or win_path.anchor.startswith("\\"):
            raise ValueError(f"Unsafe output path rejected: {rel_path}")

        cleaned = candidate.replace("\\", "/")
        parts = [p for p in cleaned.split("/") if p not in {"", "."}]
        if any(part == ".." for part in parts):
            raise ValueError(f"Unsafe output path rejected: {rel_path}")

        safe = "/".join(parts)
        if not safe:
            raise ValueError(f"Unsafe output path rejected: {rel_path}")
        return safe

    def _strip_code_fences(self, content: str) -> str:
        text = content.strip()
        lines = text.splitlines()
        if not lines:
            return text

        first = lines[0].strip().lower()

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
        outputs_resolved = outputs_dir.resolve()

        for item in files:
            try:
                rel = self._safe_relative_path(str(item.get("path", "")))
            except ValueError as exc:
                messages.append(str(exc))
                continue

            raw_content = str(item.get("content", ""))
            content = self._strip_code_fences(raw_content)
            target = (outputs_dir / rel).resolve()

            try:
                target.relative_to(outputs_resolved)
            except ValueError:
                messages.append(f"Unsafe output path rejected: {rel}")
                continue

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
