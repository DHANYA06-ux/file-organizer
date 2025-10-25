# Enhanced File Organizer (Tkinter + Python)

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)  
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A desktop File Organizer built with Python and Tkinter.  
Automatically sorts files into categories like Images, Documents, Videos, etc., with features such as undo, logging, customizable categories, and auto-scheduling.

## Features

- Graphical Interface using Tkinter
- Automatic File Sorting
- Progress Bar and Status Display
- Undo Last Organize
- Customizable Categories via `config.json`
- Summary Report after Organizing
- Graph Representation of Organized Files (via Matplotlib)
- Activity Logging
- Duplicate File Detection
- Auto-Scheduler: automatically organize a folder at set intervals
- Dark/Light Mode Ready

## Tech Stack

- Frontend: Tkinter (Python GUI)  
- Backend: Python 3.x  
- Libraries: os, shutil, json, tkinter, ttk, hashlib, logging, schedule, matplotlib


## Graph Representation

After organizing, the app automatically generates a bar or pie chart using Matplotlib
to show the distribution of files by category (e.g., Documents, Images, Videos, etc.).

Example:
Bar chart shows how many files were sorted into each category.
Helps visualize your folder’s composition and storage usage.
The chart window closes automatically after viewing.
(Requires matplotlib — install it using pip install matplotlib if not already installed.)


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
   * Optional: Click **Undo Last Organize** to revert changes

4. Auto-Scheduler:

   * Click **Start Auto-Scheduler**
   * Enter interval in minutes (default 1440 = 1 day)
   * The program will automatically organize the folder at the set interval

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
The program normalizes extensions automatically.

## Log Files

* `activity.log` — Logs all operations, errors, and auto-scheduler runs
* `last_move.json` — Stores temporary data for undo functionality

## Folder Structure

project/

```
├── file_organiser_enhanced.py
├── config.json
├── activity.log
├── last_move.json
└── README.md
```

## Future Enhancements

* Cloud backup support (Google Drive / OneDrive)
* Drag & Drop file support
* Stop Auto-Scheduler button

## Author

Dhanya R.V
Project: File Organizer
Language: Python (Tkinter GUI)

## Contact

If you encounter any issues or have suggestions for improvement,
feel free to **open an issue** or contact the maintainer.

I included:

1. **Auto-scheduler instructions**  
2. Mention of `schedule` library in Tech Stack  
3. Notes about logs recording scheduler activity  
4. Minor wording tweaks for clarity  

If you want, I can also **add a “Stop Auto-Scheduler” instruction and button** in the README to make it fully complete.  

Do you want me to add that too?

