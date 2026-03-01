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
        self.title("AI Agent Studio (Local)")
        self.geometry("1100x750")

        self.store = ProjectStore()
        self.llm = OllamaClient()
        self.orchestrator = StudioOrchestrator(
            llm=self.llm,
            store=self.store,
        )

        self.current_project = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Idle")

        self._build_ui()
        self._refresh_projects()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Project").pack(side="left")
        self.project_combo = ttk.Combobox(top, textvariable=self.current_project, width=40)
        self.project_combo.pack(side="left", padx=8)
        self.project_combo.bind("<<ComboboxSelected>>", lambda e: self._load_project())

        ttk.Button(top, text="New", command=self.new_project).pack(side="left", padx=4)
        ttk.Button(top, text="Open Folder", command=self.open_project_folder).pack(side="left", padx=4)
        ttk.Button(top, text="Refresh", command=self._refresh_projects).pack(side="left", padx=4)

        ttk.Label(top, text="Status:").pack(side="left", padx=(20, 4))
        ttk.Label(top, textvariable=self.status_var).pack(side="left")

        mid = ttk.Panedwindow(self, orient="horizontal")
        mid.pack(fill="both", expand=True, padx=10, pady=8)

        left = ttk.Frame(mid)
        right = ttk.Frame(mid)
        mid.add(left, weight=2)
        mid.add(right, weight=3)

        # Left: brief + plan
        ttk.Label(left, text="Brief / Request").pack(anchor="w")
        self.brief_text = tk.Text(left, height=10)
        self.brief_text.pack(fill="x", pady=(4, 10))

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(0, 10))
        ttk.Button(btns, text="Generate Plan", command=self.generate_plan).pack(side="left")
        ttk.Button(btns, text="Save Brief", command=self.save_brief).pack(side="left", padx=6)

        ttk.Label(left, text="Plan").pack(anchor="w")
        self.plan_text = tk.Text(left, height=18)
        self.plan_text.pack(fill="both", expand=True, pady=(4, 10))

        runbar = ttk.Frame(left)
        runbar.pack(fill="x")
        ttk.Button(runbar, text="Run Pipeline", command=self.run_pipeline).pack(side="left")
        ttk.Button(runbar, text="Stop", command=self.stop_run).pack(side="left", padx=6)

        # Right: log + files
        tabs = ttk.Notebook(right)
        tabs.pack(fill="both", expand=True)

        log_tab = ttk.Frame(tabs)
        files_tab = ttk.Frame(tabs)

        tabs.add(log_tab, text="Live Log")
        tabs.add(files_tab, text="Project Files")

        self.log_text = tk.Text(log_tab, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=6, pady=6)

        files_top = ttk.Frame(files_tab)
        files_top.pack(fill="x", padx=6, pady=6)
        ttk.Button(files_top, text="Refresh Files", command=self._refresh_project_files).pack(side="left")
        ttk.Button(files_top, text="Open File", command=self.open_selected_file).pack(side="left", padx=6)

        self.files_list = tk.Listbox(files_tab)
        self.files_list.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _append_log(self, line: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh_projects(self):
        projects = self.store.list_projects()
        self.project_combo["values"] = projects
        if projects and (self.current_project.get() not in projects):
            self.current_project.set(projects[0])
            self._load_project()

    def _load_project(self):
        project = self.current_project.get().strip()
        if not project:
            return

        data = self.store.load_project(project)
        brief = data.get("brief", "")
        plan = data.get("plan", "")

        self.brief_text.delete("1.0", "end")
        self.brief_text.insert("1.0", brief)

        self.plan_text.delete("1.0", "end")
        self.plan_text.insert("1.0", plan)

        self._append_log(f"Loaded project: {project}")
        self._refresh_project_files()

    def new_project(self):
        name = simpledialog.askstring("New Project", "Project name:")
        if not name:
            return
        name = name.strip()
        if not name:
            return

        self.store.create_project(name)
        self._refresh_projects()
        self.current_project.set(name)
        self._load_project()

    def open_project_folder(self):
        project = self.current_project.get().strip()
        if not project:
            messagebox.showwarning("No project", "Select a project first.")
            return
        folder = self.store.project_path(project)
        try:
            import os
            os.startfile(str(folder))
        except Exception as e:
            messagebox.showerror("Open folder failed", str(e))

    def _refresh_project_files(self):
        self.files_list.delete(0, "end")
        project = self.current_project.get().strip()
        if not project:
            return
        root = self.store.project_path(project)
        if not root.exists():
            return

        files = []
        for p in root.rglob("*"):
            if p.is_file():
                rel = p.relative_to(root)
                files.append(str(rel))
        files.sort()
        for f in files:
            self.files_list.insert("end", f)

    def open_selected_file(self):
        project = self.current_project.get().strip()
        if not project:
            return
        sel = self.files_list.curselection()
        if not sel:
            return
        rel = self.files_list.get(sel[0])
        path = self.store.project_path(project) / rel
        try:
            import os
            os.startfile(str(path))
        except Exception as e:
            messagebox.showerror("Open file failed", str(e))

    def save_brief(self):
        project = self.current_project.get().strip()
        if not project:
            messagebox.showwarning("No project", "Select a project first.")
            return
        brief = self.brief_text.get("1.0", "end").strip()
        self.store.save_brief(project, brief)
        self._append_log("Brief saved.")

    def generate_plan(self):
        project = self.current_project.get().strip()
        if not project:
            messagebox.showwarning("No project", "Select a project first.")
            return
        brief = self.brief_text.get("1.0", "end").strip()
        if not brief:
            messagebox.showwarning("Missing brief", "Enter a brief/request first.")
            return

        self.status_var.set("Running: Generating plan...")
        self._append_log("Generating plan...")

        try:
            plan = self.orchestrator.generate_plan(project, brief)
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

    # --- Thread-safe UI confirmation helper (fixes Tkinter thread issues) ---
    def _ui_ask(self, fn):
        done = threading.Event()
        out = {"val": None, "err": None}

        def run():
            try:
                out["val"] = fn()
            except Exception as e:
                out["err"] = e
            finally:
                done.set()

        self.after(0, run)  # run on Tk main thread
        done.wait()
        if out["err"]:
            raise out["err"]
        return out["val"]

    def _confirm_overwrite(self, path: str, preview: str) -> bool:
        def ask():
            return messagebox.askyesno(
                "Confirm overwrite",
                f"File exists: {path}\n\n{preview}\n\nOverwrite?"
            )

        return self._ui_ask(ask)

    def _confirm_command(self, cmd: str) -> bool:
        def ask():
            return messagebox.askyesno(
                "Command Approval",
                f"Command is not on allowlist:\n{cmd}\n\nRun anyway?"
            )

        return self._ui_ask(ask)

    def run_pipeline(self):
        project = self.current_project.get().strip()
        brief = self.brief_text.get("1.0", "end").strip()
        plan = self.plan_text.get("1.0", "end").strip()

        if not project:
            messagebox.showwarning("No project", "Select a project first.")
            return
        if not plan:
            messagebox.showwarning("Missing plan", "Generate a plan first.")
            return

        self.status_var.set("Running")
        self._append_log("Running pipeline...")

        def worker():
            try:
                result = self.orchestrator.run(
                    project=project,
                    plan=plan,
                    confirm_overwrite=self._confirm_overwrite,
                    confirm_command=self._confirm_command,
                    log=self._append_log,
                )
                ok = result.get("ok", False)
                msg = result.get("message", "")
                if ok:
                    self._append_log("Pipeline completed successfully.")
                    if msg:
                        self._append_log(msg)
                    self.status_var.set("Idle")
                else:
                    self._append_log("Pipeline failed.")
                    if msg:
                        self._append_log(msg)
                    self.status_var.set("Error")
                self._refresh_project_files()
            except Exception as exc:
                self.status_var.set("Error")
                self._append_log(f"Pipeline error: {exc}")

        t = threading.Thread(target=worker, daemon=True)
        t.start()


def main():
    app = AgentStudioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
