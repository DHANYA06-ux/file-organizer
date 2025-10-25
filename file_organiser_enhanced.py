import shutil, json, subprocess, platform, hashlib, logging, threading, time, schedule
from pathlib import Path
from collections import defaultdict
import customtkinter as ctk
from tkinter import messagebox, filedialog, simpledialog, Toplevel, Text, END
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ---------- Config / Logging ----------
CONFIG_FILE = "config.json"
LOG_FILE = "activity.log"
UNDO_TEMP = "last_move.json"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ---------- Config Helpers ----------
def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {k: set(v) for k, v in data.items()}
    except FileNotFoundError:
        messagebox.showerror("Config missing", f"{CONFIG_FILE} not found.")
        return {}
    except json.JSONDecodeError:
        messagebox.showerror("Config error", f"{CONFIG_FILE} contains invalid JSON.")
        return {}

def save_config(config_dict):
    serializable = {k: sorted(list(v)) for k, v in config_dict.items()}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    logging.info("Config saved.")

def category_for_extension(ext: str, config: dict) -> str:
    ext = ext.lower()
    for category, exts in config.items():
        if ext in exts:
            return category
    return "Others"

def compute_md5(path: Path, chunk_size=8192) -> str:
    import hashlib
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
    except Exception:
        return ""
    return h.hexdigest()

def ensure_unique(dest: Path) -> Path:
    if not dest.exists():
        return dest
    counter = 1
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1

def open_in_explorer(path: Path):
    if not path.exists():
        messagebox.showerror("Not found", f"Path does not exist: {path}")
        return
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.run(["explorer", str(path)])
        elif system == "Darwin":
            subprocess.run(["open", str(path)])
        else:
            subprocess.run(["xdg-open", str(path)])
    except Exception as e:
        messagebox.showerror("Open error", str(e))

# ---------- Main GUI ----------
class FileOrganiserApp:
    def __init__(self, master):
        self.master = master
        master.title("File Organiser — Enhanced")
        master.geometry("850x500")
        master.resizable(True, True)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.config = load_config()
        self.moved_records = []
        self.stop_flag = False
        self.scheduler_running = False

        # ---------- Path Entry ----------
        self.title_label = ctk.CTkLabel(master, text="Path to organise:", font=("Segoe UI", 22, "bold"), text_color="#ffa726")
        self.title_label.pack(pady=(15, 5))

        self.path_var = ctk.StringVar()
        path_frame = ctk.CTkFrame(master, corner_radius=10)
        path_frame.pack(padx=15, pady=5, fill="x")

        self.path_entry = ctk.CTkEntry(path_frame, textvariable=self.path_var, font=("Segoe UI", 14))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)

        browse_btn = ctk.CTkButton(path_frame, text="Browse", command=self.browse_folder, fg_color="#ff5722",
                                   hover_color="#ff7043", corner_radius=10)
        browse_btn.pack(side="right", padx=6, pady=6)

        # ---------- Action Buttons ----------
        btn_frame = ctk.CTkFrame(master, corner_radius=10)
        btn_frame.pack(padx=12, pady=10, fill="x")

        self.organise_btn = ctk.CTkButton(btn_frame, text="Organise", command=self.organise_clicked,
                                          fg_color="#00c853", corner_radius=10)
        self.organise_btn.pack(side="left", padx=6, pady=6)

        self.undo_btn = ctk.CTkButton(btn_frame, text="Undo Last", command=self.undo_last,
                                      fg_color="#2bbd2b", corner_radius=10)
        self.undo_btn.pack(side="left", padx=6, pady=6)

        self.open_folder_btn = ctk.CTkButton(btn_frame, text="Open Folder", command=self.open_root,
                                             fg_color="#26ac26", corner_radius=10)
        self.open_folder_btn.pack(side="left", padx=6, pady=6)

        self.view_log_btn = ctk.CTkButton(btn_frame, text="View Log", command=self.view_log,
                                          fg_color="#1f961f", corner_radius=10)
        self.view_log_btn.pack(side="left", padx=6, pady=6)

        self.auto_btn = ctk.CTkButton(btn_frame, text="Start Auto-Scheduler", command=self.start_scheduler_prompt,
                                      fg_color="#1d891d", corner_radius=10)
        self.auto_btn.pack(side="left", padx=6, pady=6)

        # ---------- Progress ----------
        self.progress = ctk.CTkProgressBar(master, width=700)
        self.progress.pack(padx=12, pady=10)
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(master, text="Ready", anchor="w", font=("Segoe UI", 12))
        self.status_label.pack(fill="x", padx=12)

        # ---------- Category Buttons ----------
        self.cat_frame = ctk.CTkFrame(master, corner_radius=10)
        self.cat_frame.pack(padx=12, pady=10, fill="x")
        self.refresh_category_buttons()

    # ---------- Helpers ----------
    def refresh_category_buttons(self):
        for w in self.cat_frame.winfo_children():
            w.destroy()
        categories = list(self.config.keys()) + ["Others", "NoExtension", "Duplicates"]
        for cat in categories:
            b = ctk.CTkButton(self.cat_frame, text=cat, width=120, corner_radius=10,
                              fg_color="#f9a825", hover_color="#ffb300",
                              command=lambda c=cat: self.open_category(c))
            b.pack(side="left", padx=6, pady=6)

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_var.set(folder)

    def open_root(self):
        p = Path(self.path_var.get().strip())
        if not p.exists():
            messagebox.showerror("Invalid path", "Set a valid path first.")
            return
        open_in_explorer(p)

    def view_log(self):
        p = Path(LOG_FILE)
        if not p.exists():
            messagebox.showinfo("No logs", "No logs found yet.")
            return
        open_in_explorer(p)

    def open_category(self, category_name: str):
        p = Path(self.path_var.get().strip())
        if not p.exists():
            messagebox.showerror("Invalid path", "Set a valid path first.")
            return
        target = p / category_name
        if not target.exists():
            messagebox.showinfo("Not found", f"Folder '{category_name}' does not exist yet.")
            return
        open_in_explorer(target)

    # ---------- Organising ----------
    def organise_clicked(self):
        p = Path(self.path_var.get().strip())
        if not p.exists():
            messagebox.showerror("Invalid path", "Please provide a valid directory path.")
            return
        self.organise_btn.configure(state="disabled")
        self.undo_btn.configure(state="disabled")
        threading.Thread(target=self._organise_worker, args=(p,), daemon=True).start()

    def _organise_worker(self, path: Path):
        try:
            files = [f for f in path.iterdir() if f.is_file()]
            total = len(files)
            if total == 0:
                self._update_status("No files to organise.")
                return
            self.moved_records = []
            self._update_progress(0)
            counts = defaultdict(int)
            sizes = defaultdict(int)
            hash_map = {}

            for i, file in enumerate(files, 1):
                ext = file.suffix[1:] if file.suffix.startswith(".") else file.suffix
                folder_name = category_for_extension(ext, self.config) if ext else "NoExtension"
                file_hash = compute_md5(file)
                is_duplicate = False

                if file_hash:
                    existing = hash_map.get(file_hash)
                    if existing:
                        dest_folder = path / "Duplicates"
                        dest_folder.mkdir(exist_ok=True)
                        dest = ensure_unique(dest_folder / file.name)
                        shutil.move(str(file), str(dest))
                        counts["Duplicates"] += 1
                        sizes["Duplicates"] += dest.stat().st_size
                        is_duplicate = True
                    else:
                        hash_map[file_hash] = file

                if not is_duplicate:
                    folder_path = path / folder_name
                    folder_path.mkdir(exist_ok=True)
                    dest = ensure_unique(folder_path / file.name)
                    shutil.move(str(file), str(dest))
                    counts[folder_name] += 1
                    sizes[folder_name] += dest.stat().st_size

                self._update_progress(i / total)

            with open(UNDO_TEMP, "w", encoding="utf-8") as f:
                json.dump(self.moved_records, f, indent=2)

            self._show_summary(counts, sizes)
            self._update_status(f"Done. {sum(counts.values())} files organised.")
        except Exception as e:
            logging.exception("Organise failed")
            messagebox.showerror("Error", str(e))
        finally:
            self.master.after(200, lambda: self.organise_btn.configure(state="normal"))
            self.master.after(200, lambda: self.undo_btn.configure(state="normal"))
            self.master.after(200, self.refresh_category_buttons)

    def _update_progress(self, val):
        self.master.after(1, lambda: self.progress.set(val))

    def _update_status(self, text):
        self.master.after(1, lambda: self.status_label.configure(text=text))

    # ---------- Summary + Bar Graph ----------
    def _show_summary(self, counts, sizes):
        def human(n):
            for unit in ["B", "KB", "MB", "GB"]:
                if n < 1024:
                    return f"{n:.1f}{unit}"
                n /= 1024
            return f"{n:.1f}TB"

        summary = ["Summary of organise:\n"]
        total_files, total_size = 0, 0
        for cat, cnt in counts.items():
            sz = sizes.get(cat, 0)
            summary.append(f"{cat}: {cnt} files, {human(sz)}")
            total_files += cnt
            total_size += sz
        summary.append(f"\nTotal: {total_files} files, {human(total_size)}")

        self.master.after(1, lambda: messagebox.showinfo("Summary", "\n".join(summary)))
        self.master.after(1, lambda: self._show_bar_graph(counts))

    def _show_bar_graph(self, counts):
        if not counts:
            return
        top = Toplevel(self.master)
        top.title("File Distribution")
        top.geometry("600x400")

        categories = list(counts.keys())
        values = [counts[c] for c in categories]

        fig, ax = plt.subplots(figsize=(6, 4), facecolor="#2b2b2b")
        bars = ax.bar(categories, values, color="#ff9800")
        ax.set_title("Files Organised by Category", color="white", fontsize=12)
        ax.set_xlabel("Category", color="white")
        ax.set_ylabel("File Count", color="white")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, yval + 0.1, str(yval),
                    ha='center', va='bottom', color='white', fontsize=9)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------- Undo ----------
    def undo_last(self):
        p = Path(UNDO_TEMP)
        if not p.exists():
            messagebox.showinfo("Nothing to undo", "No previous organise found.")
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception as e:
            messagebox.showerror("Undo error", str(e))
            return
        if not messagebox.askyesno("Confirm Undo", "Restore moved files?"):
            return

        for src, dst in reversed(records):
            try:
                dstp = Path(dst)
                srcp = Path(src)
                if dstp.exists():
                    shutil.move(str(dstp), str(srcp))
            except Exception as e:
                logging.error(f"Undo failed: {e}")

        p.unlink(missing_ok=True)
        messagebox.showinfo("Undo Complete", "Restored all files successfully.")

    # ---------- Auto Scheduler ----------
    def start_scheduler_prompt(self):
        folder = self.path_var.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showerror("Invalid path", "Please select a valid folder first.")
            return
        interval = simpledialog.askinteger("Interval (minutes)", "Enter interval:", initialvalue=1440, minvalue=1)
        if interval:
            self.start_auto_scheduler(folder, interval)
            messagebox.showinfo("Auto-Scheduler", f"Organiser will run every {interval} minutes.")

    def start_auto_scheduler(self, folder_path, interval_minutes=1440):
        if self.scheduler_running:
            messagebox.showinfo("Scheduler", "Already running.")
            return
        self.scheduler_running = True
        folder_path = Path(folder_path)

        def job():
            if folder_path.exists():
                self._organise_worker(folder_path)
        schedule.every(interval_minutes).minutes.do(job)

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(10)

        threading.Thread(target=run_scheduler, daemon=True).start()
        logging.info(f"Scheduler started for {folder_path}")

# ---------- Run ----------
if __name__ == "__main__":
    root = ctk.CTk()
    app = FileOrganiserApp(root)
    root.mainloop()
