import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from agent_studio.llm.ollama_client import OllamaClient
from agent_studio.orchestrator import StudioOrchestrator
from agent_studio.storage.project_store import ProjectStore


class AgentStudioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Agent Studio")
        self.geometry("1300x780")
        self.minsize(1100, 680)

        self.config_data = json.loads(Path("agent_studio/config/studio_config.json").read_text(encoding="utf-8"))
        self.store = ProjectStore("studio_projects")
        self.llm = OllamaClient(self.config_data.get("ollama_url", "http://127.0.0.1:11434"))
        self.orchestrator = StudioOrchestrator(self.llm, self.store, "agent_studio/config/allowed_commands.json")

        self.current_project = tk.StringVar(value="_demo")
        self.status_var = tk.StringVar(value="Idle")
        self.model_var = tk.StringVar(value=self.config_data.get("default_model", "qwen2.5:7b"))
        self.temp_var = tk.DoubleVar(value=0.2)
        preset = next(iter(self.config_data.get("context_presets", {"Medium (4K)": 4096})))
        self.ctx_label_var = tk.StringVar(value=preset)

        self.ux_lock = tk.BooleanVar(value=False)
        self.function_lock = tk.BooleanVar(value=False)
        self.page_lock = tk.BooleanVar(value=False)

        self._build_layout()
        self._refresh_projects()
        self._load_project_brief()
        self._refresh_project_files()

    def _build_layout(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Model:").pack(side="left")
        ttk.Combobox(top, textvariable=self.model_var, values=self.config_data.get("models", []), width=22).pack(side="left", padx=6)
        ttk.Button(top, text="Check Ollama", command=self.check_ollama).pack(side="left", padx=6)
        ttk.Label(top, text="Temperature:").pack(side="left", padx=(18, 0))
        ttk.Scale(top, from_=0.0, to=1.0, variable=self.temp_var, orient="horizontal", length=140).pack(side="left", padx=6)
        ttk.Label(top, text="Context:").pack(side="left", padx=(18, 0))
        ttk.Combobox(top, textvariable=self.ctx_label_var, values=list(self.config_data.get("context_presets", {}).keys()), width=14).pack(side="left", padx=6)

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=3)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(0, weight=1)

        left = ttk.LabelFrame(body, text="Projects + Agents", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Button(left, text="New Project", command=self.create_project).pack(fill="x")
        self.project_list = tk.Listbox(left, height=10)
        self.project_list.pack(fill="both", expand=True, pady=6)
        self.project_list.bind("<<ListboxSelect>>", self.select_project)
        ttk.Label(left, text="Agents").pack(anchor="w", pady=(8, 2))
        self.agent_list = tk.Listbox(left, height=6)
        for agent in ["PlannerAgent", "BuilderAgent", "ReviewerAgent", "RunnerAgent"]:
            self.agent_list.insert("end", agent)
        self.agent_list.pack(fill="x")
        ttk.Button(left, text="Attach File", command=self.attach_file).pack(fill="x", pady=(10, 0))

        center = ttk.LabelFrame(body, text="Task Brief", padding=8)
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        self.brief_text = tk.Text(center, wrap="word", height=13)
        self.brief_text.pack(fill="both", expand=True)
        controls = ttk.Frame(center)
        controls.pack(fill="x", pady=8)
        ttk.Button(controls, text="Generate Plan", command=self.generate_plan).pack(side="left")
        ttk.Button(controls, text="Run", command=self.run_pipeline).pack(side="left", padx=6)
        ttk.Button(controls, text="Stop", command=self.stop_run).pack(side="left")

        lock_bar = ttk.Frame(center)
        lock_bar.pack(fill="x", pady=(2, 4))
        ttk.Checkbutton(lock_bar, text="UX lock", variable=self.ux_lock).pack(side="left")
        ttk.Checkbutton(lock_bar, text="Function lock", variable=self.function_lock).pack(side="left", padx=8)
        ttk.Checkbutton(lock_bar, text="Page lock", variable=self.page_lock).pack(side="left")

        ttk.Label(center, text="Plan Preview").pack(anchor="w")
        self.plan_text = tk.Text(center, wrap="word", height=10)
        self.plan_text.pack(fill="both", expand=True)

        right = ttk.LabelFrame(body, text="Logs / Outputs / Files", padding=8)
        right.grid(row=0, column=2, sticky="nsew")
        ttk.Label(right, text="Logs").pack(anchor="w")
        self.log_text = tk.Text(right, wrap="word", height=14)
        self.log_text.pack(fill="both", expand=True)
        ttk.Label(right, text="Project Files").pack(anchor="w", pady=(8, 2))
        self.files_list = tk.Listbox(right, height=10)
        self.files_list.pack(fill="both", expand=True)

        bottom = ttk.Frame(self, padding=8)
        bottom.pack(fill="x")
        ttk.Label(bottom, textvariable=self.status_var).pack(side="left")

    def _ctx_value(self) -> int:
        return self.config_data.get("context_presets", {}).get(self.ctx_label_var.get(), 4096)

    def _locks(self) -> dict:
        return {
            "ux_lock": self.ux_lock.get(),
            "function_lock": self.function_lock.get(),
            "page_lock": self.page_lock.get(),
        }

    def _refresh_projects(self):
        self.store.ensure_project("_demo")
        self.project_list.delete(0, "end")
        for name in self.store.list_projects():
            self.project_list.insert("end", name)

    def _load_project_brief(self):
        project = self.current_project.get()
        self.brief_text.delete("1.0", "end")
        self.brief_text.insert("1.0", self.store.load_brief(project))

    def _refresh_project_files(self):
        self.files_list.delete(0, "end")
        project = self.store.ensure_project(self.current_project.get())
        for path in sorted(project.rglob("*")):
            if path.is_file():
                self.files_list.insert("end", path.relative_to(project).as_posix())

    def _append_log(self, msg: str):
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")

    def create_project(self):
        name = simpledialog.askstring("New Project", "Project name:")
        if not name:
            return
        self.store.ensure_project(name)
        self.current_project.set(name)
        self._refresh_projects()
        self._load_project_brief()
        self._refresh_project_files()

    def select_project(self, _event=None):
        selected = self.project_list.curselection()
        if not selected:
            return
        name = self.project_list.get(selected[0])
        self.current_project.set(name)
        self._load_project_brief()
        self._refresh_project_files()
        self.status_var.set(f"Selected project: {name}")

    def attach_file(self):
        chosen = filedialog.askopenfilename(title="Select file to attach")
        if not chosen:
            return
        dest = self.store.copy_attachment(self.current_project.get(), chosen)
        self._append_log(f"Attached copy saved: {dest.as_posix()}")
        self._refresh_project_files()

    def check_ollama(self):
        ok, msg = self.llm.check_connection()
        if not ok:
            messagebox.showerror("Ollama Check", msg)
            return
        model_ok, model_msg = self.llm.model_exists(self.model_var.get())
        if model_ok:
            messagebox.showinfo("Ollama Check", f"{msg}\n{model_msg}")
        else:
            messagebox.showwarning("Ollama Check", f"{msg}\n{model_msg}")

    def generate_plan(self):
        project = self.current_project.get()
        brief = self.brief_text.get("1.0", "end").strip()
        self.store.save_brief(project, brief)
        self.status_var.set("Running: Generating plan...")
        try:
            plan = self.orchestrator.generate_plan(project, self.model_var.get(), brief, self.temp_var.get(), self._ctx_value())
            self.plan_text.delete("1.0", "end")
            self.plan_text.insert("1.0", plan)
            self._append_log("Plan generated.")
            self.status_var.set("Idle")
            self._refresh_project_files()
        except Exception as exc:
            self.status_var.set("Error")
            messagebox.showerror("Plan generation failed", str(exc))

    def stop_run(self):
        self.orchestrator.stop()
        self.status_var.set("Stopped")
        self._append_log("Stop requested.")

    def _confirm_overwrite(self, path: str, preview: str) -> bool:
        return messagebox.askyesno("Confirm overwrite", f"File exists: {path}\n\n{preview}\n\nOverwrite?")

    def _confirm_command(self, cmd: str) -> bool:
        return messagebox.askyesno("Command Approval", f"Command is not on allowlist:\n{cmd}\n\nRun anyway?")

    def run_pipeline(self):
        project = self.current_project.get()
        brief = self.brief_text.get("1.0", "end").strip()
        plan = self.plan_text.get("1.0", "end").strip()
        if not plan:
            messagebox.showwarning("Missing plan", "Generate a plan first.")
            return

        self.status_var.set("Running")

        def worker():
            try:
                result = self.orchestrator.run(
                    project=project,
                    model=self.model_var.get(),
                    brief=brief,
                    plan=plan,
                    temperature=self.temp_var.get(),
                    num_ctx=self._ctx_value(),
                    locks=self._locks(),
                    confirm_overwrite=self._confirm_overwrite,
                    confirm_command=self._confirm_command,
                )
                self._append_log(result.get("message", "Run done."))
                self._append_log(f"Run folder: {result.get('run_dir', '')}")
                self.status_var.set("Idle" if result.get("ok") else "Error")
                self._refresh_project_files()
            except Exception as exc:
                self.status_var.set("Error")
                self._append_log(f"Run failed: {exc}")

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = AgentStudioApp()
    app.mainloop()
