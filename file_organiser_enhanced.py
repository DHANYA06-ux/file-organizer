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
import concurrent.futures

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

        # UI-disable helper (used while heavy moves run)
        self._ui_disabled = False

        self._build_sidebar()
        self._build_main_area()
        self.draw_empty_graph()
        self._start_clock_thread()

    def _log(self, msg: str):
        """Append a small log entry to activity.log for diagnostics."""
        try:
            with open("activity.log", "a", encoding="utf-8") as fh:
                fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception:
            pass

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

        # 🟢 Animated Heading
        self.heading = ctk.CTkLabel(
            self.main_frame, text="WELCOME TO FILE ORGANISER",
            font=("Segoe UI", 30, "bold"), text_color="#00FFAA"
        )
        self.heading.place(relx=0.5, rely=0.14, anchor="center")

        # Color animation (multi-color loop)
        # Color animation (use Tkinter-safe after loop instead of updating GUI from a background thread)
        def animate_colors(i=0):
            try:
                colors = ["#66FF00", "#00FF99", "#81EA00", "#0FDF65", "#8AE600"]
                self.heading.configure(text_color=colors[i % len(colors)])
                self.after(100, lambda: animate_colors(i + 1))
            except Exception:
                try:
                    self._log("animate_colors error")
                except Exception:
                    pass

        animate_colors()

        # Subheading
        self.subheading = ctk.CTkLabel(
            self.main_frame, text="Organize the files smartly and easily.",
            font=("Calibri", 14), text_color=TEXT_LIGHT
        )
        self.subheading.place(relx=0.5, rely=0.19, anchor="center")

        # 🟢 Rounded Search Bar + Glow Effect
        search_frame = ctk.CTkFrame(
            self.main_frame, fg_color=PANEL_BG,
            corner_radius=18, border_width=2, border_color="#0A0101"
        )
        search_frame.place(relx=0.5, rely=0.26, anchor="center", relwidth=0.85, relheight=0.09)

        # Shadow glow (fake layer behind)
        glow = ctk.CTkFrame(self.main_frame, fg_color="#1F231F", corner_radius=18)
        glow.place(relx=0.5, rely=0.262, anchor="center", relwidth=0.855, relheight=0.092)
        glow.lower(search_frame)

        self.path_entry = ctk.CTkEntry(
            search_frame, width=900, height=36,
            placeholder_text="Select folder to organise", corner_radius=12
        )
        self.path_entry.pack(side="left", padx=(12, 8), pady=6, fill="x", expand=True)

        self.browse_button = ctk.CTkButton(
            search_frame, text="Browse", command=self._browse,
            fg_color=BROWSE_COLOR, hover_color="#FF9933",
            width=120, height=36, corner_radius=10,
            font=("Segoe UI", 14, "bold")
        )
        self.browse_button.pack(side="right", padx=(8, 12), pady=6)

        # Action buttons
        action_card = ctk.CTkFrame(self.main_frame, fg_color=PANEL_BG, corner_radius=18)
        action_card.place(relx=0.5, rely=0.42, anchor="center", relwidth=0.86, relheight=0.18)
        btn_w, btn_h = 240, 56
        self.organise_btn = ctk.CTkButton(action_card, text="Organise Now", command=self._organise_now,
                                          fg_color=self.button_color, text_color=self.button_text_color,
                                          width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 20, "bold"))
        self.organise_btn.grid(row=0, column=0, padx=20, pady=30)
        self.scheduler_btn = ctk.CTkButton(action_card, text="Start Scheduler", command=self._start_scheduler_prompt,
                                           fg_color=self.button_color, text_color=self.button_text_color,
                                           width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 20, "bold"))
        self.scheduler_btn.grid(row=0, column=1, padx=20, pady=30)
        self.undo_btn = ctk.CTkButton(action_card, text="Undo Last", command=self._undo_last,
                                      fg_color=self.button_color, text_color=self.button_text_color,
                                      width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 20, "bold"))
        self.undo_btn.grid(row=0, column=2, padx=20, pady=30)
        # Duplicate Finder Button
        self.dup_btn = ctk.CTkButton(action_card, text="Find Duplicates", command=self._find_duplicates,
                             fg_color="#B6E619", hover_color="#FFD343", text_color="black",
                             width=btn_w, height=btn_h, corner_radius=22, font=("Segoe UI", 20, "bold"))
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
        # Show a results window immediately and run scanning in background to keep UI responsive
        top = ctk.CTkToplevel(self)
        top.title("Duplicate Files - Scanning...")
        top.geometry("650x400")
        ctk.CTkLabel(top, text="Duplicate Files", font=("Segoe UI", 14, "bold"),
                     text_color=self.button_color).pack(pady=8)

        text_box = ctk.CTkTextbox(top, wrap="none", font=("Consolas", 11))
        text_box.pack(fill="both", expand=True, padx=12, pady=8)

        status_lbl = ctk.CTkLabel(top, text="Scanning, please wait...", font=("Segoe UI", 11))
        status_lbl.pack(pady=(4, 8))

        def do_scan():
            try:
                dup_dict = self._scan_duplicates(self.folder)
            except Exception as e:
                dup_dict = {}
                try:
                    self._log(f"_scan_duplicates failed: {e}")
                except Exception:
                    pass

            def show_results():
                status_lbl.configure(text="Scan complete")
                if not dup_dict:
                    text_box.insert("end", "No duplicate files found.\n")
                    return
                for hash_val, files in dup_dict.items():
                    if len(files) > 1:
                        text_box.insert("end", f"\n--- Group ({len(files)} duplicates) ---\n")
                        for f in files:
                            try:
                                size = os.path.getsize(f) / 1024
                                text_box.insert("end", f"{Path(f).name}  ({size:.1f} KB)\n")
                            except Exception:
                                text_box.insert("end", f"{Path(f).name}  (size unknown)\n")

                def _delete_dups():
                    deleted = 0
                    for files in dup_dict.values():
                        if len(files) > 1:
                            for f in files[1:]:
                                try:
                                    os.remove(f)
                                    deleted += 1
                                except Exception:
                                    try:
                                        self._log(f"Failed to delete duplicate: {f}")
                                    except Exception:
                                        pass
                    messagebox.showinfo("Deleted", f"Deleted {deleted} duplicate files.")
                    top.destroy()

                ctk.CTkButton(top, text="Delete Duplicates", command=_delete_dups,
                              fg_color="#D32F2F", hover_color="#FF5252",
                              text_color="white", width=180, height=36).pack(pady=10)

            # schedule UI update on main thread
            try:
                self.after(0, show_results)
            except Exception:
                pass

        threading.Thread(target=do_scan, daemon=True).start()

    def _scan_duplicates(self, folder):
        # Faster duplicate detection using size prefilter + sample-first hashing + parallel workers
        SAMPLE_SIZE = 16 * 1024  # 16KB sample for quick elimination
        max_workers = min(32, (os.cpu_count() or 1) * 4)

        # 1) Group files by size
        size_map = defaultdict(list)
        for root, _, files in os.walk(folder):
            for fname in files:
                try:
                    p = Path(root) / fname
                    try:
                        sz = p.stat().st_size
                    except Exception:
                        continue
                    # skip zero-size files quickly
                    size_map[sz].append(str(p))
                except Exception:
                    continue

        # 2) For groups with >1 file, compute a sample hash (first SAMPLE_SIZE bytes) in parallel
        def sample_hash(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read(SAMPLE_SIZE)
                h = hashlib.sha256()
                h.update(data)
                return (path, h.hexdigest())
            except Exception:
                try:
                    self._log(f"sample_hash failed: {path}")
                except Exception:
                    pass
                return (path, None)

        sample_groups = defaultdict(list)  # (size, sample_hash) -> [paths]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = []
            for sz, paths in size_map.items():
                if len(paths) < 2:
                    continue
                for path in paths:
                    futures.append(exe.submit(sample_hash, path))

            for fut in concurrent.futures.as_completed(futures):
                try:
                    path, sh = fut.result()
                    if sh is None:
                        continue
                    try:
                        sz = Path(path).stat().st_size
                    except Exception:
                        continue
                    sample_groups[(sz, sh)].append(path)
                except Exception:
                    continue

        # 3) For sample groups with >1 file, compute full hash (in parallel) and collect duplicates
        def full_hash(path):
            try:
                h = hashlib.sha256()
                with open(path, 'rb') as f:
                    for chunk in iter(lambda: f.read(65536), b''):
                        h.update(chunk)
                return (path, h.hexdigest())
            except Exception:
                try:
                    self._log(f"full_hash failed: {path}")
                except Exception:
                    pass
                return (path, None)

        hash_map = defaultdict(list)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as exe:
            futures = []
            for (sz, sh), paths in sample_groups.items():
                if len(paths) < 2:
                    continue
                for path in paths:
                    futures.append(exe.submit(full_hash, path))

            for fut in concurrent.futures.as_completed(futures):
                try:
                    path, fh = fut.result()
                    if fh:
                        hash_map[fh].append(path)
                except Exception:
                    continue

        # Only return groups with actual duplicates
        return {h: lst for h, lst in hash_map.items() if len(lst) > 1}


    # ---------------- Clock ----------------
    def _start_clock_thread(self):
        # Use Tkinter after scheduling rather than a background thread to update GUI safely
        def _tick():
            try:
                now = time.strftime("%I:%M:%S %p")
                self.clock_lbl.configure(text=now)
            except Exception:
                try:
                    self._log("clock update failed")
                except Exception:
                    pass
            try:
                self.after(1000, _tick)
            except Exception:
                pass

        _tick()

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

        # Disable heavy UI interactions while organizing to prevent UI-side slowdowns
        def _disable_ui():
            try:
                for btn in (self.organise_btn, self.scheduler_btn, self.undo_btn, self.browse_button, self.dup_btn):
                    try:
                        btn.configure(state="disabled")
                    except Exception:
                        pass
                self._ui_disabled = True
            except Exception:
                pass

        def _enable_ui():
            try:
                for btn in (self.organise_btn, self.scheduler_btn, self.undo_btn, self.browse_button, self.dup_btn):
                    try:
                        btn.configure(state="normal")
                    except Exception:
                        pass
                self._ui_disabled = False
            except Exception:
                pass

        # 🟦 Show progress bar
        self.progress = ctk.CTkProgressBar(self.main_frame, mode="indeterminate", width=400)
        self.progress.place(relx=0.5, rely=0.48, anchor="center")
        self.progress.start()

        # disable UI immediately on main thread
        try:
            self.after(0, _disable_ui)
        except Exception:
            pass

        def run_task():
            try:
                counts, actions = self._perform_organise(self.folder)
                if actions:
                    self.undo_stack.append(actions)
                # schedule graph & summary update on main thread
                self.after(0, lambda: self._show_summary_and_graph(counts))
                try:
                    self._speak("Files Organized Successfully!")
                except Exception:
                    pass
                # show toast on main thread
                try:
                    self.after(0, lambda: self.show_toast("✅ Files Organised Successfully!"))
                except Exception:
                    pass
            except Exception as e:
                try:
                    self._log(f"Organise failed: {e}")
                except Exception:
                    pass
                try:
                    self.after(0, lambda: messagebox.showerror("Error", "Organising failed. See activity.log"))
                except Exception:
                    pass
            finally:
                try:
                    # stop progress and hide it on main thread
                    self.after(0, lambda: (self.progress.stop(), self.progress.place_forget()))
                    # re-enable UI on main thread
                    self.after(0, _enable_ui)
                except Exception:
                    pass

        threading.Thread(target=run_task, daemon=True).start()

    # helper to update summary + graph in main thread
    def _show_summary_and_graph(self, counts):
        self._show_summary(counts)
        self._show_graph_main(counts)

    # ---------------- Toast Message ----------------
    def show_toast(self, msg: str):
        toast = ctk.CTkLabel(self.main_frame, text=msg,
                             fg_color="#1E90FF", text_color="white",
                             corner_radius=8, font=("Segoe UI", 13, "bold"))
        toast.place(relx=0.83, rely=0.1, anchor="ne")

        # auto-hide after 2.5 seconds
        self.after(2500, toast.destroy)


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
        # schedule actual drawing on main thread
        self.after(0, self._draw_empty_graph_main)

    def _draw_empty_graph_main(self):
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
        # always schedule graph updates on main thread
        self.after(0, lambda: self._show_graph_main(counts))

    def _show_graph_main(self, counts: dict):
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

    # ---------------- Undo (Fast + Correct) ----------------
    def _undo_last(self):
        if not self.undo_stack:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        last = self.undo_stack.pop()
        restore_list = []

        for dest, original in last:
            dest_p = Path(dest)
            orig_p = Path(original)
            if dest_p.exists():
                # recreate missing folders if needed
                orig_p.parent.mkdir(parents=True, exist_ok=True)
                restore_list.append((str(dest_p), str(orig_p)))

        if not restore_list:
            messagebox.showinfo("Undo", "No valid files to restore.")
            return

        restored = 0
        restored_lock = threading.Lock()

        def restore_one(src, dst):
            nonlocal restored
            try:
                # Prevent overwrite
                dst_path = Path(dst)
                if dst_path.exists():
                    base, ext = dst_path.stem, dst_path.suffix
                    dst_path = dst_path.parent / f"{base}_restored{ext}"

                try:
                    os.replace(src, dst_path)
                except Exception:
                    shutil.move(src, dst_path)

                with restored_lock:
                    restored += 1
            except Exception as e:
                self._log(f"Undo failed: {src} -> {dst} | {e}")

        # Run restores in parallel
        max_workers = min(8, os.cpu_count() or 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(lambda pair: restore_one(*pair), restore_list))

        messagebox.showinfo("Undo", f"Restored {restored} files successfully.")
        self.draw_empty_graph()
        self.summary_panel.lower()


    # ---------------- Scheduler Prompt ----------------
    def _start_scheduler_prompt(self):
        """Ask user for interval before starting the scheduler."""
        import tkinter.simpledialog as sd
        minutes = sd.askinteger("Scheduler", "Run every how many minutes?", minvalue=1, initialvalue=5)
        if minutes:
            self._start_scheduler(minutes)


    # ---------------- Scheduler ----------------
    def _start_scheduler(self, minutes: int):
        if self.scheduler_running:
            messagebox.showinfo("Scheduler", "Scheduler already running.")
            return
        self.scheduler_running = True

        def loop():
            while self.scheduler_running:
                time.sleep(minutes * 60)
                if self.folder and Path(self.folder).exists():
                    # Run organise inside GUI thread using 'after'
                    self.after(0, self._run_scheduled_task)

        self.scheduler_thread = threading.Thread(target=loop, daemon=True)
        self.scheduler_thread.start()
        messagebox.showinfo("Scheduler", f"Scheduler started: every {minutes} minutes.")

    def _run_scheduled_task(self):
        counts, actions = self._perform_organise(self.folder)
        if actions:
            self.undo_stack.append(actions)
        # ensure UI updates happen on main thread
        self.after(0, lambda: self._show_summary_and_graph(counts))
        self._speak("Files Organized Successfully!")

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

    # ---------------- Core Organising Logic (Optimised with Document Subfolders + speedups) ----------------
    def _perform_organise(self, folder: str):
        """
        Optimized performing of organising:
         - Collect moves first (single scan)
         - Perform parallel moves using ThreadPoolExecutor and os.replace (fast same-drive renames)
         - Use locks to safely update counts and actions from worker threads
         - Avoid repeated expensive stat/hash operations
        """
        counts = {"Images": 0, "Documents": 0, "Videos": 0, "Music": 0, "Others": 0}
        actions = []
        exts = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".pptx", ".xlsx"],
            "Videos": [".mp4", ".avi", ".mov", ".mkv"],
            "Music": [".mp3", ".wav", ".aac", ".flac"]
        }

        # Mapping of subfolders inside "Documents"
        doc_subfolders = {
            ".pdf": "PDFs",
            ".docx": "Word",
            ".doc": "Word",
            ".xlsx": "Excel",
            ".xls": "Excel",
            ".pptx": "PowerPoint",
            ".ppt": "PowerPoint",
            ".txt": "Text"
        }

        folder_path = Path(folder)

        # Step 1: collect all top-level files and their target destinations (single pass, no per-file scanning)
        file_moves = []  # list of tuples (src_path_str, dest_path_str, category_key)
        try:
            for file_path in folder_path.iterdir():
                try:
                    if not file_path.is_file():
                        continue
                    ext = file_path.suffix.lower()
                    moved_category = None
                    # Determine category and destination (documents may have subfolder)
                    for cat, ext_list in exts.items():
                        if ext in ext_list:
                            dest = folder_path / cat
                            if cat == "Documents":
                                sub = doc_subfolders.get(ext)
                                if sub:
                                    dest = dest / sub
                            dest.mkdir(parents=True, exist_ok=True)
                            new_path = dest / file_path.name
                            file_moves.append((str(file_path), str(new_path), cat))
                            moved_category = cat
                            break
                    if moved_category is None:
                        dest = folder_path / "Others"
                        dest.mkdir(exist_ok=True)
                        new_path = dest / file_path.name
                        file_moves.append((str(file_path), str(new_path), "Others"))
                except Exception:
                    # keep going even if a particular file caused an exception
                    try:
                        self._log(f"collect move failed for {file_path}")
                    except Exception:
                        pass
                    continue
        except Exception:
            # fallback: keep counts/actions empty if the scan fails
            try:
                self._log("Top-level scan failed in _perform_organise")
            except Exception:
                pass
            return counts, actions

        # Step 2: perform moves in parallel
        # fast_move uses os.replace for same-drive moves (instant) and falls back to shutil.move
        move_lock = threading.Lock()
        MAX_WORKERS = min(12, max(2, (os.cpu_count() or 1) * 2))

        def fast_move(src, dst, category):
            """
            Move file src -> dst quickly:
             - try os.replace (rename) first for same-filesystem speed
             - fallback to shutil.move if needed (cross-device)
            Update counts and actions under lock for thread safety.
            """
            nonlocal counts, actions
            try:
                # If destination already exists, attempt to generate a unique name (preserve)
                dst_p = Path(dst)
                if dst_p.exists():
                    # create a unique name (append counter)
                    base = dst_p.stem
                    suff = dst_p.suffix
                    parent = dst_p.parent
                    i = 1
                    while True:
                        cand = parent / f"{base} ({i}){suff}"
                        if not cand.exists():
                            dst_p = cand
                            dst = str(dst_p)
                            break
                        i += 1

                try:
                    os.replace(src, dst)  # fast rename when same filesystem
                except Exception:
                    # fallback (handles cross-device moves)
                    shutil.move(src, dst)

                # record action (new_path, original_path) for undo
                with move_lock:
                    actions.append((dst, src))
                    if category in counts:
                        counts[category] += 1
                    else:
                        counts["Others"] += 1
            except Exception as e:
                try:
                    self._log(f"fast_move failed for {src} -> {dst}: {e}")
                except Exception:
                    pass
                # do not raise; we just skip failed moves here

        # If there are many document moves, it's common they are the slower ones; parallelize all moves
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as exe:
                futures = []
                for src, dst, cat in file_moves:
                    futures.append(exe.submit(fast_move, src, dst, cat))
                # Wait for all to complete; we don't need their return values
                for fut in concurrent.futures.as_completed(futures):
                    try:
                        fut.result()
                    except Exception:
                        # already logged inside fast_move
                        pass
        except Exception:
            try:
                # final fallback: sequential moves (should rarely be hit)
                for src, dst, cat in file_moves:
                    fast_move(src, dst, cat)
            except Exception:
                pass

        # Step 3: return aggregated counts and actions
        return counts, actions


# ---------------- Run the app ----------------
if __name__ == "__main__":
    app = FileOrganiserApp()
    # ---- Safe Exit Protection ----
    def safe_quit():
        try:
           app.destroy()
        except Exception:
           pass

    app.protocol("WM_DELETE_WINDOW", safe_quit)
# ---- End Safe Exit Protection ----

    app.mainloop()
