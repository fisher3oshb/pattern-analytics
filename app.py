import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from src.predictor import PatternAnalyzer

FONT_MONO = ("Courier New", 10)
FONT_UI   = ("Helvetica", 11)
BG        = "#1e1e2e"
BG2       = "#2a2a3e"
FG        = "#cdd6f4"
ACCENT    = "#89b4fa"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pattern Analytics — Аналіз логістики")
        self.geometry("1100x750")
        self.configure(bg=BG)
        self.resizable(True, True)

        self.analyzer = PatternAnalyzer(radius_km=5.0, min_samples=2, max_gap_hours=8.0)
        self._build_ui()

    def _build_ui(self):
        # Top bar
        top = tk.Frame(self, bg=BG, pady=8)
        top.pack(fill="x", padx=12)

        tk.Label(top, text="Pattern Analytics", font=("Helvetica", 14, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")

        self.status_var = tk.StringVar(value="Готовий")
        tk.Label(top, textvariable=self.status_var, font=FONT_UI,
                 bg=BG, fg=GREEN).pack(side="right")

        # Main pane: left=input, right=report
        pane = tk.PanedWindow(self, orient="horizontal", bg=BG, sashwidth=6,
                              sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # --- Left panel ---
        left = tk.Frame(pane, bg=BG2, padx=8, pady=8)
        pane.add(left, minsize=340)

        tk.Label(left, text="Вставте дані (текст або CSV):", font=FONT_UI,
                 bg=BG2, fg=FG).pack(anchor="w")

        self.input_box = scrolledtext.ScrolledText(
            left, font=FONT_MONO, bg="#13131f", fg=FG,
            insertbackground=FG, relief="flat", height=18,
        )
        self.input_box.pack(fill="both", expand=True, pady=(4, 8))

        # Settings row
        cfg = tk.Frame(left, bg=BG2)
        cfg.pack(fill="x", pady=(0, 6))

        tk.Label(cfg, text="Радіус км:", bg=BG2, fg=FG, font=FONT_UI).pack(side="left")
        self.radius_var = tk.StringVar(value="5")
        tk.Entry(cfg, textvariable=self.radius_var, width=5, bg="#13131f",
                 fg=FG, insertbackground=FG, relief="flat").pack(side="left", padx=(2, 12))

        tk.Label(cfg, text="Макс. пауза год:", bg=BG2, fg=FG, font=FONT_UI).pack(side="left")
        self.gap_var = tk.StringVar(value="8")
        tk.Entry(cfg, textvariable=self.gap_var, width=5, bg="#13131f",
                 fg=FG, insertbackground=FG, relief="flat").pack(side="left", padx=(2, 0))

        # Accumulate checkbox
        self.accumulate_var = tk.BooleanVar(value=True)
        tk.Checkbutton(left, text="Накопичувати в базі", variable=self.accumulate_var,
                       bg=BG2, fg=FG, selectcolor="#13131f",
                       activebackground=BG2, font=FONT_UI).pack(anchor="w", pady=(0, 8))

        btn_frame = tk.Frame(left, bg=BG2)
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="▶  Аналізувати", font=("Helvetica", 11, "bold"),
                  bg=ACCENT, fg="#1e1e2e", relief="flat", padx=14, pady=6,
                  cursor="hand2", command=self._run).pack(side="left", padx=(0, 8))

        tk.Button(btn_frame, text="Очистити поле", font=FONT_UI,
                  bg=BG, fg=FG, relief="flat", padx=10, pady=6,
                  cursor="hand2", command=lambda: self.input_box.delete("1.0", "end")
                  ).pack(side="left")

        tk.Button(btn_frame, text="Скинути базу", font=FONT_UI,
                  bg=RED, fg="#1e1e2e", relief="flat", padx=10, pady=6,
                  cursor="hand2", command=self._reset_db).pack(side="right")

        # --- Right panel ---
        right = tk.Frame(pane, bg=BG, padx=8, pady=8)
        pane.add(right, minsize=500)

        tk.Label(right, text="Звіт:", font=FONT_UI, bg=BG, fg=FG).pack(anchor="w")

        self.report_box = scrolledtext.ScrolledText(
            right, font=FONT_MONO, bg="#13131f", fg=FG,
            state="disabled", relief="flat",
        )
        self.report_box.pack(fill="both", expand=True, pady=(4, 0))

        # Coloring tags
        self.report_box.tag_config("header", foreground=ACCENT, font=("Courier New", 10, "bold"))
        self.report_box.tag_config("priority_high", foreground=RED, font=("Courier New", 10, "bold"))
        self.report_box.tag_config("priority_med", foreground=GREEN)
        self.report_box.tag_config("peak", foreground=GREEN)

    def _run(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Немає даних", "Вставте дані у ліве поле.")
            return

        try:
            radius = float(self.radius_var.get())
            gap = float(self.gap_var.get())
        except ValueError:
            messagebox.showerror("Помилка", "Невірне значення радіусу або паузи.")
            return

        self.analyzer.radius_km = radius
        self.analyzer.max_gap_hours = gap

        try:
            if self.accumulate_var.get():
                added = self.analyzer.ingest(text, source="manual")
                self.analyzer.fit_from_db()
                self.status_var.set(f"Додано {added} нових подій  |  всього в базі: {len(self.analyzer.events)}")
            else:
                self.analyzer.load(text).fit()
                self.status_var.set(f"Завантажено {len(self.analyzer.events)} подій (без збереження)")

            report = self.analyzer.full_report(from_time=datetime.utcnow())
            self._show_report(report)

        except Exception as exc:
            messagebox.showerror("Помилка аналізу", str(exc))

    def _show_report(self, text: str):
        self.report_box.configure(state="normal")
        self.report_box.delete("1.0", "end")
        for line in text.splitlines():
            tag = None
            if line.startswith("=") or line.strip().startswith("["):
                tag = "header"
            elif "!!! ПРІОРИТЕТ" in line or "!! Важливо" in line:
                tag = "priority_high"
            elif "◄ ПІКОВА" in line:
                tag = "peak"
            if tag:
                self.report_box.insert("end", line + "\n", tag)
            else:
                self.report_box.insert("end", line + "\n")
        self.report_box.configure(state="disabled")
        self.report_box.see("1.0")

    def _reset_db(self):
        from src.storage import DB_PATH
        if messagebox.askyesno("Скинути базу", "Видалити всі накопичені дані?"):
            if DB_PATH.exists():
                DB_PATH.unlink()
            self.analyzer = PatternAnalyzer(
                radius_km=float(self.radius_var.get()),
                max_gap_hours=float(self.gap_var.get()),
            )
            self._show_report("База даних скинута.")
            self.status_var.set("База скинута")


if __name__ == "__main__":
    App().mainloop()
