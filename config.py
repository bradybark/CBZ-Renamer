import os
import sys
import json
import base64

# --- THEME COLORS ---
BG_DARK = "#0e0e0e"
BG_PANEL = "#181818"
BG_SURFACE = "#1e1e1e"
FG_TEXT = "#e8e8e8"
FG_DIM = "#707070"
FG_MUTED = "#999999"
ACCENT_BLUE = "#7c3aed"  # Using Purple as primary accent now (despite var name)
ACCENT_HOVER = "#8b5cf6" # Lighter purple for hover
ACCENT_PURPLE = "#7c3aed"
SUCCESS_GREEN = "#22c55e"
TABLE_BG = "#141414"
TABLE_FG = "#d4d4d4"
CONFLICT_YELLOW = "#eab308"
ERROR_RED = "#ef4444"
BORDER_COLOR = "#2a2a2a"
EDIT_BG = "#0c2d48"

# --- Config path (%LOCALAPPDATA%\CBZ Renamer\) ---
APP_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "CBZ Renamer")
os.makedirs(APP_DATA_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(APP_DATA_DIR, "settings.json")
CACHE_PATH = os.path.join(APP_DATA_DIR, "cache.json")

# Simple obfuscation key (avoids plain text in file)
_KEY = b'CBZ_RENAMER_SECURE'

def _encrypt(text):
    """Obfuscate text using simple XOR + Base64."""
    if not text: return ""
    try:
        data = text.encode('utf-8')
        xor_data = bytearray()
        key_len = len(_KEY)
        for i, b in enumerate(data):
            xor_data.append(b ^ _KEY[i % key_len])
        return "ENC:" + base64.b64encode(xor_data).decode('utf-8')
    except Exception:
        return text

def _decrypt(text):
    """De-obfuscate text."""
    if not text: return ""
    if not text.startswith("ENC:"): return text
    try:
        raw = base64.b64decode(text[4:])
        data = bytearray()
        key_len = len(_KEY)
        for i, b in enumerate(raw):
            data.append(b ^ _KEY[i % key_len])
        return data.decode('utf-8')
    except Exception:
        return text

def load_config():
    defaults = {
        "scan_mode": "both",
        "num_padding": 2,
        "include_subtitle": False,
        "sub_separator": "hyphen",
        "online_source": "google_books",
        "comicvine_api_key": "",
        "google_books_api_key": "",
        "use_source_format": True,
        "comicvine_vol_prefix": "#",
        "chapter_prefix": "Ch."
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)

            # Decrypt API keys
            for key in ["comicvine_api_key", "google_books_api_key"]:
                if key in saved:
                    saved[key] = _decrypt(saved[key])

            defaults.update(saved)

        # --- Legacy migration: read old files next to exe if they exist ---
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
        else:
            exe_dir = os.path.dirname(os.path.abspath(__file__))

        old_config = os.path.join(exe_dir, "cbz_renamer_config.json")
        old_secrets = os.path.join(exe_dir, "cbz_renamer.secrets")
        old_cache = os.path.join(exe_dir, "cbz_renamer_cache.json")

        migrated = False
        if os.path.exists(old_config):
            with open(old_config, "r") as f:
                old = json.load(f)
            for key in ["comicvine_api_key", "google_books_api_key"]:
                if key in old:
                    old[key] = _decrypt(old[key])
            defaults.update(old)
            os.remove(old_config)
            migrated = True

        if os.path.exists(old_secrets):
            with open(old_secrets, "r") as f:
                old_sec = json.load(f)
            for key in ["comicvine_api_key", "google_books_api_key"]:
                if key in old_sec:
                    old_sec[key] = _decrypt(old_sec[key])
            defaults.update(old_sec)
            os.remove(old_secrets)
            migrated = True

        if os.path.exists(old_cache):
            # Move cache file to new location
            import shutil
            shutil.move(old_cache, CACHE_PATH)

        if migrated:
            save_config(defaults)

    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        save_data = dict(cfg)

        # Encrypt API keys before saving
        for key in ["comicvine_api_key", "google_books_api_key"]:
            if key in save_data and save_data[key]:
                save_data[key] = _encrypt(save_data[key])

        with open(CONFIG_PATH, "w") as f:
            json.dump(save_data, f, indent=2)

    except Exception as e:
        print(f"Config save error: {e}")
