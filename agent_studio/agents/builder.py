import json
from pathlib import Path


class BuilderAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def propose_patch(
        self,
        model: str,
        brief: str,
        plan: str,
        editable_paths: list[str],
        temperature: float,
        num_ctx: int,
    ) -> dict:
        prompt = (
            "You are BuilderAgent. Return JSON only. Produce a minimal scoped patch plan.\n"
            "Rules:\n"
            "- Output JSON object with keys: summary, files.\n"
            "- files must be an array of objects: {path, content}.\n"
            "- Only use file paths under these allowed roots: "
            f"{', '.join(editable_paths)}\n"
            "- Keep files count <= 3.\n"
            "- Do not include markdown fences.\n\n"
            f"Plan:\n{plan}\n\n"
            f"Brief:\n{brief}\n"
        )
        raw = self.llm.generate(model=model, prompt=prompt, temperature=temperature, num_ctx=num_ctx)
        parsed = self._extract_json(raw)
        if not isinstance(parsed, dict) or "files" not in parsed:
            return self._fallback_patch(brief)
        files = parsed.get("files")
        if not isinstance(files, list):
            return self._fallback_patch(brief)
        return parsed

    def _extract_json(self, raw: str):
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json\n", "", 1)
        try:
            return json.loads(cleaned)
        except Exception:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(cleaned[start : end + 1])
                except Exception:
                    return None
            return None

    def _fallback_patch(self, brief: str) -> dict:
        return {
            "summary": "Fallback patch generated locally.",
            "files": [
                {
                    "path": "docs/generated_spec.md",
                    "content": f"# Generated Spec\\n\\n{brief}\\n",
                }
            ],
        }

    def apply_patch_plan(
        self,
        project_root: Path,
        patch_plan: dict,
        editable_roots: list[str],
        max_files: int,
    ) -> dict:
        files = patch_plan.get("files", [])
        if len(files) > max_files:
            return {"ok": False, "reason": f"File cap exceeded ({len(files)}>{max_files}).", "changes": []}

        changes = []
        for entry in files:
            rel = str(entry.get("path", "")).replace("\\", "/").strip("/")
            content = entry.get("content", "")
            if not rel:
                return {"ok": False, "reason": "Empty path in patch plan.", "changes": changes}
            if not any(rel == root or rel.startswith(root + "/") for root in editable_roots):
                return {"ok": False, "reason": f"Out-of-scope path: {rel}", "changes": changes}

            target = project_root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            old = target.read_text(encoding="utf-8") if target.exists() else ""
            target.write_text(content, encoding="utf-8")
            changes.append({"path": rel, "old": old, "new": content})

        return {"ok": True, "reason": "Patch applied", "changes": changes}
