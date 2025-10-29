🗂️ File Organiser App

**Smart Desktop Tool to Automatically Organize Files**


📘 **Project Overview**

The **File Organiser App** is a modern desktop application built using **Python (Tkinter / CustomTkinter)** that helps users **organize files inside a selected folder automatically** based on file types such as images, documents, videos, and music.

It also supports **undo**, **duplicate finder**, **auto-scheduler**, **backup**, **voice feedback**, and **theme customization** — all within a stylish GUI interface.

 🚀 **Features**

✅ **Automatic File Sorting**
Organizes files into subfolders (Images, Documents, Videos, Music, Others).

✅ **Duplicate Finder**
Detects and optionally deletes duplicate files based on content hash (SHA-256).

✅ **Undo Last Action**
Reverts the most recent organization operation.

✅ **Scheduler**
Automatically runs the organizer at regular time intervals (user-defined in minutes).

✅ **Summary & Graph View**
Displays file distribution summary and live graph visualization (Matplotlib).

✅ **Voice Feedback**
Uses text-to-speech (pyttsx3) to announce task completion.

✅ **Light / Dark Theme Modes**
Toggle between themes instantly.

✅ **Custom Accent Colors**
Choose between Green, Blue, or Purple UI color themes.

✅ **Backup & Restore**
Quickly create a backup of your selected folder.

✅ **Privacy Cleaner**
Deletes activity logs and configuration files.

🧰 **Technologies Used**

| Component     | Library / Tool                 |
| ------------- | ------------------------------ |
| GUI           | CustomTkinter / Tkinter        |
| File Handling | OS, Shutil, Pathlib            |
| Plotting      | Matplotlib                     |
| Voice Engine  | pyttsx3                        |
| Threading     | threading                      |
| Hashing       | hashlib (for duplicate finder) |

 🖥️ **How to Run**

**1️⃣ Install Dependencies**

Make sure you have **Python 3.12+** installed, then open a terminal and run:

```bash
pip install customtkinter matplotlib pyttsx3
```

> (If some libraries fail to install, the app still runs with minimal fallbacks.)

### **2️⃣ Run the Application**

Save the script as `file_organiser_perfect.py`, then run:

```bash
python file_organiser_perfect.py
```

📂 **How It Works**

1. **Browse** → Select a folder using the **Browse** button.
2. **Organise Now** → Instantly sorts files into category folders.
3. **Undo Last** → Moves files back to their original location.
4. **Find Duplicates** → Scans and shows duplicate files. Option to delete duplicates.
5. **Start Scheduler** → Automates organizing every *N* minutes.
6. **Settings** → Change theme, accent color, clock format, language, and privacy options.
7. **Backup** → Creates a copy of your files in `_backup` folder.

📊 **Outputs**

* **Organized Folder Structure**

  ```
  📁 MyFolder
  ├── Images/
  ├── Documents/
  ├── Videos/
  ├── Music/
  ├── Others/
  └── _backup/  (if backup created)
  ```

* **Summary Panel** → Shows counts for each file type.
* **Bar Graph** → Displays file distribution visually.
* **Voice Message** → “Files Organized Successfully!”

 **User Interface Layout**

| Section            | Description                                                  |
| ------------------ | ------------------------------------------------------------ |
| **Sidebar (Left)** | Home, Open Folder, Settings, Exit                            |
| **Main Area**      | Headings, Browse Field, Action Buttons                       |
| **Buttons**        | Organise Now • Start Scheduler • Undo Last • Find Duplicates |
| **Graph Area**     | Displays organized file statistics                           |
| **Summary Box**    | Shows category counts (bottom-right)                         |


⚙️ **Configuration & Logs**

* **activity.log** → Tracks organization events
* **config.json** → Stores custom file type mappings
* **_backup/** → Stores backup copies when created

Use **Clear Logs** in *Settings → Privacy Cleaner* to erase them safely.

🔒 **Safety Features**

* Files moved, not deleted (reversible using Undo).
* Duplicate deletion is optional and confirmed.
* Backup option ensures data safety before organizing.

🧑‍💻 **Developer Info**

**Developer:** Dhanya R.V
**Version:** 1.0
**Theme:** Dark / Green
**Tagline:** *“Smart desktop tool to sort files quickly and safely.”*


🗣️ **Voice Output Example**

> 🎙️ “Files Organized Successfully!”

 📸 **Screenshots (Recommended for Report)**

1. **Home Page with Buttons**
2. **After Organization – Summary and Graph**
3. **Duplicate Finder Window**
4. **Settings Window**

🏁 **Conclusion**

The **File Organiser App** is a powerful and user-friendly tool designed to keep your system folders clean and organized automatically.
Its mix of **automation**, **customization**, and **voice feedback** makes it an efficient solution for everyday file management.

