from pathlib import Path


class BuilderAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def propose_changes(self, model: str, brief: str, plan: str, temperature: float, num_ctx: int) -> str:
        prompt = (
            "You are BuilderAgent. Produce a concise changes summary and draft output artifacts for the task."
            " Keep output deterministic and avoid unrelated edits."
            "\n\nPlan:\n"
            f"{plan}\n\nBrief:\n{brief}\n"
        )
        return self.llm.generate(model=model, prompt=prompt, temperature=temperature, num_ctx=num_ctx)

    def write_output_with_preview(self, output_file: Path, content: str, confirm_overwrite) -> tuple[bool, str]:
        if output_file.exists():
            old = output_file.read_text(encoding="utf-8")
            preview = (
                "--- Existing (first 300 chars) ---\n"
                f"{old[:300]}\n\n"
                "--- New (first 300 chars) ---\n"
                f"{content[:300]}"
            )
            if not confirm_overwrite(output_file.as_posix(), preview):
                return False, f"Overwrite cancelled for {output_file.name}."
        output_file.write_text(content, encoding="utf-8")
        return True, f"Wrote {output_file.name}."
