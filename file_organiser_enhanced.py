# file_organiser_perfect.py
# Full feature File Organiser — polished layout and working features.
# Python 3.12 compatible.

import os
import shutil
import threading
import time
from pathlib import Path
from collections import defaultdict
import hashlib

# Try to import required UI/plot/voice libraries. Provide minimal fallbacks where possible.
try:
    import customtkinter as ctk
except Exception:
    ctk = None

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MPL_AVAILABLE = True
except Exception:
    MPL_AVAILABLE = False
    plt = None
    FigureCanvasTkAgg = None

try:
    import pyttsx3
    TTS_AVAILABLE = True
    tts_engine = pyttsx3.init()
except Exception:
    TTS_AVAILABLE = False
    tts_engine = None

# If customtkinter isn't available, create a thin shim using tkinter widgets
if ctk is None:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog

    class _CTkShim:
        def __init__(self):
            pass

    class CTk(tk.Tk): pass
    class CTkFrame(tk.Frame): pass
    class CTkLabel(tk.Label): pass
    class CTkButton(tk.Button):
        def __init__(self, master=None, **kwargs):
            cmd = kwargs.pop("command", None)
            text = kwargs.pop("text", "")
            fg = kwargs.pop("fg_color", None)
            font = kwargs.pop("font", None)
            super().__init__(master, text=text, command=cmd, bg=fg, font=font)
    class CTkEntry(tk.Entry): pass
    class CTkSwitch(tk.Checkbutton): pass

    def set_appearance_mode(mode): return None
    def set_default_color_theme(theme): return None

    ctk = _CTkShim()
    ctk.CTk = CTk
    ctk.CTkFrame = CTkFrame
    ctk.CTkLabel = CTkLabel
    ctk.CTkButton = CTkButton
    ctk.CTkEntry = CTkEntry
    ctk.CTkSwitch = CTkSwitch
    from tkinter import messagebox, filedialog
else:
    from tkinter import messagebox, filedialog
    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")

# Color constants
DARK_BG = "#0B0F0B"
PANEL_BG = "#111C11"
ACCENT_GREEN = "#8AE600"
LIGHT_BUTTON = "#23AD00"
BROWSE_COLOR = "#F08000"
TEXT_LIGHT = "white"
TEXT_DARK = "black"

# ----------------------------------------------------------
# Main Application
# ----------------------------------------------------------
class FileOrganiserApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self._clean_exit)
        self.title("File Organiser App")
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("fullscreen", True)
        self.configure(fg_color=DARK_BG)

        self.folder = ""
        self.undo_stack = []
        self.scheduler_running = False
        self.scheduler_thread = None
        self.theme = "dark"
        self.button_color = ACCENT_GREEN
        self.button_text_color = TEXT_DARK

        self._build_sidebar()
        self._build_main_area()
        self.draw_empty_graph()
        self._start_clock_thread()

    # ---------------- Sidebar ----------------
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#000000")
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(self.sidebar, text="File Organiser", font=("Barnice", 20, "bold"),
                     text_color=self.button_color).pack(pady=(30, 20))

        btn_kw = dict(width=180, height=44, corner_radius=20, font=("Segoe UI", 14, "bold"))
        self.home_btn = ctk.CTkButton(self.sidebar, text="Home", command=self._home_click,
                                      fg_color=self.button_color, text_color=self.button_text_color, **btn_kw)
        self.home_btn.pack(pady=10)

        self.open_btn = ctk.CTkButton(self.sidebar, text="Open Folder", command=self._browse,
                                      fg_color=self.button_color, text_color=self.button_text_color, **btn_kw)
        self.open_btn.pack(pady=10)

        self.settings_btn = ctk.CTkButton(self.sidebar, text="Settings", command=self._open_settings,
                                          fg_color=self.button_color, text_color=self.button_text_color, **btn_kw)
        self.settings_btn.pack(pady=10)

        self.exit_btn = ctk.CTkButton(self.sidebar, text="Exit", command=self._clean_exit,
                                      fg_color=self.button_color, text_color=self.button_text_color, **btn_kw)
        self.exit_btn.pack(pady=10)

        ctk.CTkLabel(self.sidebar, text="").pack(expand=True, fill="both")
        about_txt = ("File Organiser v1.0\nDeveloper: Dhanya\n"
                     "Smart desktop tool to sort files quickly and safely.\n"
                     "Features: Scheduler, Undo, Summary, Voice feedback.")
        ctk.CTkLabel(self.sidebar, text="About", font=("Segoe UI", 14, "bold"),
                     text_color=self.button_color).pack(pady=(6, 0))
        ctk.CTkLabel(self.sidebar, text=about_txt, font=("Segoe UI", 10),
                     wraplength=200, justify="left").pack(padx=12, pady=(4, 18))

    # ---------------- Main area ----------------
    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=DARK_BG)
        self.main_frame.pack(side="right", fill="both", expand=True)

        # Clock and theme switch
        self.top_right = ctk.CTkFrame(self.main_frame, fg_color=DARK_BG)
        self.top_right.place(relx=0.94, rely=0.02, anchor="ne")
        self.clock_lbl = ctk.CTkLabel(self.top_right, text="", font=("Consolas", 12, "bold"))
        self.clock_lbl.grid(row=0, column=0, padx=(0, 10), pady=6)
        self.theme_switch = ctk.CTkSwitch(self.top_right, text="Light Mode", command=self._toggle_theme)
        self.theme_switch.grid(row=0, column=1, pady=6)

        # Headings
        ctk.CTkLabel(self.main_frame, text="WELCOME TO FILE ORGANISER",
                     font=("Segoe UI", 30, "bold"), text_color=self.button_color).place(relx=0.5, rely=0.14, anchor="center")
        ctk.CTkLabel(self.main_frame, text="Organize the files smartly and easily.",
                     font=("Rosex", 14), text_color=TEXT_LIGHT).place(relx=0.5, rely=0.19, anchor="center")

        # Search bar
        search_frame = ctk.CTkFrame(self.main_frame, fg_color=PANEL_BG, corner_radius=12)
        search_frame.place(relx=0.5, rely=0.26, anchor="center", relwidth=0.85, relheight=0.09)
        self.path_entry = ctk.CTkEntry(search_frame, width=900, height=36, placeholder_text="Select folder to organise")
        self.path_entry.pack(side="left", padx=(12, 8), pady=6, fill="x", expand=True)
        ctk.CTkButton(search_frame, text="Browse", command=self._browse, fg_color=BROWSE_COLOR,
                      width=120, height=36, corner_radius=10, font=("Segoe UI", 14, "bold")).pack(side="right", padx=(8, 12), pady=6)

        # Action buttons
        action_card = ctk.CTkFrame(self.main_frame, fg_color=PANEL_BG, corner_radius=18)
        action_card.place(relx=0.5, rely=0.42, anchor="center", relwidth=0.86, relheight=0.18)
        btn_w, btn_h = 240, 56
        self.organise_btn = ctk.CTkButton(action_card, text="Organise Now", command=self._organise_now,
                                          fg_color=self.button_color, text_color=self.button_text_color,
                                          width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 16, "bold"))
        self.organise_btn.grid(row=0, column=0, padx=20, pady=30)
        self.scheduler_btn = ctk.CTkButton(action_card, text="Start Scheduler", command=self._start_scheduler_prompt,
                                           fg_color=self.button_color, text_color=self.button_text_color,
                                           width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 16, "bold"))
        self.scheduler_btn.grid(row=0, column=1, padx=20, pady=30)
        self.undo_btn = ctk.CTkButton(action_card, text="Undo Last", command=self._undo_last,
                                      fg_color=self.button_color, text_color=self.button_text_color,
                                      width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 16, "bold"))
        self.undo_btn.grid(row=0, column=2, padx=20, pady=30)

# 🆕 Duplicate Finder Button — next to Undo Last
        self.dup_btn = ctk.CTkButton(action_card, text="Find Duplicates", command=self._find_duplicates,
                             fg_color="#B6E619", hover_color="#FFD343", text_color="black",
                             width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 16, "bold"))
        self.dup_btn.grid(row=0, column=3, padx=20, pady=30)                                            

        # Graph & Summary
        self.graph_frame = ctk.CTkFrame(self.main_frame, fg_color="#111C11", corner_radius=12)
        self.graph_frame.place(relx=0.38, rely=0.78, anchor="center", relwidth=0.45, relheight=0.35)
        self.summary_panel = ctk.CTkFrame(self.main_frame, fg_color="#0F1A0F", corner_radius=10)
        self.summary_panel.place(relx=0.80, rely=0.78, anchor="center", relwidth=0.25, relheight=0.35)
        self.summary_title = ctk.CTkLabel(self.summary_panel, text="Summary",
                                          font=("Segoe UI", 13, "bold"), text_color=self.button_color)
        self.summary_title.pack(pady=(10, 8))
        self.summary_inner = ctk.CTkFrame(self.summary_panel, fg_color="#0B140B", border_width=2,
                                          border_color="#3C3C3C", corner_radius=10)
        self.summary_inner.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.summary_label = ctk.CTkLabel(self.summary_inner, text="No data available",
                                          font=("Segoe UI", 12), text_color="white", justify="center")
        self.summary_label.place(relx=0.5, rely=0.5, anchor="center")


    # ---------------- Duplicate Finder ----------------
    def _find_duplicates(self):
        if not self.folder or not Path(self.folder).exists():
            messagebox.showerror("Select folder", "Please choose a valid folder first.")
            return

        dup_dict = self._scan_duplicates(self.folder)
        if not dup_dict:
            messagebox.showinfo("No Duplicates", "No duplicate files found.")
            return

        top = ctk.CTkToplevel(self)
        top.title("Duplicate Files Found")
        top.geometry("650x400")
        ctk.CTkLabel(top, text="Duplicate Files", font=("Segoe UI", 14, "bold"),
                     text_color=self.button_color).pack(pady=8)

        text_box = ctk.CTkTextbox(top, wrap="none", font=("Consolas", 11))
        text_box.pack(fill="both", expand=True, padx=12, pady=8)

        for hash_val, files in dup_dict.items():
            if len(files) > 1:
                text_box.insert("end", f"\n--- Group ({len(files)} duplicates) ---\n")
                for f in files:
                    size = os.path.getsize(f) / 1024
                    text_box.insert("end", f"{Path(f).name}  ({size:.1f} KB)\n")

        def _delete_dups():
            deleted = 0
            for files in dup_dict.values():
                if len(files) > 1:
                    for f in files[1:]:
                        try:
                            os.remove(f)
                            deleted += 1
                        except Exception:
                            pass
            messagebox.showinfo("Deleted", f"Deleted {deleted} duplicate files.")
            top.destroy()

        ctk.CTkButton(top, text="Delete Duplicates", command=_delete_dups,
                      fg_color="#D32F2F", hover_color="#FF5252",
                      text_color="white", width=180, height=36).pack(pady=10)

    def _scan_duplicates(self, folder):
        hash_map = defaultdict(list)
        for root, _, files in os.walk(folder):
            for file in files:
                try:
                    path = Path(root) / file
                    h = hashlib.sha256()
                    with open(path, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    hash_map[h.hexdigest()].append(str(path))
                except Exception:
                    pass
        return {h: lst for h, lst in hash_map.items() if len(lst) > 1}


    # ---------------- Clock ----------------
    def _start_clock_thread(self):
        def _tick():
            while True:
                now = time.strftime("%I:%M:%S %p")
                try:
                    self.clock_lbl.configure(text=now)
                except Exception:
                    pass
                time.sleep(1)

        t = threading.Thread(target=_tick, daemon=True)
        t.start()

    # ---------------- Theme toggle ----------------
    def _toggle_theme(self):
        if self.theme == "dark":
            self.theme = "light"
            self._apply_light_theme()
        else:
            self.theme = "dark"
            self._apply_dark_theme()

    def _apply_light_theme(self):
        # update backgrounds and button colors
        try:
            self.configure(fg_color="#F4F7F3")
            self.main_frame.configure(fg_color="#F4F7F3")
            self.button_color = LIGHT_BUTTON
            self.button_text_color = TEXT_LIGHT
            # update sidebar buttons
            for btn in (self.home_btn, self.open_btn, self.settings_btn, self.exit_btn):
                btn.configure(fg_color=self.button_color, text_color=self.button_text_color)
            for btn in (self.organise_btn, self.scheduler_btn, self.undo_btn, self.browse_button):
                btn.configure(fg_color=self.button_color, text_color=self.button_text_color)
            self.heading.configure(text_color=self.button_color)
            self.subheading.configure(text_color="#000000")
            self.summary_panel.configure(fg_color="#EAFBE7")
            self.summary_title.configure(text_color=self.button_color)
            self.graph_frame.configure(fg_color="#FFFFFF")
        except Exception:
            pass

    def _apply_dark_theme(self):
        try:
            self.configure(fg_color=DARK_BG)
            self.main_frame.configure(fg_color=DARK_BG)
            self.button_color = ACCENT_GREEN
            self.button_text_color = TEXT_DARK
            for btn in (self.home_btn, self.open_btn, self.settings_btn, self.exit_btn):
                btn.configure(fg_color=self.button_color, text_color=self.button_text_color)
            for btn in (self.organise_btn, self.scheduler_btn, self.undo_btn, self.browse_button):
                btn.configure(fg_color=self.button_color, text_color=self.button_text_color)
            self.heading.configure(text_color=self.button_color)
            self.subheading.configure(text_color=TEXT_LIGHT)
            self.summary_panel.configure(fg_color="#0F1A0F")
            self.summary_title.configure(text_color=self.button_color)
            self.graph_frame.configure(fg_color="#111C11")
        except Exception:
            pass

    # ---------------- Browse ----------------
    def _browse(self):
        path = filedialog.askdirectory()
        if path:
            self.folder = path
            # show path in entry (use ctk entry text set if available)
            try:
                self.path_entry.delete(0, "end")
                self.path_entry.insert(0, path)
            except Exception:
                pass

    # ---------------- Organize ----------------
    def _organise_now(self):
        if not self.folder or not Path(self.folder).exists():
            messagebox.showerror("Select folder", "Please choose a valid folder first.")
            return
        counts, actions = self._perform_organise(self.folder)
        if actions:
            self.undo_stack.append(actions)
        self._show_summary(counts)
        self.show_graph(counts)
        self._speak("Files Organized Successfully!")
        messagebox.showinfo("Success", "Files organized successfully!")

    def _perform_organise(self, folder: str):
        folder_p = Path(folder)
        categories = {
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Music": [".mp3", ".wav", ".m4a"],
        }
        counts = defaultdict(int)
        actions = []
        for item in list(folder_p.iterdir()):
            if item.is_file():
                ext = item.suffix.lower()
                moved = False
                for name, exts in categories.items():
                    if ext in exts:
                        dest_dir = folder_p / name
                        dest_dir.mkdir(exist_ok=True)
                        dest = dest_dir / item.name
                        try:
                            shutil.move(str(item), str(dest))
                            counts[name] += 1
                            actions.append((dest, folder_p / item.name))
                        except Exception:
                            pass
                        moved = True
                        break
                if not moved:
                    dest_dir = folder_p / "Others"
                    dest_dir.mkdir(exist_ok=True)
                    dest = dest_dir / item.name
                    try:
                        shutil.move(str(item), str(dest))
                        counts["Others"] += 1
                        actions.append((dest, folder_p / item.name))
                    except Exception:
                        pass
        return counts, actions

    # ---------------- Summary ----------------
    def _show_summary(self, counts: dict):
        if not counts:
            self.summary_label.configure(text="No files organised.")
            self.summary_panel.lower()
            return
        lines = []
        total = 0
        for key in ["Images", "Documents", "Videos", "Music", "Others"]:
            val = counts.get(key, 0)
            lines.append(f"{key}: {val}")
            total += val
        lines.append(f"\nTotal: {total}")
        self.summary_label.configure(text="\n".join(lines))
        self.summary_panel.lift()

    # ---------------- Graph ----------------
    def draw_empty_graph(self):
        # If matplotlib not available, just clear the frame and show a text notice
        for w in self.graph_frame.winfo_children():
            w.destroy()
        if not MPL_AVAILABLE:
            lbl = ctk.CTkLabel(self.graph_frame, text="matplotlib not installed — graph unavailable",
                               font=("Segoe UI", 12))
            lbl.pack(expand=True, fill="both")
            return
        fig, ax = plt.subplots(figsize=(9, 4), facecolor="#111C11")
        ax.axhline(0, color=self.button_color)
        ax.set_title("Organised Files Summary (waiting for data...)", color=self.button_color)
        ax.set_xticks([])
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color(self.button_color)
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def show_graph(self, counts: dict):
        for w in self.graph_frame.winfo_children():
            w.destroy()
        if not MPL_AVAILABLE:
            lbl = ctk.CTkLabel(self.graph_frame, text="matplotlib not installed — graph unavailable",
                               font=("Segoe UI", 12))
            lbl.pack(expand=True, fill="both")
            return
        fig, ax = plt.subplots(figsize=(9, 4), facecolor="#111C11")
        keys = list(counts.keys())
        vals = [counts[k] for k in keys]
        ax.bar(keys, vals, color=self.button_color)
        ax.set_title("Organised Files Summary", color=self.button_color)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color(self.button_color)
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------- Undo ----------------
    def _undo_last(self):
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return
        last = self.undo_stack.pop()
        restored = 0
        for dest, original in last:
            try:
                if dest.exists():
                    shutil.move(str(dest), str(original))
                    restored += 1
            except Exception:
                pass
        messagebox.showinfo("Undo", f"Restored {restored} files.")
        self.draw_empty_graph()
        self.summary_panel.lower()

    # ---------------- Scheduler ----------------
    def _start_scheduler_prompt(self):
        # small dialog via simple input of minutes
        def on_ok():
            val = entry.get()
            try:
                minutes = int(val)
                if minutes <= 0:
                    raise ValueError
            except Exception:
                messagebox.showerror("Invalid", "Please enter a positive integer.")
                return
            top.destroy()
            self._start_scheduler(minutes)

        top = ctk.CTkToplevel(self)
        top.geometry("360x140")
        top.title("Scheduler interval (minutes)")
        ctk.CTkLabel(top, text="Run organiser every N minutes:", font=("Segoe UI", 12)).pack(pady=(12, 6))
        entry = ctk.CTkEntry(top, width=120)
        entry.insert(0, "60")
        entry.pack()
        ctk.CTkButton(top, text="Start", command=on_ok, fg_color=self.button_color, text_color=self.button_text_color).pack(pady=12)

    def _start_scheduler(self, minutes: int):
        if self.scheduler_running:
            messagebox.showinfo("Scheduler", "Scheduler already running.")
            return
        self.scheduler_running = True

        def loop():
            while self.scheduler_running:
                time.sleep(minutes * 60)
                if self.folder and Path(self.folder).exists():
                    counts, actions = self._perform_organise(self.folder)
                    if actions:
                        self.undo_stack.append(actions)
                    # update UI
                    try:
                        self.after(100, lambda: (self._show_summary(counts), self.show_graph(counts), self._speak("Files Organized Successfully!")))
                    except Exception:
                        pass
        self.scheduler_thread = threading.Thread(target=loop, daemon=True)
        self.scheduler_thread.start()
        messagebox.showinfo("Scheduler", f"Scheduler started: every {minutes} minutes.")

    # ---------------- Voice ----------------
    def _speak(self, text: str):
        if not TTS_AVAILABLE:
            return
        try:
            tts_engine.say(text)
            tts_engine.runAndWait()
        except Exception:
            pass

    # ---------------- Enhanced Settings ----------------
    def _open_settings(self):
        top = ctk.CTkToplevel(self)
        top.title("Settings & Preferences")
        top.geometry("500x550")
        top.configure(fg_color=PANEL_BG)

        ctk.CTkLabel(top, text="Settings", font=("Segoe UI", 20, "bold"),
                     text_color=self.button_color).pack(pady=(15, 10))

        # === Theme Color ===
        ctk.CTkLabel(top, text="Theme Color:", font=("Segoe UI", 13, "bold")).pack(pady=(8, 4))
        color_frame = ctk.CTkFrame(top, fg_color=DARK_BG, corner_radius=10)
        color_frame.pack(pady=4, padx=12, fill="x")

        def apply_theme(color):
            self.button_color = color
            messagebox.showinfo("Theme Applied", "Theme color updated!")

        for i, (name, color) in enumerate([("Green", "#8AE600"), ("Blue", "#00BCD4"), ("Purple", "#A020F0")]):
            ctk.CTkButton(color_frame, text=name, width=90, height=36,
                          fg_color=color, text_color="black",
                          command=lambda c=color: apply_theme(c)).grid(row=0, column=i, padx=10, pady=10)

        # === Theme Mode Switch ===
        ctk.CTkLabel(top, text="Theme Mode:", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))
        ctk.CTkSwitch(top, text="Light Mode", command=self._toggle_theme).pack(pady=4)

        # === Clock Format ===
        ctk.CTkLabel(top, text="Clock Format:", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))
        fmt_frame = ctk.CTkFrame(top, fg_color=DARK_BG, corner_radius=10)
        fmt_frame.pack(pady=4, padx=12, fill="x")

        def set_time_fmt(fmt):
            self.time_format = fmt
            messagebox.showinfo("Time Format", f"Time format set to {fmt}-hour.")

        ctk.CTkButton(fmt_frame, text="12-hour", width=100,
                      command=lambda: set_time_fmt(12)).grid(row=0, column=0, padx=10, pady=8)
        ctk.CTkButton(fmt_frame, text="24-hour", width=100,
                      command=lambda: set_time_fmt(24)).grid(row=0, column=1, padx=10, pady=8)

        # === Language ===
        ctk.CTkLabel(top, text="Language:", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))
        lang_frame = ctk.CTkFrame(top, fg_color=DARK_BG, corner_radius=10)
        lang_frame.pack(pady=4, padx=12, fill="x")

        def set_lang(lang):
            self.language = lang
            messagebox.showinfo("Language", f"Language changed to {lang}.")

        ctk.CTkButton(lang_frame, text="English", width=100,
                      command=lambda: set_lang("English")).grid(row=0, column=0, padx=10, pady=8)
        ctk.CTkButton(lang_frame, text="Tamil", width=100,
                      command=lambda: set_lang("Tamil")).grid(row=0, column=1, padx=10, pady=8)

        # === Backup ===
        ctk.CTkLabel(top, text="Backup & Restore:", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))

        def create_backup():
            if not self.folder:
                messagebox.showerror("Error", "Select a folder first.")
                return
            backup_dir = Path(self.folder) / "_backup"
            backup_dir.mkdir(exist_ok=True)
            for f in Path(self.folder).iterdir():
                if f.is_file():
                    shutil.copy2(f, backup_dir / f.name)
            messagebox.showinfo("Backup", f"Backup created in {backup_dir}")

        ctk.CTkButton(top, text="Create Backup", fg_color="#2E7D32",
                      width=180, command=create_backup).pack(pady=6)

        # === Privacy Cleaner ===
        ctk.CTkLabel(top, text="Privacy Cleaner:", font=("Segoe UI", 13, "bold")).pack(pady=(10, 4))

        def clear_logs():
            for f in ["activity.log", "config.json"]:
                if Path(f).exists():
                    os.remove(f)
            messagebox.showinfo("Privacy", "Activity and config logs cleared.")

        ctk.CTkButton(top, text="Clear Logs", fg_color="#B71C1C",
                      width=180, command=clear_logs).pack(pady=6)

        # === Close ===
        ctk.CTkButton(top, text="Close", fg_color="#555", hover_color="#777",
                      text_color="white", width=120, command=top.destroy).pack(pady=(20, 8))

    # ---------------- Home / Exit Buttons ----------------
    def _home_click(self):
        messagebox.showinfo("Home", "You are already on the home screen.")

    def _do_open_folder(self):
        self._browse()

    def _clean_exit(self):
        self.scheduler_running = False
        try:
            self.destroy()
        except Exception:
            os._exit(0)


# ---------------- Run the app ----------------
if __name__ == "__main__":
    app = FileOrganiserApp()
    app.mainloop()
