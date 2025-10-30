🗂️ File Organiser App - Smart Desktop Tool to Automatically Organize Files

📘 Overview:
>>> The **File Organiser App** is a Python-based desktop tool built with **Tkinter / CustomTkinter**.  
>>> It automatically organizes files in a selected folder into categories like **Images**, **Videos**, **Music**, **Documents**, and **Others** — including **Sub-Documents** under Documents.
>>> The app includes **Undo**, **Duplicate Finder**, **Scheduler**, **Voice Feedback**, **Backup**, and **Theme Customization** features — all in one simple GUI.



🚀 **Features:**

✅ **Organiser** – Sorts files into folders (Images, Videos, Documents → Sub-Documents, Music, Others).  
✅ **Undo Last** – Restores files to original places.  
✅ **Duplicate Finder** – Detects and deletes duplicate files (SHA-256 hash).  
✅ **Auto Scheduler** – Runs automatically every few minutes.  
✅ **Summary & Graphs** – Shows file stats with charts.  
✅ **Voice Feedback** – Announces when tasks complete.  
✅ **Themes & Colors** – Light/Dark mode with Green, Blue, Purple accents.  
✅ **Backup & Restore** – Creates backups safely.  
✅ **Privacy Cleaner** – Deletes logs and configs securely.






🧰 **Technologies Used:**

| Feature | Library |
|----------|----------|
| GUI | Tkinter / CustomTkinter |
| File Handling | OS, Shutil, Pathlib |
| Threading | threading |
| Graphs | Matplotlib |
| Voice | pyttsx3 |
| Hashing | hashlib |






🖥️ **How to Run**:

1️⃣ Install Python 3.12+  
2️⃣ Install libraries:
```bash
pip install customtkinter matplotlib pyttsx3
python file_organiser_perfect.py
```





📂 **Folder Output Example**

📁 MyFolder
├── Images/
├── Videos/
├── Music/
├── Documents/
│   ├── PDF/
│   ├── Word/
│   ├── Excel/
│   └── Others/
├── Others/
└── _backup/

🎙️ Voice Output: “Files Organized Successfully!”






🧩 **UI Sections**

Sidebar: Home, Open Folder, Settings, Exit. 

Main Area: Browse field, Buttons (Organise, Undo, Duplicates, Scheduler). 

Graph & Summary: Shows file stats and counts. 







⚙️ **Config & Logs**

activity.log – Tracks actions, 

config.json – Saves preferences, 

_backup/ – Folder backups, 

Use Privacy Cleaner in settings to clear data.







🔒 **Safe Features**

Files moved, not deleted. 

Undo available anytime. 

Duplicate deletion optional. 

Backup ensures safety. 








🧑‍💻 **Developer Info**

Developer: Dhanya R.V
Version: 1.0


🏁 **Conclusion**

The File Organiser App is a smart, safe, and fast desktop tool that keeps your folders clean and organized automatically.
Perfect for everyday use with automation, backup, and voice feedback.
