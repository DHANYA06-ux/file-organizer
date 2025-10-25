# Enhanced File Organizer (Tkinter + Python)

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)  
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A desktop File Organizer built with Python and Tkinter.  
Automatically sorts files into categories like Images, Documents, Videos, etc., with features such as undo, logging, and customizable categories.


## Features

- Graphical Interface using Tkinter
- Automatic File Sorting
- Progress Bar and Status Display
- Undo Last Organize
- Customizable Categories via `config.json`
- Summary Report after Organizing
- Activity Logging
- Duplicate File Detection
- Dark/Light Mode Ready


## Tech Stack

- Frontend: Tkinter (Python GUI)  
- Backend: Python 3.x  
- Libraries: `os`, `shutil`, `json`, `tkinter`, `ttk`, `hashlib`, `logging`  



## How to Run

1. Open **PowerShell or CMD** in your project folder:

```bash
cd "C:\Users\91843\OneDrive\Documents\Desktop\project"
````

2. Run the program:

```bash
python file_organiser_enhanced.py
```

3. Use the app:

   * Click **Browse** and select a folder
   * Click **Organize** to start sorting
   * Check the newly created folders (Documents, Images, Videos, etc.)

4. Undo last action: Click **Undo Last Organize**.


## Configuration (`config.json`)

Define file categories in `config.json`:

```json
{
  "Images": ["jpg", "jpeg", "png"],
  "Documents": ["pdf", "docx", "txt"],
  "Videos": ["mp4", "mkv"],
  "Audio": ["mp3", "wav"],
  "Archives": ["zip", "rar"]
}
```

You can edit or add your own categories.

## Log Files

* `activity.log` — Logs all operations and errors
* `last_move.json` — Stores temporary data for undo functionality


## Folder Structure

project/
├── file_organiser_enhanced.py
├── config.json
├── activity.log
├── last_move.json
└── README.md


## Future Enhancements

* Auto-scheduler for daily organizing
* Cloud backup support (Google Drive / OneDrive)
* Drag & Drop file support

## Author

Dhanya R.V
Project: File Organizer
Language: Python (Tkinter GUI)


##  Contact

If you encounter any issues or have suggestions for improvement,  
feel free to **open an issue** or contact the maintainer.
