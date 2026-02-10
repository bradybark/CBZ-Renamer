# CBZ Renamer // PRO

A professional bulk renaming tool for comic and manga files (`.cbz`) that fetches accurate metadata from **Google Books** and **ComicVine**. This tool helps organize your digital library by normalizing filenames and appending correct subtitles.

![License](https://img.shields.io/badge/License-MIT-purple) ![Python](https://img.shields.io/badge/Python-3.13-blue)

## Features

- **Smart Metadata** — Verifies series names and numbering against online databases.
- **Subtitle Probing** — Automatically fetches volume subtitles (e.g., `Invincible, Vol. 01: Family Matters`).
- **Secure Configuration** — API keys are encrypted and stored in a separate `.secrets` file.
- **Conflict Detection** — Highlights discrepancies between filenames and online data.
- **Pro UI** — sleek dark theme, inline editing, and collapsible settings.

## Usage

1.  **Run** the application (`CBZ Renamer.exe` or `python cbz_file_renamer.py`).
2.  **Configure** your API keys in Settings (`Google Books` is free; `ComicVine` requires a key).
3.  **Open Folder** containing your `.cbz` files.
4.  **Scan** to fetch metadata.
5.  **Review** matches (Web vs Local). Double-click to edit, right-click to toggle source.
6.  **Apply Rename** to finalize changes.

## Installation

No installation required for the executable.
To run from source:
```bash
pip install -r requirements.txt  # (Only standard lib + Pillow/requests if needed)
python cbz_file_renamer.py
```
*(Note: This project uses only the Python Standard Library + Pillow/requests for icons/api)*
