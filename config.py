import os
import sys
import json

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

# --- Config path (next to script or exe) ---
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import base64
import json

CONFIG_PATH = os.path.join(BASE_DIR, "cbz_renamer_config.json")
SECRETS_PATH = os.path.join(BASE_DIR, "cbz_renamer.secrets")
CACHE_PATH = os.path.join(BASE_DIR, "cbz_renamer_cache.json")

# Simple obfuscation key (avoids plain text in file)
# VPN/Hardware safe (Portable)
_KEY = b'CBZ_RENAMER_SECURE'

def _encrypt(text):
    """Obfuscate text using simple XOR + Base64."""
    if not text: return ""
    try:
        data = text.encode('utf-8')
        xor_data = bytearray()
        # Use a cycle of the combined key
        key_len = len(_KEY)
        for i, b in enumerate(data):
            xor_data.append(b ^ _KEY[i % key_len])
        return "ENC:" + base64.b64encode(xor_data).decode('utf-8')
    except Exception:
        return text

def _decrypt(text):
    """De-obfuscate text."""
    if not text: return ""
    if not text.startswith("ENC:"): return text # Return legacy plain text as-is
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
        "comicvine_vol_prefix": "#"
    }
    try:
        # 1. Load main config
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            
            # Decrypt legacy keys if present in main config
            if "comicvine_api_key" in saved:
                saved["comicvine_api_key"] = _decrypt(saved["comicvine_api_key"])
            if "google_books_api_key" in saved:
                saved["google_books_api_key"] = _decrypt(saved["google_books_api_key"])

            defaults.update(saved)
            
        # 2. Load secrets (overrides main config if present)
        if os.path.exists(SECRETS_PATH):
            with open(SECRETS_PATH, "r") as f:
                secrets = json.load(f)
            
            # Decrypt secrets
            for key in ["comicvine_api_key", "google_books_api_key"]:
                if key in secrets:
                    secrets[key] = _decrypt(secrets[key])
            
            defaults.update(secrets)
            
        # Legacy migration check handled in save_config
            
    except Exception:
        pass
    return defaults


def save_config(cfg):
    try:
        # Separate keys from public config
        secret_keys = ["comicvine_api_key", "google_books_api_key"]
        
        public_cfg = {k: v for k, v in cfg.items() if k not in secret_keys}
        secrets_cfg = {}
        
        # Encrypt keys for secrets file
        for k in secret_keys:
            if k in cfg:
                secrets_cfg[k] = _encrypt(cfg[k])

        # Save public config
        with open(CONFIG_PATH, "w") as f:
            json.dump(public_cfg, f, indent=2)
            
        # Save secrets
        with open(SECRETS_PATH, "w") as f:
            json.dump(secrets_cfg, f, indent=2)
            
    except Exception as e:
        print(f"Config save error: {e}")
