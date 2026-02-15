from __future__ import annotations

import subprocess
import tempfile
import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText

from core import (
    MODEL_NAME,
    SUPPORTED_LANGUAGES,
    answer_question,
    list_lessons,
    make_anchor_script,
    ollama_health,
    read_lesson,
)

BG = "#000000"
PANEL = "#111111"
TEXT = "#FFFFFF"
ACCENT = "#FFD400"


class SeniorsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AI for Seniors - Offline Desktop")
        self.root.geometry("1500x860")
        self.root.configure(bg=BG)

        self.lesson_content = ""
        self.language_var = tk.StringVar(value="English")

        self.build_layout()
        self.load_health()
        self.load_lessons()

    def build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        self.root.grid_columnconfigure(2, weight=2)
        self.root.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.root, bg=PANEL, bd=2, relief="groove")
        center = tk.Frame(self.root, bg=PANEL, bd=2, relief="groove")
        right = tk.Frame(self.root, bg=PANEL, bd=2, relief="groove")
        left.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        center.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        right.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)

        tk.Label(left, text="Lessons", fg=ACCENT, bg=PANEL, font=("Arial", 20, "bold")).pack(anchor="w", padx=10, pady=(10, 4))
        self.health_var = tk.StringVar(value="Checking local Ollama...")
        tk.Label(left, textvariable=self.health_var, fg="#8CFFB1", bg=PANEL, font=("Arial", 14)).pack(anchor="w", padx=10, pady=(0, 6))

        self.lesson_list = tk.Listbox(left, font=("Arial", 16), bg="#1B1B1B", fg=TEXT, selectbackground=ACCENT, selectforeground="#000")
        self.lesson_list.pack(fill="both", expand=True, padx=10, pady=10)
        self.lesson_list.bind("<<ListboxSelect>>", self.on_lesson_select)

        header = tk.Frame(center, bg=PANEL)
        header.pack(fill="x", padx=10, pady=10)
        tk.Label(header, text="AI for Seniors (Desktop GUI)", fg=ACCENT, bg=PANEL, font=("Arial", 22, "bold")).pack(side="left")
        tk.Button(header, text="Print lesson", font=("Arial", 14, "bold"), bg=ACCENT, fg="#000", command=self.print_lesson).pack(side="right")

        self.lesson_text = ScrolledText(center, font=("Arial", 17), bg="#000", fg=TEXT, insertbackground=TEXT, wrap="word")
        self.lesson_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.lesson_text.insert("1.0", "Select a lesson from the left.")

        top_controls = tk.Frame(right, bg=PANEL)
        top_controls.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top_controls, text="Ask a question", fg=ACCENT, bg=PANEL, font=("Arial", 20, "bold")).pack(anchor="w")

        lang_row = tk.Frame(top_controls, bg=PANEL)
        lang_row.pack(fill="x", pady=(6, 0))
        tk.Label(lang_row, text="Language:", fg=TEXT, bg=PANEL, font=("Arial", 14, "bold")).pack(side="left")
        language_menu = tk.OptionMenu(lang_row, self.language_var, *SUPPORTED_LANGUAGES.keys())
        language_menu.config(font=("Arial", 13, "bold"), bg=ACCENT, fg="#000", highlightthickness=0)
        language_menu["menu"].config(font=("Arial", 12), bg="#222", fg=TEXT)
        language_menu.pack(side="left", padx=8)

        self.question_text = ScrolledText(right, font=("Arial", 16), height=5, bg="#FFF", fg="#000", wrap="word")
        self.question_text.pack(fill="x", padx=10)

        tk.Button(right, text="Ask", font=("Arial", 14, "bold"), bg=ACCENT, fg="#000", command=self.ask_question).pack(fill="x", padx=10, pady=6)

        btn_row = tk.Frame(right, bg=PANEL)
        btn_row.pack(fill="x", padx=10)
        for txt in ["Explain simpler", "Give an example", "Common mistake", "Safety tip"]:
            tk.Button(btn_row, text=txt, font=("Arial", 12, "bold"), bg=ACCENT, fg="#000", command=lambda t=txt: self.append_prompt(t)).pack(fill="x", pady=3)

        self.answer_text = ScrolledText(right, font=("Arial", 15), height=8, bg="#1F1F1F", fg=TEXT, wrap="word")
        self.answer_text.pack(fill="both", expand=False, padx=10, pady=8)
        self.answer_text.insert("1.0", "Your answer will appear here.")

        tk.Label(right, text="AI Video Anchor", fg=ACCENT, bg=PANEL, font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(6, 4))
        tk.Button(right, text="Generate anchor script", font=("Arial", 14, "bold"), bg=ACCENT, fg="#000", command=self.run_anchor).pack(fill="x", padx=10, pady=4)
        tk.Button(right, text="Play anchor voice", font=("Arial", 13, "bold"), bg=ACCENT, fg="#000", command=self.play_voice).pack(fill="x", padx=10, pady=4)

        self.anchor_text = ScrolledText(right, font=("Arial", 15), height=9, bg="#1F1F1F", fg=TEXT, wrap="word")
        self.anchor_text.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.anchor_text.insert("1.0", "Anchor script will appear here.")

    def current_language(self) -> str:
        return self.language_var.get()

    def load_health(self) -> None:
        state = ollama_health()
        if state["ollama"] == "ok" and state["model_ready"]:
            self.health_var.set(f"Ollama ready: {MODEL_NAME}")
        elif state["ollama"] == "ok":
            self.health_var.set(f"Ollama online; missing model: {MODEL_NAME}")
        else:
            self.health_var.set("Ollama not reachable. Start local Ollama.")

    def load_lessons(self) -> None:
        self.lesson_list.delete(0, tk.END)
        for lesson in list_lessons():
            self.lesson_list.insert(tk.END, lesson)

    def on_lesson_select(self, _event: object) -> None:
        pick = self.lesson_list.curselection()
        if not pick:
            return
        lesson_name = self.lesson_list.get(pick[0])
        self.lesson_content = read_lesson(lesson_name)
        self.lesson_text.delete("1.0", tk.END)
        self.lesson_text.insert("1.0", self.lesson_content)

    def append_prompt(self, text: str) -> None:
        current = self.question_text.get("1.0", tk.END).strip()
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert("1.0", f"{current}\n{text}".strip())

    def ask_question(self) -> None:
        q = self.question_text.get("1.0", tk.END).strip()
        ans = answer_question(q, self.current_language())
        self.answer_text.delete("1.0", tk.END)
        self.answer_text.insert("1.0", ans)

    def run_anchor(self) -> None:
        topic = self.question_text.get("1.0", tk.END).strip()
        script = make_anchor_script(topic, self.current_language())
        self.anchor_text.delete("1.0", tk.END)
        self.anchor_text.insert("1.0", script)

    def play_voice(self) -> None:
        text = self.anchor_text.get("1.0", tk.END).strip()
        if not text or "will appear here" in text:
            messagebox.showinfo("AI Video Anchor", "Generate an anchor script first.")
            return
        ps = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            "$s.Rate = -1;"
            f"$s.Speak(@'{text}'@);"
        )
        try:
            subprocess.Popen(["powershell", "-NoProfile", "-Command", ps])
        except OSError:
            messagebox.showwarning("Voice playback", "Could not start local voice playback.")

    def print_lesson(self) -> None:
        text = self.lesson_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("Print lesson", "Select a lesson first.")
            return
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as tmp:
            tmp.write(text)
            path = tmp.name
        try:
            subprocess.Popen(["notepad.exe", "/p", path])
        except OSError:
            messagebox.showwarning("Print lesson", f"Could not print. File saved at: {path}")


if __name__ == "__main__":
    root = tk.Tk()
    SeniorsApp(root)
    root.mainloop()
