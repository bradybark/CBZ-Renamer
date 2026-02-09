import os
import json

# --- THEME COLORS ---
BG_DARK = "#0e0e0e"
BG_PANEL = "#181818"
BG_SURFACE = "#1e1e1e"
FG_TEXT = "#e8e8e8"
FG_DIM = "#707070"
FG_MUTED = "#999999"
ACCENT_BLUE = "#2b8aed"
ACCENT_HOVER = "#4da3ff"
ACCENT_PURPLE = "#7c3aed"
SUCCESS_GREEN = "#22c55e"
TABLE_BG = "#141414"
TABLE_FG = "#d4d4d4"
CONFLICT_YELLOW = "#eab308"
ERROR_RED = "#ef4444"
BORDER_COLOR = "#2a2a2a"
EDIT_BG = "#0c2d48"

# --- Config path (next to script) ---
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cbz_renamer_config.json")


def load_config():
    defaults = {
        "scan_mode": "both",
        "num_padding": 2,
        "include_subtitle": False,
        "sub_separator": "hyphen",
        "online_source": "google_books",
        "comicvine_api_key": "",
        "use_source_format": True
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"Config save error: {e}")
