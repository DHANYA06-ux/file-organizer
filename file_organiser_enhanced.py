import shutil
import json
import subprocess
import platform
import hashlib
import logging
import threading
import time
from pathlib import Path
from collections import defaultdict
from tkinter import (
    Tk, Menu, Frame, Label, Entry, Button, StringVar, messagebox, Toplevel, Text, END, DISABLED, NORMAL
)
from tkinter import filedialog, simpledialog, ttk
import schedule  # <- NEW for auto-scheduler

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
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
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

# ---------- GUI App ----------
class FileOrganiserApp:
    def __init__(self, master):
        self.master = master
        master.title("File Organiser — Enhanced")
        master.geometry("680x300")
        master.resizable(False, False)

        self.config = load_config()
        self.moved_records = []  # for undo
        self.stop_flag = False
        self.scheduler_running = False

        # Menubar
        menubar = Menu(master)
        organiser_menu = Menu(menubar, tearoff=0)
        organiser_menu.add_command(label="Select Folder...", command=self.browse_folder)
        organiser_menu.add_command(label="Edit Categories...", command=self.open_config_editor)
        organiser_menu.add_separator()
        organiser_menu.add_command(label="Quit", command=master.quit)
        menubar.add_cascade(label="Organiser", menu=organiser_menu)
        master.config(menu=menubar)

        # Path entry
        frame = Frame(master)
        frame.pack(padx=12, pady=8, fill="x")
        Label(frame, text="Path to organise:").grid(row=0, column=0, sticky="w")
        self.path_var = StringVar()
        self.entry = Entry(frame, textvariable=self.path_var, width=72)
        self.entry.grid(row=1, column=0, columnspan=3, pady=6, sticky="w")
        browse_btn = Button(frame, text="Browse", command=self.browse_folder, width=10)
        browse_btn.grid(row=1, column=3, padx=6)

        # Buttons
        btn_frame = Frame(master)
        btn_frame.pack(padx=12, pady=4, fill="x")
        self.organise_btn = Button(btn_frame, text="Organise", width=16, command=self.organise_clicked)
        self.organise_btn.grid(row=0, column=0, padx=6)
        self.undo_btn = Button(btn_frame, text="Undo last organise", width=16, command=self.undo_last)
        self.undo_btn.grid(row=0, column=1, padx=6)
        self.open_root_btn = Button(btn_frame, text="Open Folder", width=12, command=self.open_root)
        self.open_root_btn.grid(row=0, column=2, padx=6)
        self.open_logs_btn = Button(btn_frame, text="View Log", width=12, command=self.view_log)
        self.open_logs_btn.grid(row=0, column=3, padx=6)
        self.auto_btn = Button(btn_frame, text="Start Auto-Scheduler", width=18, command=self.start_scheduler_prompt)
        self.auto_btn.grid(row=0, column=4, padx=6)

        # Progress
        self.progress = ttk.Progressbar(master, orient="horizontal", length=640, mode="determinate")
        self.progress.pack(padx=12, pady=8)
        self.status_label = Label(master, text="Ready", anchor="w")
        self.status_label.pack(fill="x", padx=12)

        # category quick-open buttons
        self.cat_frame = Frame(master)
        self.cat_frame.pack(padx=12, pady=6, fill="x")
        self.refresh_category_buttons()

    # ---------- GUI Helper ----------
    def refresh_category_buttons(self):
        for w in self.cat_frame.winfo_children():
            w.destroy()
        categories = list(self.config.keys()) + ["Others", "NoExtension", "Duplicates"]
        col = 0
        for cat in categories:
            b = Button(self.cat_frame, text=cat, width=12, command=lambda c=cat: self.open_category(c))
            b.grid(row=0, column=col, padx=4)
            col += 1

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
            messagebox.showinfo("Not found", f"Folder for category '{category_name}' does not exist yet.")
            return
        open_in_explorer(target)

    # ---------- Organise ----------
    def organise_clicked(self):
        p = Path(self.path_var.get().strip())
        if not p.exists():
            messagebox.showerror("Invalid path", "Please provide a valid directory path to organise.")
            return
        self.organise_btn.config(state=DISABLED)
        self.undo_btn.config(state=DISABLED)
        self.stop_flag = False
        t = threading.Thread(target=self._organise_worker, args=(p,), daemon=True)
        t.start()

    def _organise_worker(self, path: Path):
        try:
            files = [f for f in path.iterdir() if f.is_file()]
            total = len(files)
            if total == 0:
                self._update_status("No files to organise.")
                return
            self.moved_records = []
            self._update_progress(0, total)
            counts = defaultdict(int)
            sizes = defaultdict(int)
            hash_map = {}
            for i, file in enumerate(files, 1):
                if self.stop_flag:
                    break
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
                        logging.info(f"Duplicate moved: {file} -> {dest}")
                        self.moved_records.append((str(file), str(dest)))
                        counts["Duplicates"] += 1
                        sizes["Duplicates"] += dest.stat().st_size
                        is_duplicate = True
                    else:
                        hash_map[file_hash] = file
                if is_duplicate:
                    self._update_progress(i, total)
                    continue
                folder_path = path / folder_name
                folder_path.mkdir(exist_ok=True)
                dest = ensure_unique(folder_path / file.name)
                try:
                    shutil.move(str(file), str(dest))
                    self.moved_records.append((str(file), str(dest)))
                    counts[folder_name] += 1
                    sizes[folder_name] += dest.stat().st_size
                    logging.info(f"Moved: {file} -> {dest}")
                except Exception as e:
                    logging.error(f"Failed to move {file}: {e}")
                self._update_progress(i, total)
            try:
                with open(UNDO_TEMP, "w", encoding="utf-8") as f:
                    json.dump(self.moved_records, f, indent=2)
            except Exception as e:
                logging.error("Failed to write undo file: " + str(e))
            self._show_summary(counts, sizes)
            self._update_status(f"Done. {sum(counts.values())} files organised.")
        except Exception as e:
            logging.exception("Organise failed")
            self._update_status("Error during organise.")
            messagebox.showerror("Error", str(e))
        finally:
            self.master.after(200, lambda: self.organise_btn.config(state=NORMAL))
            self.master.after(200, lambda: self.undo_btn.config(state=NORMAL))
            self.master.after(200, self.refresh_category_buttons)
            self._update_progress(0, 1)

    # ---------- Progress Helpers ----------
    def _update_progress(self, current, total):
        def apply():
            if total <= 0:
                self.progress["value"] = 0
                self.progress["maximum"] = 1
            else:
                self.progress["maximum"] = total
                self.progress["value"] = current
            self.status_label.config(text=f"Processing {current}/{total}")
        self.master.after(1, apply)

    def _update_status(self, text):
        self.master.after(1, lambda: self.status_label.config(text=text))

    def _show_summary(self, counts: dict, sizes: dict):
        def human(n):
            for unit in ["B", "KB", "MB", "GB"]:
                if n < 1024: return f"{n:.1f}{unit}"
                n /= 1024
            return f"{n:.1f}TB"
        text_lines = ["Summary of organise:\n"]
        total_files = 0
        total_size = 0
        for cat, cnt in counts.items():
            sz = sizes.get(cat, 0)
            total_files += cnt
            total_size += sz
            text_lines.append(f"{cat}: {cnt} files, {human(sz)}")
        text_lines.append("\nTotal: {} files, {}".format(total_files, human(total_size)))
        self.master.after(1, lambda: messagebox.showinfo("Organise Summary", "\n".join(text_lines)))

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
            messagebox.showerror("Undo error", "Failed to read undo file: " + str(e))
            return
        if not messagebox.askyesno("Confirm undo", "Restore moved files to their original locations?"):
            return
        failed = []
        restored = 0
        for src, dst in reversed(records):
            try:
                dstp = Path(dst)
                srcp = Path(src)
                if dstp.exists():
                    dest_parent = srcp.parent
                    dest_parent.mkdir(parents=True, exist_ok=True)
                    final_dest = ensure_unique(srcp)
                    shutil.move(str(dstp), str(final_dest))
                    logging.info(f"Undo: {dstp} -> {final_dest}")
                    restored += 1
                else:
                    failed.append(dst)
            except Exception as e:
                logging.error("Undo failed for {}: {}".format(dst, e))
                failed.append(dst)
        if failed:
            messagebox.showwarning("Partial undo", f"Restored {restored} files. Failed for {len(failed)} files.")
        else:
            messagebox.showinfo("Undo complete", f"Restored {restored} files.")
        try:
            p.unlink()
        except Exception:
            pass

    # ---------- Config Editor ----------
    def open_config_editor(self):
        top = Toplevel(self.master)
        top.title("Edit Categories & Extensions")
        top.geometry("600x420")
        top.transient(self.master)
        txt = Text(top)
        initial = {k: sorted(list(v)) for k, v in self.config.items()}
        txt.insert(END, json.dumps(initial, indent=2))
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        def save_and_close():
            try:
                data = json.loads(txt.get("1.0", END))
                self.config = {k: set([ext.lower() for ext in val]) for k, val in data.items()}
                save_config(self.config)
                messagebox.showinfo("Saved", "Categories saved to config.json")
                top.destroy()
                self.refresh_category_buttons()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save config: {e}")
        save_btn = Button(top, text="Save", command=save_and_close)
        save_btn.pack(side="left", padx=8, pady=6)
        cancel_btn = Button(top, text="Close", command=top.destroy)
        cancel_btn.pack(side="right", padx=8, pady=6)

    # ---------- Auto Scheduler ----------
    def start_scheduler_prompt(self):
        folder = self.path_var.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showerror("Invalid path", "Please select a valid folder first.")
            return
        interval = simpledialog.askinteger("Interval (minutes)", "Enter interval in minutes:", initialvalue=1440, minvalue=1)
        if interval:
            self.start_auto_scheduler(folder, interval)
            messagebox.showinfo("Auto-Scheduler", f"Organiser will run every {interval} minutes for:\n{folder}")

    def start_auto_scheduler(self, folder_path, interval_minutes=1440):
        if self.scheduler_running:
            messagebox.showinfo("Scheduler", "Auto-scheduler already running.")
            return
        self.scheduler_running = True
        folder_path = Path(folder_path)
        def job():
            if folder_path.exists():
                logging.info(f"Auto-scheduler: organising {folder_path}")
                self._organise_worker(folder_path)
            else:
                logging.warning(f"Auto-scheduler: folder not found {folder_path}")
        schedule.every(interval_minutes).minutes.do(job)
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(10)
        t = threading.Thread(target=run_scheduler, daemon=True)
        t.start()
        logging.info(f"Auto-scheduler started for folder {folder_path} every {interval_minutes} min")

# ---------- Main ----------
if __name__ == "__main__":
    root = Tk()
    app = FileOrganiserApp(root)
    root.mainloop()