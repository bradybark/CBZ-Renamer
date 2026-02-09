# CBZ Renamer // PRO

A desktop tool for batch-renaming `.cbz` comic and manga files using online metadata from **Google Books** and **ComicVine** APIs.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

- **Online Lookups** — Fetches correct series names and subtitles from Google Books or ComicVine
- **Source Format Preservation** — Uses the exact title formatting returned by the API (e.g. `Berserk Volume 01.cbz`), with a toggle to switch to standardized formatting (`Berserk, Vol. 01.cbz`)
- **Local Guess** — Parses filenames locally when no internet is available
- **Conflict Detection** — Highlights when online and local names disagree
- **Duplicate Detection** — Flags files that would rename to the same target
- **Inline Editing** — Double-click any final name to manually adjust it
- **Right-Click Toggle** — Quickly switch between Web Match and Local Guess per file
- **Zero-Padded Numbers** — Configurable 2 or 3-digit volume padding
- **Subtitle Support** — Optionally include subtitles with configurable separators
- **Dark UI** — Clean dark theme built with Tkinter

## Screenshot

> Launch the app to see the dark-themed interface with scan results table, status indicators, and settings dialog.

## Getting Started

### Requirements

- Python 3.10+
- No external dependencies — uses only the Python standard library

### Run

```bash
python cbz_file_renamer.py
```

### Usage

1. Click **OPEN FOLDER** and select a directory containing `.cbz` files
2. Click **SCAN** to analyze filenames and fetch online metadata
3. Review the results table:
   - **WEB MATCH** — Name from the online API
   - **LOCAL GUESS** — Name parsed from the filename
   - **FINAL NAME** — The name that will be applied (double-click to edit)
   - **STATUS** — `Verified`, `Conflict`, `Online`, `Ready`, `Perfect`, etc.
4. Right-click a row to toggle between Web Match and Local Guess
5. Click **APPLY RENAME** to rename the files

### Settings

Click the ⚙ gear icon to configure:

| Setting               | Options                                                        |
| --------------------- | -------------------------------------------------------------- |
| **Scan Source**       | Local + Online, Local Only, Online Only                        |
| **Online Source**     | Google Books (no key needed), ComicVine (requires API key)     |
| **Number Padding**    | 2 digits (01) or 3 digits (001)                                |
| **Use Source Format** | Preserve exact API title formatting (default: on)              |
| **Subtitles**         | Include/exclude, separator style (hyphen, colon, match source) |

## Project Structure

```
cbz-renamer/
├── cbz_file_renamer.py    # Main app — UI and scan logic
├── config.py              # Theme colors, config load/save
├── filename_parser.py     # Filename parsing and normalization
├── api_sources.py         # Google Books & ComicVine API clients
└── cbz_renamer_config.json  # Persisted user settings (auto-generated)
```

## ComicVine API Key

To use ComicVine as your online source, you'll need a free API key:

1. Create an account at [comicvine.gamespot.com](https://comicvine.gamespot.com)
2. Get your key at [comicvine.gamespot.com/api](https://comicvine.gamespot.com/api/)
3. Paste it into Settings → ComicVine API Key
