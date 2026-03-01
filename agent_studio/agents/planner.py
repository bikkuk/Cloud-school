class PlannerAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def build_plan(self, model: str, brief: str, temperature: float, num_ctx: int, context_notes: str = "") -> str:
        prompt = (
            "You are PlannerAgent. Turn the brief into an actionable, ordered plan with clear steps. "
            "Keep scope tight, mention files to touch, and include quick validation steps."
            "\n\nTask Brief:\n"
            f"{brief}\n"
        )
        if context_notes.strip():
            prompt += "\nProject memory/context from prior iterations:\n" + context_notes + "\n"
        return self.llm.generate(model=model, prompt=prompt, temperature=temperature, num_ctx=num_ctx)
